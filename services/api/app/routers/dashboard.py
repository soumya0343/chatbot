from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

RANGE_HOURS = {"1h": 1, "6h": 6, "24h": 24, "7d": 168, "30d": 720}


@router.get("/stats")
async def get_stats(
    range: Literal["1h", "6h", "24h", "7d", "30d"] = Query(default="24h"),
    provider: str = Query(default="all"),
    db: AsyncSession = Depends(get_db),
):
    hours = RANGE_HOURS[range]
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    provider_filter = "" if provider == "all" else "AND provider = :provider"

    # Timeseries from materialized view (fast, ~0ms)
    ts_rows = await db.execute(
        text(f"""
            SELECT
                hour_bucket,
                provider,
                model,
                request_count,
                error_count,
                ROUND(avg_latency_ms) AS avg_latency_ms,
                ROUND(p50_latency_ms) AS p50_latency_ms,
                ROUND(p95_latency_ms) AS p95_latency_ms,
                ROUND(p99_latency_ms) AS p99_latency_ms,
                total_tokens,
                total_input_tokens,
                total_output_tokens
            FROM dashboard_hourly_stats
            WHERE hour_bucket >= :since
            {provider_filter}
            ORDER BY hour_bucket ASC
        """),
        {"since": since, "provider": provider} if provider != "all" else {"since": since},
    )
    timeseries = [dict(row._mapping) for row in ts_rows]

    # Aggregate totals from raw inference_logs (includes current partial hour)
    agg_rows = await db.execute(
        text(f"""
            SELECT
                COUNT(*)                                            AS total_requests,
                COUNT(*) FILTER (WHERE status = 'error')           AS total_errors,
                COUNT(*) FILTER (WHERE status = 'cancelled')       AS total_cancelled,
                ROUND(AVG(latency_ms))                             AS avg_latency_ms,
                ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY latency_ms)) AS p50_latency_ms,
                ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms)) AS p95_latency_ms,
                ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms)) AS p99_latency_ms,
                COALESCE(SUM(input_tokens + output_tokens), 0)     AS total_tokens,
                COALESCE(SUM(input_tokens), 0)                     AS total_input_tokens,
                COALESCE(SUM(output_tokens), 0)                    AS total_output_tokens
            FROM inference_logs
            WHERE started_at >= :since
              AND completed_at IS NOT NULL
            {provider_filter}
        """),
        {"since": since, "provider": provider} if provider != "all" else {"since": since},
    )
    agg = dict(agg_rows.mappings().one())

    # Per-provider breakdown
    provider_rows = await db.execute(
        text("""
            SELECT
                provider,
                COUNT(*)                                       AS request_count,
                COUNT(*) FILTER (WHERE status = 'error')      AS error_count,
                ROUND(AVG(latency_ms))                         AS avg_latency_ms,
                COALESCE(SUM(input_tokens + output_tokens), 0) AS total_tokens
            FROM inference_logs
            WHERE started_at >= :since AND completed_at IS NOT NULL
            GROUP BY provider
            ORDER BY request_count DESC
        """),
        {"since": since},
    )
    by_provider = [dict(row._mapping) for row in provider_rows]

    # Serialize datetimes in timeseries
    for row in timeseries:
        if isinstance(row.get("hour_bucket"), datetime):
            row["hour_bucket"] = row["hour_bucket"].isoformat()

    return {
        "range": range,
        "provider_filter": provider,
        "since": since.isoformat(),
        "totals": {k: (float(v) if v is not None else None) for k, v in agg.items()},
        "timeseries": timeseries,
        "by_provider": by_provider,
    }
