# Architecture Notes

## System Overview

```
Browser
  │  SSE (text/event-stream)
  ▼
┌─────────────────────────────────────────┐
│         Next.js 14 Frontend             │
│  /conversations  /dashboard             │
└──────────────┬──────────────────────────┘
               │ fetch + EventSource
               ▼
┌─────────────────────────────────────────┐
│          FastAPI API Service            │
│                                         │
│  POST /sessions        (create)         │
│  GET  /sessions/{id}/stream  (SSE)      │
│  GET  /dashboard/stats  (analytics)     │
│                                         │
│  ┌────────────┐   ┌──────────────────┐  │
│  │ llm-sdk    │   │ Presidio client  │  │
│  │ TrackedClient   │ (inline PII)    │  │
│  └──────┬─────┘   └──────────────────┘  │
└─────────┼───────────────────────────────┘
          │ XADD (fire-and-forget)
          ▼
┌─────────────────────┐     ┌─────────────┐
│   Redis Streams     │     │  PostgreSQL  │
│  "llm-inference-    │     │             │
│     logs"           │     │ chat_sessions│
└─────────┬───────────┘     │ messages    │
          │ XREADGROUP       │ inference_  │
          ▼                  │ logs        │
┌─────────────────────┐     │ dashboard_  │
│  Ingestion Service  │────►│ hourly_stats│
│  (2 replicas)       │     └─────────────┘
│                     │
│  ┌───────────────┐  │
│  │ Presidio      │  │
│  │ (async PII)   │  │
│  └───────────────┘  │
└─────────────────────┘
          ▲
┌─────────────────────┐
│  Presidio Sidecar   │
│  (port 8080)        │
│  spaCy en_core_web  │
└─────────────────────┘
```

---

## Services

### 1. llm-sdk (Internal Python Package)

The SDK is a standalone installable package (`packages/llm-sdk/`) shared by the API service. It owns the entire LLM call lifecycle.

**TrackedClient** is the central abstraction:

```python
client = TrackedClient(
    provider="gemini",       # anthropic | openai | gemini
    model="gemini-2.5-flash",
    session_id=session_id,
    redis_client=redis,      # for event emission
)
async for chunk in client.stream(messages):
    yield chunk              # StreamChunk(text, is_final)
```

Internally it:
1. Delegates to the correct `BaseProvider` subclass via `PROVIDER_REGISTRY`
2. Wraps the provider's async generator with `StreamingTracker` to measure TTFT (time-to-first-token) by recording `time.monotonic()` on first yielded chunk
3. After stream completes (or errors/cancels), builds an `InferenceEvent` Pydantic model and calls `emit_event()` — a fire-and-forget XADD to Redis Streams that never raises

**Provider abstraction:**

```
BaseProvider (ABC)
├── AnthropicProvider   — anthropic-sdk streaming
├── OpenAIProvider      — openai-sdk streaming
├── GeminiProvider      — google-genai streaming
│                         (maps "assistant" role → "model",
│                          injects system prompt into first user message)
└── SarvamProvider      — OpenAI-compatible (openai-sdk, base_url override)
```

All three providers implement the same interface: `stream()` yields `(StreamChunk, ProviderMeta)` tuples. The SDK never knows which provider it's talking to beyond the initial registry lookup.

**Why a separate SDK package?**
The ingestion service and API service both import from it. More importantly, it enforces a clean boundary: business logic (session management, HTTP routing) never touches LLM provider SDKs directly. If we add a fourth provider, only the SDK changes.

---

### 2. API Service (FastAPI)

Single responsibility: handle HTTP and stream LLM responses to the browser. It must never block on slow I/O.

**Critical path for a chat message:**

```
1. Presidio redact(user_message)          ~30ms  sync, fail-open
2. INSERT message to Postgres             ~5ms
3. SELECT last 20 messages (context)      ~5ms
4. TrackedClient.stream(history)          open-ended
5. For each chunk:
   a. request.is_disconnected()?  → client.cancel()
   b. yield SSE event
6. INSERT assistant message               ~5ms
7. UPDATE session aggregates              ~5ms
   (InferenceEvent emitted to Redis inside SDK, step 4)
```

Steps 1-7 are all inside a single `AsyncSessionLocal` context. The SSE generator is a Python async generator wrapped in `StreamingResponse`.

**Why inline Presidio on user message (step 1)?**
The user message goes to Postgres at step 2. If we deferred PII cleaning to ingestion (as we do for previews), the raw PII would sit in the `messages` table permanently. Compliance requires the stored record to be clean. The ~30ms penalty is acceptable on the human-paced request cycle.

**Cancel detection:**
FastAPI's `request.is_disconnected()` is polled on every chunk iteration. When True, `client.cancel()` sets an internal flag; the SDK's stream loop checks it and breaks, emitting an `InferenceEvent` with `status="cancelled"`.

**Context window:**
Last 20 messages loaded from DB ordered by `sequence_num DESC LIMIT 20`, then reversed for chronological order. This caps token spend without requiring a summarization strategy.

**Why not inject the DB session via FastAPI `Depends`?**
The SSE generator runs inside `StreamingResponse`, which is returned before the generator executes. FastAPI's dependency lifecycle closes the session when the response is returned — before streaming starts. The generator opens its own `AsyncSessionLocal` to avoid this.

---

### 3. Redis Streams — Event Bus

Every completed LLM call (success, error, or cancel) produces one `InferenceEvent` JSON blob, published via XADD to the `llm-inference-logs` stream.

**Why Redis Streams over a task queue (Celery/RQ)?**
Redis Streams give consumer group semantics (at-least-once delivery, per-message ACK) without a separate broker. At this scale, Redis is already in the stack for session state; adding Kafka or RabbitMQ would be pure overhead.

**Why fire-and-forget from the SDK?**
The user is waiting for the SSE stream to finish. Adding a synchronous Redis write to the hot path would add latency. The emitter catches all exceptions internally and logs them — a Redis failure never surfaces to the user.

**Event schema (InferenceEvent):**

```python
class InferenceEvent(BaseModel):
    event_id: str              # uuid4
    event_version: str         # "1.0" — schema evolution
    session_id: str
    provider: str
    model: str
    sdk_version: str
    started_at: datetime
    completed_at: datetime | None
    latency_ms: int | None
    time_to_first_token_ms: int | None
    is_streaming: bool
    stream_chunks: int | None
    input_tokens: int | None
    output_tokens: int | None
    status: Literal["success", "error", "cancelled", "timeout"]
    error_code: str | None
    error_message: str | None
    input_preview: str | None    # 500 chars, truncated only (no Presidio here)
    output_preview: str | None   # 500 chars, truncated only
    provider_request_id: str | None
    client_metadata: dict
```

The `event_version` field future-proofs schema changes — the ingestion validator can branch on it.

---

### 4. Ingestion Service

Runs as a background `asyncio.Task` inside a FastAPI app (for the `/health` endpoint). Consumes from Redis Streams in batches.

**Consumer loop:**

```
loop:
  1. XAUTOCLAIM pending msgs older than 60s  ← crash recovery
     if any: process_batch()
  2. XREADGROUP streams={key: ">"} block=1s  ← new messages
     if any: process_batch()
```

**Why XAUTOCLAIM?**
If an ingestion pod crashes mid-batch, its pending entries (XREADGROUP delivered but not XACKed) sit in the PEL (Pending Entries List). On restart, XAUTOCLAIM reclaims them by idle time. This gives exactly-once write semantics — the writer uses `INSERT ... ON CONFLICT DO NOTHING` so re-processing a message is a no-op.

**Per-message processing:**

```
1. Pydantic validate raw Redis entry      fail-safe: log + XACK + skip
2. Presidio redact input_preview          fail-open: use original on error
3. Presidio redact output_preview         fail-open
4. Recompute latency_ms from timestamps   (SDK may have sent None on cancel)
5. INSERT inference_logs                  ON CONFLICT DO NOTHING
6. UPDATE chat_sessions SET total_tokens  only for status='success'
7. XACK message
```

Step 7 (XACK) happens after the write, not before. If the INSERT fails, the message stays in the PEL and is retried.

**REFRESH CONCURRENTLY:**
After every batch, the dashboard materialized view is refreshed. This runs in a separate connection with `isolation_level="AUTOCOMMIT"` — PostgreSQL requires `REFRESH MATERIALIZED VIEW CONCURRENTLY` to run outside a transaction. The unique index on `(hour_bucket, provider, model)` is required for concurrent refresh (without it, PostgreSQL falls back to an exclusive lock).

**Horizontal scaling:**
Running 2 ingestion replicas (Kubernetes deployment) divides stream throughput automatically. Both pods use the same consumer group name (`ingestion-workers`); Redis assigns each XREADGROUP call to different messages within the group. No coordination code needed.

---

### 5. PII Redaction — Two-Stage Strategy

| Stage | Service | What | Timing | Latency |
|---|---|---|---|---|
| 1 | API (inline) | User message `content` | Before Postgres write | ~30ms, blocks response |
| 2 | Ingestion (async) | `input_preview`, `output_preview`, `error_message` | After Redis consume | Zero user impact |
| 0 | SDK (truncation) | Both previews | Before XADD | <1ms |

**Stage 0 — SDK truncation:**
The SDK cuts previews to 500 chars before emitting. Not semantic redaction — just size control to keep Redis entries small. Semantic redaction happens in ingestion.

**Stage 1 — Inline on user message:**
Must be synchronous because the message hits Postgres immediately after. Fail-open: if Presidio is slow or down, the original text is stored and a warning is logged. This is a deliberate tradeoff — availability over perfect redaction on edge cases.

**Stage 2 — Async on previews:**
The `input_preview` / `output_preview` in `inference_logs` are for observability, not user-facing. Cleaning them async in ingestion adds zero latency to the chat flow. Presidio failures are also fail-open here.

**Entities detected:**
`EMAIL_ADDRESS`, `PHONE_NUMBER`, `PERSON`, `US_SSN`, `CREDIT_CARD`, `IP_ADDRESS`, `LOCATION`, `URL`, `IBAN_CODE`, `MEDICAL_LICENSE`

Replaced with `<REDACTED:ENTITY_TYPE>`.

---

### 6. Database Schema

#### `chat_sessions`
```sql
id            UUID PK
title         TEXT              -- auto-set from first 60 chars of first message
provider      TEXT
model         TEXT
status        TEXT              -- active | cancelled | archived
message_count INTEGER           -- incremented by API after each exchange
total_tokens  INTEGER           -- incremented by ingestion on success
created_at    TIMESTAMPTZ
updated_at    TIMESTAMPTZ
```

**Why denormalize `message_count` and `total_tokens`?**
The conversation list page shows these for every session. Computing them with COUNT/SUM on every page load against `messages` and `inference_logs` would be expensive at scale. The API increments `message_count` synchronously; ingestion increments `total_tokens` async (only on `status='success'` — cancelled/error calls don't contribute tokens).

#### `messages`
```sql
id            UUID PK
session_id    UUID FK → chat_sessions
role          TEXT     -- user | assistant | system
content       TEXT     -- PII-redacted before insert
sequence_num  INTEGER  -- used for ordering and context window slicing
```

**Why `sequence_num` over `created_at` for ordering?**
Two messages can have identical `created_at` (millisecond precision). `sequence_num` is assigned in the same transaction as the insert — guaranteed monotonic within a session.

#### `inference_logs`
```sql
id                     UUID PK
session_id             UUID FK (SET NULL on delete)
provider               TEXT
model                  TEXT
started_at             TIMESTAMPTZ
latency_ms             INTEGER
time_to_first_token_ms INTEGER
input_tokens           INTEGER
output_tokens          INTEGER
total_tokens           INTEGER GENERATED ALWAYS AS (input + output) STORED
status                 TEXT      -- success | error | cancelled | timeout
input_preview          TEXT      -- 500 chars, PII-redacted
output_preview         TEXT      -- 500 chars, PII-redacted
is_streaming           BOOLEAN
stream_chunks          INTEGER
```

**`total_tokens` as a generated column:**
Never out of sync with `input_tokens` / `output_tokens`. No application logic needed to keep it consistent. PostgreSQL computes it on write.

**`session_id` SET NULL on cascade:**
If a session is deleted, logs are retained for analytics. Deleting a conversation shouldn't erase throughput/latency history.

#### `dashboard_hourly_stats` (Materialized View)
```sql
hour_bucket     TIMESTAMPTZ   -- date_trunc('hour', started_at)
provider        TEXT
model           TEXT
request_count   BIGINT
error_count     BIGINT
avg_latency_ms  NUMERIC
p50_latency_ms  NUMERIC       -- PERCENTILE_CONT(0.50)
p95_latency_ms  NUMERIC
p99_latency_ms  NUMERIC
total_tokens    BIGINT
```

**Why a materialized view?**
`PERCENTILE_CONT` on a large `inference_logs` table is expensive — it sorts the entire column. Pre-aggregating by hour means dashboard reads are O(hours × providers) not O(rows). At 1000 requests/hour across 3 providers over 30 days, the view has ~2160 rows vs ~720,000 raw rows.

**Why REFRESH CONCURRENTLY?**
`REFRESH MATERIALIZED VIEW` without CONCURRENTLY takes an exclusive lock — all dashboard reads block during refresh. CONCURRENTLY builds a new version and swaps atomically. Requires the unique index on `(hour_bucket, provider, model)`.

**Staleness:**
View is 30s stale at most (refreshed after each ingestion batch, batches block up to 1s). For an observability dashboard this is acceptable. If sub-second freshness were required, we'd query `inference_logs` directly (with appropriate indexes).

---

### 7. Frontend

**Next.js 14 App Router** with a clean client/server split:

- `/conversations/[id]/page.tsx` — **server component**: fetches session + message history at request time (no loading spinner, history is available on first paint)
- `ChatWindow.tsx` — **client component**: owns the SSE stream state
- `/dashboard/DashboardClient.tsx` — **client component**: 30s polling via `setInterval`

**SSE streaming:**
Browser uses native `EventSource`. On cancel, `AbortController.abort()` closes the EventSource — the browser drops the TCP connection. The API detects this via `request.is_disconnected()` on the next chunk iteration and calls `client.cancel()`. The SDK emits `status="cancelled"` to Redis.

**Provider selector:**
State is local to `ChatWindow`. Changing provider mid-conversation is intentional — you can switch from Gemini to OpenAI on the next message in the same session. The session's `provider`/`model` columns reflect the value at creation; the stream endpoint accepts provider/model as query params per-request.

---

### 8. Kubernetes

**Why StatefulSet for Postgres?**
Postgres needs a stable network identity and persistent storage. StatefulSet provides both: stable DNS (`postgres-0.postgres.chatbot.svc`) and a PVC that survives pod restarts. A Deployment would get a new pod name on restart — the PVC attachment could fail.

**Why headless Service for Postgres?**
`clusterIP: None` means DNS resolves directly to the pod IP, not through a virtual IP. Required for StatefulSet stable DNS. Other services use `clusterIP: ClusterIP` (default) with kube-proxy load balancing.

**HPA on API service:**
```
minReplicas: 1  maxReplicas: 5  targetCPU: 70%
scaleDown stabilizationWindow: 300s
```
LLM streaming is CPU-light (mostly network I/O waiting for tokens). The HPA trigger is CPU because that's what `metrics-server` provides out of the box. In production you'd add a custom metric on active SSE connections. The 5-minute scaleDown window prevents thrashing during bursty LLM traffic.

**Why 2 ingestion replicas?**
Redis consumer groups partition stream delivery automatically — two pods in the same group each receive different messages. No application-level coordination. Adding a third replica is `kubectl scale deployment/ingestion --replicas=3`.

**startupProbe on API:**
Alembic migrations run before uvicorn starts. On a cold cluster, migration can take 30-60s (schema creation, index building). The liveness probe's `initialDelaySeconds: 30` would kill the container mid-migration. `startupProbe` with `failureThreshold: 120` × `periodSeconds: 5` = 10-minute window lets migrations finish before liveness/readiness probes activate.

**Ingress SSE config:**
```yaml
nginx.ingress.kubernetes.io/proxy-buffering: "off"
nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
chunked_transfer_encoding: on
```
nginx buffers responses by default — this would accumulate all SSE chunks and deliver them at once (defeating streaming). `proxy-buffering: off` forces chunk-by-chunk forwarding. `proxy-read-timeout: 3600` prevents nginx from closing long-lived SSE connections.

---

## Tradeoffs Summary

| Decision | Chosen | Rejected | Reason |
|---|---|---|---|
| Event bus | Redis Streams | Kafka, RabbitMQ | Already in stack; same consumer group semantics; zero extra infra |
| Ingestion timing | Async (separate service) | Inline in API | SSE hot path must not block on Presidio + Postgres write latency |
| Dashboard storage | Materialized view | Live query | Sub-ms reads; percentile aggregation on raw table is expensive |
| PII on user message | Sync inline | Async | Message hits DB immediately; compliance requires clean storage |
| ORM for ingestion writes | Raw SQL | SQLAlchemy ORM | Bulk INSERT and AUTOCOMMIT REFRESH can't be expressed cleanly in ORM |
| Primary keys | UUID v4 | ULID | Range queries use `created_at` indexes; ULID sortability provides no benefit |
| Context window | Last 20 messages | Full history | Token cost control; no summarization needed at this scale |

---

## What I Would Do Differently in Production

- **Auth** — JWT or session cookies before any public exposure; currently no authentication
- **Rate limiting** — per-user token budget to cap API spend; `slowapi` middleware on the stream endpoint
- **Cost tracking** — store per-model $/1k-token rates in a config table; ingestion computes `cost_usd` per call; dashboard shows spend over time
- **Retry with backoff** — SDK propagates provider errors directly; add exponential backoff with jitter for 429/503 before surfacing to user
- **Redis persistence in k8s** — current manifest uses `emptyDir` for Redis data volume; a production deploy needs a PVC to survive pod eviction
- **Dead-letter queue** — messages that fail ingestion after N retries (e.g. malformed JSON from a buggy SDK version) currently get XACKed and dropped; a DLQ stream would retain them for inspection
- **Schema migrations in init container** — running Alembic in the app container requires a startupProbe hack; a proper init container runs migrations once before the main container starts, with no timeout risk
- **Metrics endpoint** — expose Prometheus `/metrics` from API and ingestion; feed into Grafana instead of the custom dashboard for production observability
