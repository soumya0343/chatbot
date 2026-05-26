# Mockups & Placeholders to Fix

## API Keys — RESOLVED ✅
- `GOOGLE_API_KEY` added to `.env` — real key, verified working
- Use model `gemini-2.5-flash` (gemini-1.5-flash deprecated, gemini-2.0-flash free tier limit=0)
- `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` still placeholders — not tested

---

## Full Pipeline — VERIFIED ✅ (2026-05-26)
Real end-to-end test with `gemini-2.5-flash`:
- SSE stream delivers chunks ✅
- `inference_logs` written: `latency_ms=1929`, `time_to_first_token_ms=1926`, `input_tokens=6`, `output_tokens=2` ✅
- Both messages stored in Postgres ✅
- Session `total_tokens`, `message_count`, `title` all updated ✅
- `dashboard_hourly_stats` refreshed with real row ✅

---

## PII Redaction — VERIFIED ✅
- Sent: `"My email is test@example.com and my name is John Smith"`
- Stored in DB: `"My email is <REDACTED:EMAIL_ADDRESS> and my name is <REDACTED:PERSON>"` ✅

---

## Kubernetes (manifests only — not cluster-tested)
- `kubectl kustomize k8s/` renders all 19 resources cleanly ✅
- No live cluster available for `kubectl apply` test
- **Fix before deploy:**
  1. Fill real passwords in `k8s/postgres/secret.yaml`
  2. Fill real API keys in `k8s/api/secret.yaml`
  3. Build + push images: `docker build -t chatbot/api:latest -f services/api/Dockerfile .` etc.
  4. `kubectl apply -k k8s/`
  5. Ingresss requires nginx-ingress-controller installed on cluster

---

## Things Verified as Real (no mockups)
- Postgres schema + migrations ✅
- Redis Streams consumer group + XAUTOCLAIM ✅
- Presidio PII redaction (tested with `john@example.com` → `<REDACTED:EMAIL_ADDRESS>`) ✅
- Session CRUD endpoints ✅
- Ingestion pipeline (Redis → Postgres flow) ✅
- `dashboard_hourly_stats` REFRESH CONCURRENTLY ✅
- Next.js build passes, `/conversations` + `/dashboard` serve 200 ✅
- `kubectl kustomize k8s/` — all 19 k8s resources render without errors ✅
