# Mockups & Placeholders to Fix

## API Keys (not real)
- `ANTHROPIC_API_KEY=sk-ant-...` — placeholder in `.env` / `.env.example`
- `OPENAI_API_KEY=sk-...` — placeholder in `.env` / `.env.example`
- `GOOGLE_API_KEY=AIza...` — placeholder in `.env` / `.env.example`
- **Fix:** Add real keys to `.env` before testing live LLM calls

---

## Stage 4 Test Data (synthetic, not real SDK flow)
- Published fake `InferenceEvent` JSON directly to Redis via `redis-cli XADD`
- Bypassed TrackedClient, no real LLM call made
- `input_preview="Hello world"`, `output_preview="Hi there! I am Gemini."` — hardcoded strings
- `session_id` reused from earlier session (`8f78cc1b-...`)
- **Fix:** Test with real Gemini/OpenAI key → full flow: chat endpoint → SDK → Redis → ingestion → Postgres

---

## Frontend (built — needs live API key to fully test)
- Next.js app built and dev server verified (200 on `/conversations`, `/conversations/[id]`, `/dashboard`) ✅
- `streamChat` uses `EventSource` — browser-native SSE, no polyfill needed
- Cancel flow: `AbortController.abort()` → closes EventSource → backend `request.is_disconnected()` → logs `cancelled`
- `/dashboard` fully built — Recharts LatencyChart, ThroughputChart, ErrorRateChart, MetricCards, 30s polling ✅
- **Fix needed:** Add real `GOOGLE_API_KEY` to `.env`, test full stream → cancel → resume flow in browser

---

## Stage 3 Live Stream (not verified with real key)
- SSE endpoint confirmed routing works (got 401 from Anthropic = correct path)
- User message stored to Postgres ✅
- But full streaming + assistant message storage + Redis emit never verified end-to-end with real key
- **Fix:** Add real `GOOGLE_API_KEY`, restart API, run:
  ```bash
  SESSION_ID=$(curl -s -X POST http://localhost:8000/sessions \
    -H "Content-Type: application/json" \
    -d '{"provider":"gemini","model":"gemini-1.5-flash"}' \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
  curl -N "http://localhost:8000/sessions/${SESSION_ID}/stream?user_message=Hello&provider=gemini&model=gemini-1.5-flash"
  ```

---

## Dashboard Materialized View Data
- `dashboard_hourly_stats` has 2 rows: 1 real error event (Anthropic auth fail) + 1 synthetic success event
- Not representative of real traffic
- **Fix:** Real data populates naturally once live LLM calls work

---

## Things Verified as Real (no mockups)
- Postgres schema + migrations ✅
- Redis Streams consumer group + XAUTOCLAIM ✅
- Presidio PII redaction (tested with `john@example.com` → `<REDACTED:EMAIL_ADDRESS>`) ✅
- Session CRUD endpoints ✅
- Ingestion pipeline (Redis → Postgres flow) ✅
- `dashboard_hourly_stats` REFRESH CONCURRENTLY ✅
