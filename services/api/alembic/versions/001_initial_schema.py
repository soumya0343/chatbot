"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-25
"""
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    op.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            title         TEXT,
            provider      TEXT NOT NULL,
            model         TEXT NOT NULL,
            status        TEXT NOT NULL DEFAULT 'active',
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            message_count INTEGER NOT NULL DEFAULT 0,
            total_tokens  INTEGER NOT NULL DEFAULT 0,
            metadata      JSONB DEFAULT '{}'::jsonb
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON chat_sessions(created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status ON chat_sessions(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessions_provider ON chat_sessions(provider)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            session_id      UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
            role            TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
            content         TEXT NOT NULL,
            content_preview TEXT,
            sequence_num    INTEGER NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            metadata        JSONB DEFAULT '{}'::jsonb
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_sequence ON messages(session_id, sequence_num)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS inference_logs (
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
                                       COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)
                                   ) STORED,
            status                 TEXT NOT NULL DEFAULT 'success'
                                       CHECK (status IN ('success', 'error', 'cancelled', 'timeout')),
            error_code             TEXT,
            error_message          TEXT,
            input_preview          TEXT,
            output_preview         TEXT,
            is_streaming           BOOLEAN NOT NULL DEFAULT FALSE,
            stream_chunks          INTEGER,
            sdk_version            TEXT,
            client_metadata        JSONB DEFAULT '{}'::jsonb,
            created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_inference_logs_session_id ON inference_logs(session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_inference_logs_started_at ON inference_logs(started_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_inference_logs_provider ON inference_logs(provider)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_inference_logs_status ON inference_logs(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_inference_logs_latency ON inference_logs(latency_ms)")

    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS dashboard_hourly_stats AS
        SELECT
            date_trunc('hour', started_at)  AS hour_bucket,
            provider,
            model,
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
        WITH DATA
    """)
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS dashboard_hourly_stats_bucket_idx "
        "ON dashboard_hourly_stats(hour_bucket, provider, model)"
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS dashboard_hourly_stats")
    op.execute("DROP TABLE IF EXISTS inference_logs")
    op.execute("DROP TABLE IF EXISTS messages")
    op.execute("DROP TABLE IF EXISTS chat_sessions")
