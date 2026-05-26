# Build Checklist

> Docs live in `.claude/` — CHECKLIST.md, MOCKUPS.md, PLAN.md

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
- [x] `services/api/entrypoint.sh` — runs `alembic upgrade head` only when SYNC_DATABASE_URL is set
- [x] `services/api/Dockerfile`
- [x] `services/api/app/config.py` — pydantic-settings
- [x] `services/ingestion/pyproject.toml`
- [x] `services/ingestion/Dockerfile`
- [x] `frontend/Dockerfile` — placeholder (real app built in Stage 5)
- [x] `packages/llm-sdk/pyproject.toml`
- [x] Docker verified: postgres (5432) ✅ redis (6380) ✅ presidio (8080) ✅ api (8000) ✅
- [x] DB schema verified: all 3 tables + materialized view created
- [x] PII redaction tested: `john@example.com` → `<REDACTED:EMAIL_ADDRESS>`

---

## Stage 2 — Internal SDK (llm-sdk package) ✅
- [x] `packages/llm-sdk/llm_sdk/models.py` — InferenceEvent, ChatMessage, StreamChunk, ProviderMeta, TokenUsage
- [x] `packages/llm-sdk/llm_sdk/providers/base.py` — BaseProvider ABC
- [x] `packages/llm-sdk/llm_sdk/providers/anthropic.py` — streaming + non-streaming
- [x] `packages/llm-sdk/llm_sdk/providers/openai.py`
- [x] `packages/llm-sdk/llm_sdk/providers/gemini.py`
- [x] `packages/llm-sdk/llm_sdk/emitter.py` — Redis Streams XADD (never raises)
- [x] `packages/llm-sdk/llm_sdk/pii.py` — fast local 500-char truncation
- [x] `packages/llm-sdk/llm_sdk/streaming.py` — StreamingTracker with TTFT measurement
- [x] `packages/llm-sdk/llm_sdk/client.py` — TrackedClient orchestrator
- [x] `packages/llm-sdk/llm_sdk/__init__.py` — exports TrackedClient, ChatMessage, InferenceEvent, StreamChunk
- [x] Smoke test passed: imports, truncation, tracker, invalid provider, InferenceEvent serialization

---

## Stage 3 — API Service (FastAPI) ✅
- [x] `services/api/app/database.py` — SQLAlchemy async engine + session factory
- [x] `services/api/app/models/session.py` — ChatSession ORM
- [x] `services/api/app/models/message.py` — Message ORM
- [x] `services/api/app/models/inference_log.py` — InferenceLog ORM (read-only from API)
- [x] `services/api/app/schemas/session.py` — SessionCreate, SessionResponse, MessageResponse, SessionWithMessages
- [x] `services/api/app/dependencies.py` — DB session, Redis, Presidio client deps
- [x] `services/api/app/routers/sessions.py` — POST/GET/PATCH/DELETE + messages endpoint
- [x] `services/api/app/routers/chat.py` — SSE stream, PII inline redact, cancel detection, Redis publish
- [x] `services/api/app/routers/health.py` — /health with DB + Redis ping
- [x] `services/api/app/main.py` — lifespan (Redis pool + httpx client), CORS, all routers
- [x] Session CRUD all verified ✅
- [x] User message stored to Postgres before stream starts ✅
- [x] Auto-title on first message ✅
- [x] SSE routing verified (got 401 = API reached Anthropic correctly) ⚠️ needs real key — see MOCKUPS.md

---

## Stage 4 — Ingestion Service ✅
- [x] `services/ingestion/app/config.py`
- [x] `services/ingestion/app/database.py`
- [x] `services/ingestion/app/validator.py` — parse + fail-safe on bad payloads
- [x] `services/ingestion/app/pii_client.py` — async HTTP → Presidio, fail-open
- [x] `services/ingestion/app/extractor.py` — PII-redact previews + recompute latency_ms
- [x] `services/ingestion/app/writer.py` — bulk INSERT raw SQL + UPDATE session tokens + REFRESH CONCURRENTLY (AUTOCOMMIT conn)
- [x] `services/ingestion/app/consumer.py` — XREADGROUP loop + XAUTOCLAIM PEL claim on restart
- [x] `services/ingestion/app/main.py` — lifespan starts consumer as background asyncio task
- [x] Pipeline verified with synthetic event ⚠️ needs real key for live test — see MOCKUPS.md
- [x] inference_logs written ✅ session total_tokens updated ✅ dashboard view refreshed ✅

---

## Stage 5 — Frontend Core ✅
- [x] Next.js 14 App Router scaffold with Tailwind + shadcn/ui (shadcn v4 + base-ui components)
- [x] `frontend/lib/api.ts` — typed fetch client (Session, Message, SessionWithMessages types + streamChat)
- [x] `frontend/hooks/useChat.ts` — SSE stream + AbortController cancel
- [x] `frontend/hooks/useConversations.ts` — list + delete sessions
- [x] `frontend/app/conversations/page.tsx` — list all sessions + new chat button
- [x] `frontend/app/conversations/[id]/page.tsx` — chat window + resume (loads history server-side)
- [x] `frontend/components/chat/ChatWindow.tsx` — full chat layout with provider bar
- [x] `frontend/components/chat/MessageBubble.tsx` — user/assistant bubbles + streaming cursor
- [x] `frontend/components/chat/MessageInput.tsx` — Enter to send, Shift+Enter newline, cancel button
- [x] `frontend/components/chat/ProviderSelector.tsx` — Gemini | OpenAI | Anthropic + model dropdown
- [x] Cancel button → AbortController.abort() → EventSource closes → backend detects disconnect
- [x] `frontend/app/layout.tsx` — nav header with Conversations + Dashboard links
- [x] `frontend/app/dashboard/page.tsx` — placeholder (Stage 6)
- [x] `frontend/next.config.mjs` — output: standalone, API rewrite
- [x] `frontend/Dockerfile` — multi-stage build with standalone output
- [x] Build verified: `npm run build` passes ✅, dev server responds 200 ✅

---

## Stage 6 — Analytics Dashboard ✅
- [x] `services/api/app/routers/dashboard.py` — GET /dashboard/stats?range=&provider=
  - Queries `dashboard_hourly_stats` materialized view for timeseries
  - Live aggregate totals from `inference_logs` (includes current partial hour)
  - Per-provider breakdown table
- [x] `frontend/app/dashboard/page.tsx` + `DashboardClient.tsx` — "use client" split
- [x] `frontend/hooks/useDashboard.ts` — 30s polling with setInterval
- [x] `frontend/components/dashboard/LatencyChart.tsx` — Recharts LineChart p50/p95/p99
- [x] `frontend/components/dashboard/ThroughputChart.tsx` — stacked BarChart per provider
- [x] `frontend/components/dashboard/ErrorRateChart.tsx` — AreaChart error %
- [x] `frontend/components/dashboard/MetricCard.tsx` — total requests, error rate, avg latency, tokens
- [x] Range selector: 1h / 6h / 24h / 7d / 30d buttons
- [x] Manual refresh button
- [x] Per-provider breakdown table
- [x] Build verified: `npm run build` passes ✅, /dashboard responds 200 ✅

---

## Stage 7 — Kubernetes Manifests ✅
- [x] `k8s/namespace.yaml` — namespace: chatbot
- [x] `k8s/postgres/secret.yaml` — POSTGRES_PASSWORD, DATABASE_URL, SYNC_DATABASE_URL
- [x] `k8s/postgres/pvc.yaml` — 10Gi ReadWriteOnce
- [x] `k8s/postgres/service.yaml` — headless ClusterIP for StatefulSet DNS
- [x] `k8s/postgres/statefulset.yaml` — postgres:16-alpine, readiness/liveness probes
- [x] `k8s/redis/configmap.yaml` — redis.conf (appendonly, maxmemory 512mb, allkeys-lru)
- [x] `k8s/redis/service.yaml`
- [x] `k8s/redis/deployment.yaml` — redis:7-alpine, mounts config from ConfigMap
- [x] `k8s/presidio/deployment.yaml` — 30s readiness (spaCy model load), 1.5Gi limit
- [x] `k8s/presidio/service.yaml`
- [x] `k8s/api/secret.yaml` — LLM API keys (fill before deploy)
- [x] `k8s/api/deployment.yaml` — pulls DB/Redis/Presidio URLs from secrets
- [x] `k8s/api/service.yaml`
- [x] `k8s/api/hpa.yaml` — min=1, max=5, CPU=70%, scaleDown stabilize 5min
- [x] `k8s/ingestion/deployment.yaml` — replicas=2 (consumer group scales horizontally)
- [x] `k8s/frontend/deployment.yaml`
- [x] `k8s/frontend/service.yaml`
- [x] `k8s/frontend/ingress.yaml` — nginx, SSE proxy-buffering off, routes /sessions + /dashboard → api
- [x] `k8s/kustomization.yaml` — 19 resources, all in chatbot namespace
- [x] Validated: `kubectl kustomize k8s/` → all 19 resources render cleanly ✅

---

## Bonus Deliverables Tracker
- [x] Multi-provider support — Anthropic + OpenAI + Gemini in SDK ✅
- [x] Streaming responses — TrackedClient.stream() + SSE endpoint ✅
- [x] Event-based architecture — Redis Streams XADD + XREADGROUP ✅
- [x] PII redaction — Presidio sidecar + 2-stage strategy ✅
- [x] Cancel mid-stream — AbortController + backend disconnect detection ✅
- [x] Resume conversation — history loaded server-side on /conversations/[id] ✅
- [x] Latency + Throughput + Error dashboards ✅
- [ ] Docker Compose one-command setup — needs real API key to test full flow
- [x] Self-hosted k8s manifests ✅ (`kubectl kustomize k8s/` validated, 19 resources)

---

## Mockups / Placeholders
> Full list in `.claude/MOCKUPS.md`
- [x] Real `GOOGLE_API_KEY` added → full pipeline verified end-to-end ✅
- [x] Stage 3 SSE verified with real Gemini response ✅
- [x] Stage 4 verified with real SDK flow (not synthetic) ✅
- [x] PII redaction verified on real message ✅
- [ ] `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` — still placeholders (not needed)

---

## Final Deliverables
- [x] `README.md` — quick start, architecture diagram, schema decisions, PII strategy, k8s deploy, tradeoffs, future improvements ✅
- [ ] Demo (screenshots / Loom) — needs real API key
- [ ] GitHub repo public + pushed
