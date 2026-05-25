# LLM Inference Logging & Ingestion System — Implementation Plan

## Context

Build a production-grade LLM chatbot with full inference observability: multi-provider support, streaming responses, event-based log ingestion, PII redaction, and analytics dashboards. Target all bonus deliverables for guaranteed interview at Ollive.ai. Stack: Python (FastAPI) + Next.js 14. Staged delivery so each stage is independently testable.

---

## Architecture Overview

```
User
 │
 ▼
Next.js Frontend (port 3000)
 │  SSE stream chunks
 ▼
FastAPI API Service (port 8000)
 ├── Uses llm-sdk (internal Python package)
 │    └── Providers: Anthropic / OpenAI / Gemini
 ├── Stores messages → PostgreSQL (inline PII redaction via Presidio)
 └── Publishes InferenceEvent → Redis Streams (fire-and-forget)
                                      │
                               Redis Streams
                               ("llm-inference-logs")
                                      │
                                      ▼
                            Ingestion Service (port 8001)
                            ├── XREADGROUP consumer loop (batches of 50)
                            ├── Validates payload (Pydantic)
                            ├── Redacts PII via Presidio sidecar
                            ├── Writes InferenceLog → PostgreSQL
                            ├── Updates session aggregates
                            └── REFRESH CONCURRENTLY dashboard_hourly_stats
                                      │
                            Presidio Sidecar (port 8080)
                            └── POST /analyze_and_anonymize
```

---

## Directory Structure

```
chatbot/
├── docker-compose.yml
├── docker-compose.override.yml        # dev hot-reload + pgAdmin
├── .env.example
├── .gitignore
├── README.md
├── k8s/                               # Stage 7: Kubernetes manifests
│   ├── namespace.yaml
│   ├── postgres/
│   ├── redis/
│   ├── api/
│   ├── ingestion/
│   ├── presidio/
│   └── frontend/
│
├── packages/
│   └── llm-sdk/
│       ├── pyproject.toml
│       └── llm_sdk/
│           ├── __init__.py
│           ├── client.py              # TrackedClient (keystone)
│           ├── providers/
│           │   ├── base.py            # BaseProvider ABC
│           │   ├── anthropic.py
│           │   ├── openai.py
│           │   └── gemini.py
│           ├── models.py              # InferenceEvent Pydantic model
│           ├── emitter.py             # Redis Streams XADD publisher
│           ├── pii.py                 # Fast local truncation (500 chars)
│           └── streaming.py           # AsyncIterator wrapper
│
├── services/
│   ├── api/
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── alembic.ini
│   │   ├── alembic/versions/001_initial_schema.py
│   │   └── app/
│   │       ├── main.py
│   │       ├── config.py
│   │       ├── database.py            # SQLAlchemy async engine
│   │       ├── dependencies.py
│   │       ├── models/
│   │       │   ├── session.py         # ChatSession ORM
│   │       │   ├── message.py         # Message ORM
│   │       │   └── inference_log.py   # InferenceLog ORM
│   │       ├── schemas/               # Pydantic request/response
│   │       └── routers/
│   │           ├── sessions.py        # CRUD conversations
│   │           ├── chat.py            # SSE streaming endpoint
│   │           ├── dashboard.py       # Analytics queries
│   │           └── health.py
│   │
│   ├── ingestion/
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── app/
│   │       ├── main.py
│   │       ├── consumer.py            # Redis Streams XREADGROUP loop
│   │       ├── validator.py           # Pydantic validation
│   │       ├── extractor.py           # Metadata extraction
│   │       ├── pii_client.py          # HTTP → Presidio sidecar
│   │       ├── database.py
│   │       └── writer.py              # Async bulk insert
│   │
│   └── presidio/
│       ├── Dockerfile
│       └── app.py                     # Thin FastAPI wrapper
│
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── next.config.ts
    └── src/
        ├── app/
        │   ├── conversations/page.tsx  # List + resume
        │   ├── conversations/[id]/page.tsx
        │   └── dashboard/page.tsx
        ├── components/
        │   ├── chat/                  # ChatWindow, MessageBubble, Input, ProviderSelector
        │   └── dashboard/             # LatencyChart, ThroughputChart, ErrorRateChart, MetricCard
        ├── hooks/
        │   ├── useChat.ts             # SSE + abort/cancel
        │   └── useConversations.ts
        └── lib/api.ts                 # Typed fetch client
```

---

## Database Schema

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Sessions
CREATE TABLE chat_sessions (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title         TEXT,
    provider      TEXT NOT NULL,
    model         TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'active',  -- active | cancelled | archived
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    message_count INTEGER NOT NULL DEFAULT 0,
    total_tokens  INTEGER NOT NULL DEFAULT 0,
    metadata      JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_sessions_created_at ON chat_sessions(created_at DESC);
CREATE INDEX idx_sessions_status     ON chat_sessions(status);
CREATE INDEX idx_sessions_provider   ON chat_sessions(provider);

-- Messages
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content         TEXT NOT NULL,               -- PII-redacted before storage
    content_preview TEXT,                        -- first 200 chars
    sequence_num    INTEGER NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata        JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_messages_session_sequence ON messages(session_id, sequence_num);

-- Inference Logs
CREATE TABLE inference_logs (
    id                     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id             UUID REFERENCES chat_sessions(id) ON DELETE SET NULL,
    message_id             UUID REFERENCES messages(id) ON DELETE SET NULL,
    provider               TEXT NOT NULL,
    model                  TEXT NOT NULL,
    provider_request_id    TEXT,
    started_at             TIMESTAMPTZ NOT NULL,
    completed_at           TIMESTAMPTZ,
    latency_ms             INTEGER,
    time_to_first_token_ms INTEGER,
    input_tokens           INTEGER,
    output_tokens          INTEGER,
    total_tokens           INTEGER GENERATED ALWAYS AS (
                               COALESCE(input_tokens,0) + COALESCE(output_tokens,0)
                           ) STORED,
    status                 TEXT NOT NULL DEFAULT 'success'
                               CHECK (status IN ('success','error','cancelled','timeout')),
    error_code             TEXT,
    error_message          TEXT,
    input_preview          TEXT,   -- 500 chars, PII-redacted
    output_preview         TEXT,   -- 500 chars, PII-redacted
    is_streaming           BOOLEAN NOT NULL DEFAULT FALSE,
    stream_chunks          INTEGER,
    sdk_version            TEXT,
    client_metadata        JSONB DEFAULT '{}'::jsonb,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_inference_logs_session_id  ON inference_logs(session_id);
CREATE INDEX idx_inference_logs_started_at  ON inference_logs(started_at DESC);
CREATE INDEX idx_inference_logs_provider    ON inference_logs(provider);
CREATE INDEX idx_inference_logs_status      ON inference_logs(status);
CREATE INDEX idx_inference_logs_latency     ON inference_logs(latency_ms);

-- Materialized view for dashboard (REFRESH CONCURRENTLY after each ingestion batch)
CREATE MATERIALIZED VIEW dashboard_hourly_stats AS
SELECT
    date_trunc('hour', started_at)  AS hour_bucket,
    provider, model,
    COUNT(*)                         AS request_count,
    COUNT(*) FILTER (WHERE status = 'error') AS error_count,
    AVG(latency_ms)                  AS avg_latency_ms,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY latency_ms) AS p50_latency_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95_latency_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms) AS p99_latency_ms,
    SUM(total_tokens)                AS total_tokens,
    SUM(input_tokens)                AS total_input_tokens,
    SUM(output_tokens)               AS total_output_tokens
FROM inference_logs
WHERE completed_at IS NOT NULL
GROUP BY 1, 2, 3
WITH DATA;

CREATE UNIQUE INDEX ON dashboard_hourly_stats(hour_bucket, provider, model);
```

---

## Key Interfaces

### SDK — TrackedClient
```python
class TrackedClient:
    def __init__(self, provider: Literal["anthropic","openai","gemini"],
                 model: str, session_id: str,
                 emit_logs: bool = True, redact_pii: bool = True): ...

    async def chat(self, messages: list[ChatMessage], **kwargs) -> ChatResponse: ...
    async def stream(self, messages: list[ChatMessage], **kwargs) -> AsyncIterator[StreamChunk]: ...
    async def cancel(self): ...
```

### SDK — InferenceEvent (Redis payload)
```python
class InferenceEvent(BaseModel):
    event_id: str; event_version: str = "1.0"
    session_id: str; provider: str; model: str; sdk_version: str
    started_at: datetime; completed_at: datetime | None; latency_ms: int | None
    time_to_first_token_ms: int | None; is_streaming: bool; stream_chunks: int | None
    input_tokens: int | None; output_tokens: int | None
    status: Literal["success","error","cancelled","timeout"]
    error_code: str | None; error_message: str | None
    input_preview: str | None; output_preview: str | None
    provider_request_id: str | None; client_metadata: dict
```

### Provider abstraction
```python
class BaseProvider(ABC):
    @abstractmethod
    async def complete(self, messages, model, **kwargs) -> tuple[ChatResponse, ProviderMeta]: ...
    @abstractmethod
    async def stream(self, messages, model, **kwargs) -> AsyncIterator[tuple[StreamChunk, ProviderMeta]]: ...
    @abstractmethod
    def extract_usage(self, raw) -> TokenUsage: ...
    @abstractmethod
    def extract_request_id(self, raw) -> str | None: ...

PROVIDER_REGISTRY = {
    "anthropic": AnthropicProvider,
    "openai":    OpenAIProvider,
    "gemini":    GeminiProvider,
}
```

---

## Staged Implementation Plan

### Stage 1 — Infrastructure Foundation
**Goal:** `docker compose up` brings up healthy postgres + redis + presidio.

- Write `docker-compose.yml` (postgres:16, redis:7, presidio, api, ingestion, frontend)
- Write `docker-compose.override.yml` (hot-reload + pgAdmin on `--profile debug`)
- Write `.env.example`
- Write `alembic/versions/001_initial_schema.py` (all tables + materialized view)
- Write presidio sidecar `services/presidio/app.py` (POST /analyze_and_anonymize)
- Test: `docker compose up postgres redis presidio` → all healthy

**Files:** `docker-compose.yml`, `docker-compose.override.yml`, `.env.example`, `services/presidio/app.py`, `services/api/alembic/versions/001_initial_schema.py`

---

### Stage 2 — Internal SDK (llm-sdk package)
**Goal:** `TrackedClient` wraps all 3 providers, publishes events to Redis Streams.

- `packages/llm-sdk/llm_sdk/providers/base.py` — BaseProvider ABC
- `packages/llm-sdk/llm_sdk/providers/anthropic.py` — streaming + non-streaming
- `packages/llm-sdk/llm_sdk/providers/openai.py`
- `packages/llm-sdk/llm_sdk/providers/gemini.py`
- `packages/llm-sdk/llm_sdk/models.py` — InferenceEvent
- `packages/llm-sdk/llm_sdk/emitter.py` — XADD to Redis Streams
- `packages/llm-sdk/llm_sdk/client.py` — TrackedClient orchestrator
- Test: smoke test each provider, assert InferenceEvent fields, assert Redis XLEN > 0

**Files:** All under `packages/llm-sdk/llm_sdk/`

---

### Stage 3 — API Service (FastAPI)
**Goal:** `curl` can start a session and receive SSE chunks from any provider.

- `services/api/app/database.py` — SQLAlchemy async engine + session factory
- `services/api/app/models/` — ORM models (ChatSession, Message, InferenceLog)
- `services/api/app/routers/sessions.py` — POST/GET/DELETE /sessions
- `services/api/app/routers/chat.py` — GET /sessions/{id}/stream (SSE)
  - Inline Presidio call on user message before DB write
  - `request.is_disconnected()` check → `client.cancel()` on abort
  - Fire-and-forget Redis publish after stream ends
- Test: `curl -N "http://localhost:8000/sessions/{id}/stream?user_message=hi&provider=anthropic&model=claude-sonnet-4-6"`

**Critical file:** `services/api/app/routers/chat.py` (most complex endpoint)

---

### Stage 4 — Ingestion Service
**Goal:** Events flow Redis → Ingestion → Postgres with PII-redacted previews.

- `services/ingestion/app/consumer.py` — XREADGROUP loop, batch=50, timeout=1s
  - Consumer groups with `XACK` on success
  - PEL claim on restart (exactly-once semantics)
- `services/ingestion/app/validator.py` — Pydantic parse raw Redis entry
- `services/ingestion/app/pii_client.py` — async HTTP → presidio sidecar
- `services/ingestion/app/writer.py` — bulk insert inference_logs, UPDATE session aggregates, REFRESH CONCURRENTLY dashboard_hourly_stats
- Test: send message → verify inference_logs row in Postgres with correct fields

**Critical file:** `services/ingestion/app/consumer.py` (PEL claim logic)

---

### Stage 5 — Frontend Core
**Goal:** Full chat UI with conversation list, resume, cancel, provider selector.

- Next.js 14 App Router + Tailwind + shadcn/ui scaffold
- `src/hooks/useChat.ts` — SSE stream with AbortController cancel
- `src/app/conversations/page.tsx` — list all sessions (GET /sessions)
- `src/app/conversations/[id]/page.tsx` — chat window, load history on resume
- `src/components/chat/ProviderSelector.tsx` — Anthropic | OpenAI | Gemini + model dropdown
- Cancel button: calls `abortRef.current.abort()` → backend detects disconnect → logs `cancelled`
- Test: create session, send message, see streaming chunks, cancel mid-stream, resume session

---

### Stage 6 — Analytics Dashboard
**Goal:** Live charts auto-refreshing every 30s from materialized view.

- `services/api/app/routers/dashboard.py` — GET /dashboard/stats?range=24h&provider=all
  - Queries `dashboard_hourly_stats` view
  - Returns: latency p50/p95/p99, request_count, error_rate, token usage per bucket
- `src/app/dashboard/page.tsx` + components:
  - `LatencyChart` — Recharts LineChart (p50/p95/p99 over time)
  - `ThroughputChart` — BarChart (requests/hour per provider)
  - `ErrorRateChart` — AreaChart (error % rolling)
  - `MetricCard` — total requests, avg latency, total tokens, error count
- 30s polling via `setInterval` + `useDashboard` hook

---

### Stage 7 — Kubernetes Manifests
**Goal:** `kubectl apply -k k8s/` deploys full stack on self-hosted k8s (Kind/Minikube).

- `k8s/namespace.yaml`
- `k8s/postgres/` — StatefulSet, PVC, Service, Secret
- `k8s/redis/` — Deployment, Service, ConfigMap (persistence + maxmemory)
- `k8s/presidio/` — Deployment, Service
- `k8s/api/` — Deployment, Service, HPA (min=1, max=5, CPU=70%)
- `k8s/ingestion/` — Deployment (replicas=2 for consumer group scaling)
- `k8s/frontend/` — Deployment, Service, Ingress
- `k8s/kustomization.yaml` — ties all together
- Test: `kind create cluster && kubectl apply -k k8s/ && kubectl get pods -n chatbot`

---

## PII Redaction Strategy

| Location | What | When | Latency impact |
|---|---|---|---|
| API service (inline) | User message content | Before Postgres write | ~30ms, acceptable |
| Ingestion service (async) | input_preview, output_preview, error_message | After Redis consume | Zero user impact |
| SDK | Truncation only (500 chars) | Before Redis publish | <1ms |

Presidio detects: `EMAIL_ADDRESS`, `PHONE_NUMBER`, `PERSON`, `US_SSN`, `CREDIT_CARD`, `IP_ADDRESS`, `LOCATION`. Replaces with `<REDACTED:ENTITY_TYPE>`.

---

## Docker Compose (one-command)

```
docker compose up --build
```

Services: `postgres`, `redis`, `presidio`, `api`, `ingestion`, `frontend`
Dev extras: `docker compose --profile debug up` adds `pgadmin`
Scale ingestion: `docker compose up --scale ingestion=3`

---

## Verification (End-to-End)

1. `docker compose up --build` — all 6 services healthy
2. Open `http://localhost:3000` — conversation list visible
3. New conversation → select Anthropic → send "Hello" → see streaming response
4. Switch to OpenAI provider → send message → works identically
5. Mid-stream: click Cancel → stream stops → `inference_logs` row has `status=cancelled`
6. Go back to conversation list → click resumed session → history loads, continue chatting
7. Open `http://localhost:3000/dashboard` → charts show latency/throughput/errors
8. Send PII ("My email is test@example.com") → check DB → content shows `<REDACTED:EMAIL_ADDRESS>`
9. Check `inference_logs` table → `input_preview` PII-redacted, all fields populated
10. `kubectl apply -k k8s/` → all pods running → same test on cluster

---

## Tradeoffs and Notes

- **Redis Streams over Kafka**: same consumer group semantics, zero extra infra at this scale
- **Separate ingestion service**: hot path (SSE) never blocked by Presidio/Postgres write latency
- **Materialized view**: sub-ms dashboard reads; 30s staleness acceptable for observability
- **PII two-stage**: user message cleaned sync (must be before DB write); assistant preview cleaned async (no urgency)
- **UUID v4 over ULID**: simpler; range queries use `created_at` indexes instead
