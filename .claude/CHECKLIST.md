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
- [x] Multi-provider support — Anthropic + OpenAI + Gemini in SDK ✅
- [x] Streaming responses — TrackedClient.stream() + SSE endpoint ✅
- [x] Event-based architecture — Redis Streams XADD + XREADGROUP ✅
- [x] PII redaction — Presidio sidecar + 2-stage strategy ✅
- [x] Cancel mid-stream — AbortController + backend disconnect detection ✅
- [x] Resume conversation — history loaded server-side on /conversations/[id] ✅
- [ ] Latency + Throughput + Error dashboards — Stage 6
- [ ] Docker Compose one-command setup — needs real API key to test full flow
- [ ] Self-hosted k8s — Stage 7

---

## Mockups / Placeholders ⚠️
> Full list in `.claude/MOCKUPS.md`
- [ ] Real `GOOGLE_API_KEY` in `.env` → test live Gemini stream end-to-end
- [ ] Real `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` if needed
- [ ] Stage 3 SSE not verified with real LLM response
- [ ] Stage 4 tested with synthetic data only

---

## Final Deliverables
- [ ] `README.md` — setup, architecture, schema decisions, tradeoffs, future improvements
- [ ] Architecture notes doc
- [ ] Demo (hosted link / screenshots / Loom)
- [ ] GitHub repo public + pushed
