# Build Checklist

## Stage 1 — Infrastructure Foundation ✅
- [x] Directory structure created
- [x] `docker-compose.yml` — postgres, redis, presidio, api, ingestion, frontend
- [x] `docker-compose.override.yml` — dev hot-reload + pgAdmin profile
- [x] `.env.example`
- [x] `.gitignore`
- [x] `services/presidio/app.py` — PII redaction via presidio-analyzer + presidio-anonymizer
- [x] `services/presidio/Dockerfile`
- [x] `services/presidio/requirements.txt`
- [x] `services/api/pyproject.toml` — all deps including psycopg2-binary
- [x] `services/api/alembic.ini`
- [x] `services/api/alembic/env.py` — reads SYNC_DATABASE_URL from env
- [x] `services/api/alembic/versions/001_initial_schema.py` — chat_sessions, messages, inference_logs, dashboard_hourly_stats materialized view
- [x] `services/api/entrypoint.sh` — runs `alembic upgrade head` before server starts
- [x] `services/api/Dockerfile`
- [x] `services/api/app/main.py` — placeholder FastAPI app with /health
- [x] `services/api/app/config.py` — pydantic-settings
- [x] `services/ingestion/pyproject.toml`
- [x] `services/ingestion/Dockerfile`
- [x] `services/ingestion/app/main.py` — placeholder with /health
- [x] `frontend/Dockerfile`
- [x] `packages/llm-sdk/pyproject.toml`
- [x] `packages/llm-sdk/llm_sdk/__init__.py`
- [x] Docker verified: postgres (5432) ✅ redis (6380) ✅ presidio (8080) ✅ api (8000) ✅
- [x] DB schema verified: all 3 tables + materialized view created
- [x] PII redaction tested: `john@example.com` → `<REDACTED:EMAIL_ADDRESS>`

---

## Stage 2 — Internal SDK (llm-sdk package) ⬜
- [ ] `packages/llm-sdk/llm_sdk/models.py` — InferenceEvent, ChatMessage, StreamChunk, ProviderMeta, TokenUsage
- [ ] `packages/llm-sdk/llm_sdk/providers/base.py` — BaseProvider ABC
- [ ] `packages/llm-sdk/llm_sdk/providers/anthropic.py` — streaming + non-streaming
- [ ] `packages/llm-sdk/llm_sdk/providers/openai.py`
- [ ] `packages/llm-sdk/llm_sdk/providers/gemini.py`
- [ ] `packages/llm-sdk/llm_sdk/emitter.py` — Redis Streams XADD publisher
- [ ] `packages/llm-sdk/llm_sdk/pii.py` — fast local 500-char truncation
- [ ] `packages/llm-sdk/llm_sdk/streaming.py` — AsyncIterator wrapper + TTFT measurement
- [ ] `packages/llm-sdk/llm_sdk/client.py` — TrackedClient orchestrator
- [ ] Smoke test: each provider returns response + InferenceEvent published to Redis

---

## Stage 3 — API Service (FastAPI) ⬜
- [ ] `services/api/app/database.py` — SQLAlchemy async engine + session factory
- [ ] `services/api/app/models/session.py` — ChatSession ORM
- [ ] `services/api/app/models/message.py` — Message ORM
- [ ] `services/api/app/models/inference_log.py` — InferenceLog ORM
- [ ] `services/api/app/schemas/` — Pydantic request/response schemas
- [ ] `services/api/app/dependencies.py` — DB session, Redis deps
- [ ] `services/api/app/routers/sessions.py` — POST/GET/DELETE /sessions
- [ ] `services/api/app/routers/chat.py` — SSE streaming endpoint (cancel detection, PII inline, Redis publish)
- [ ] `services/api/app/routers/health.py` — /health with DB + Redis ping
- [ ] Integration test: curl SSE stream endpoint, verify chunks + DB write

---

## Stage 4 — Ingestion Service ⬜
- [ ] `services/ingestion/app/config.py`
- [ ] `services/ingestion/app/database.py`
- [ ] `services/ingestion/app/validator.py` — Pydantic parse raw Redis entry
- [ ] `services/ingestion/app/pii_client.py` — async HTTP → Presidio sidecar
- [ ] `services/ingestion/app/extractor.py` — compute latency_ms, derived fields
- [ ] `services/ingestion/app/writer.py` — bulk insert inference_logs + UPDATE session aggregates + REFRESH CONCURRENTLY
- [ ] `services/ingestion/app/consumer.py` — XREADGROUP loop, batch=50, PEL claim on restart
- [ ] Test: send message → verify inference_logs row in Postgres

---

## Stage 5 — Frontend Core ⬜
- [ ] Next.js 14 App Router scaffold with Tailwind + shadcn/ui
- [ ] `src/lib/api.ts` — typed fetch client
- [ ] `src/hooks/useChat.ts` — SSE stream + AbortController cancel
- [ ] `src/hooks/useConversations.ts`
- [ ] `src/app/conversations/page.tsx` — list all sessions
- [ ] `src/app/conversations/[id]/page.tsx` — chat window + resume
- [ ] `src/components/chat/ChatWindow.tsx`
- [ ] `src/components/chat/MessageBubble.tsx`
- [ ] `src/components/chat/MessageInput.tsx`
- [ ] `src/components/chat/ProviderSelector.tsx` — Anthropic | OpenAI | Gemini + model picker
- [ ] Cancel button → abort SSE → backend logs `cancelled`
- [ ] Test: create session, stream, cancel mid-stream, resume

---

## Stage 6 — Analytics Dashboard ⬜
- [ ] `services/api/app/routers/dashboard.py` — GET /dashboard/stats
- [ ] `src/app/dashboard/page.tsx`
- [ ] `src/hooks/useDashboard.ts` — 30s polling
- [ ] `src/components/dashboard/LatencyChart.tsx` — Recharts LineChart p50/p95/p99
- [ ] `src/components/dashboard/ThroughputChart.tsx` — BarChart requests/hour
- [ ] `src/components/dashboard/ErrorRateChart.tsx` — AreaChart error %
- [ ] `src/components/dashboard/MetricCard.tsx` — total requests, avg latency, tokens, errors

---

## Stage 7 — Kubernetes Manifests ⬜
- [ ] `k8s/namespace.yaml`
- [ ] `k8s/postgres/` — StatefulSet, PVC, Service, Secret
- [ ] `k8s/redis/` — Deployment, Service, ConfigMap
- [ ] `k8s/presidio/` — Deployment, Service
- [ ] `k8s/api/` — Deployment, Service, HPA (min=1, max=5, CPU=70%)
- [ ] `k8s/ingestion/` — Deployment (replicas=2)
- [ ] `k8s/frontend/` — Deployment, Service, Ingress
- [ ] `k8s/kustomization.yaml`
- [ ] Test: `kubectl apply -k k8s/` all pods running

---

## Bonus Deliverables Tracker
- [x] Multi-provider support (planned in SDK) — Stage 2
- [x] Streaming responses (planned in API + frontend) — Stage 3 + 5
- [x] Event-based architecture (Redis Streams) — Stage 1 infra ready
- [x] PII redaction (Presidio sidecar running) — Stage 1 ✅
- [ ] Latency + Throughput + Error dashboards — Stage 6
- [ ] Docker Compose one-command setup — Stage 1 ✅ (needs frontend scaffold first)
- [ ] Self-hosted k8s — Stage 7

---

## Final Deliverables
- [ ] `README.md` — setup instructions, architecture overview, schema decisions, tradeoffs, future improvements
- [ ] Architecture notes doc
- [ ] Demo (hosted link / screenshots / Loom)
- [ ] GitHub repo public + pushed
