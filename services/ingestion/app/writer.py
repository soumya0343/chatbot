import logging

from sqlalchemy import text

from .database import AsyncSessionLocal, engine

logger = logging.getLogger(__name__)

_INSERT_LOG = text("""
    INSERT INTO inference_logs (
        id, session_id, provider, model, provider_request_id,
        started_at, completed_at, latency_ms, time_to_first_token_ms,
        input_tokens, output_tokens,
        status, error_code, error_message,
        input_preview, output_preview,
        is_streaming, stream_chunks, sdk_version, client_metadata
    ) VALUES (
        :id, :session_id, :provider, :model, :provider_request_id,
        :started_at, :completed_at, :latency_ms, :time_to_first_token_ms,
        :input_tokens, :output_tokens,
        :status, :error_code, :error_message,
        :input_preview, :output_preview,
        :is_streaming, :stream_chunks, :sdk_version, :client_metadata
    )
    ON CONFLICT (id) DO NOTHING
""")

_UPDATE_TOKENS = text("""
    UPDATE chat_sessions
    SET total_tokens = total_tokens + :tokens,
        updated_at   = NOW()
    WHERE id = :session_id
""")

_REFRESH_VIEW = text("REFRESH MATERIALIZED VIEW CONCURRENTLY dashboard_hourly_stats")


async def write_batch(rows: list[dict]) -> None:
    """Bulk-insert inference_logs rows and update session token aggregates."""
    if not rows:
        return

    async with AsyncSessionLocal() as db:
        # 1. Bulk insert — cast client_metadata to JSON string for asyncpg
        for row in rows:
            if isinstance(row.get("client_metadata"), dict):
                import json
                row["client_metadata"] = json.dumps(row["client_metadata"])
        await db.execute(_INSERT_LOG, rows)

        # 2. Aggregate tokens per session and update
        session_tokens: dict[str, int] = {}
        for row in rows:
            sid = row.get("session_id")
            if sid and row.get("status") == "success":
                tokens = (row.get("input_tokens") or 0) + (row.get("output_tokens") or 0)
                session_tokens[sid] = session_tokens.get(sid, 0) + tokens

        for session_id, tokens in session_tokens.items():
            await db.execute(_UPDATE_TOKENS, {"session_id": session_id, "tokens": tokens})

        await db.commit()

    # 3. Refresh materialized view — must run outside transaction (AUTOCOMMIT)
    await _refresh_dashboard()


async def _refresh_dashboard() -> None:
    try:
        async with engine.connect() as conn:
            await conn.execution_options(isolation_level="AUTOCOMMIT")
            await conn.execute(_REFRESH_VIEW)
    except Exception as e:
        # Non-fatal — dashboard will be slightly stale until next batch
        logger.warning(f"Dashboard view refresh failed: {e}")
