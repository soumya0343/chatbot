"use client";

import { useState, useEffect, useCallback, useRef } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface DashboardTotals {
  total_requests: number | null;
  total_errors: number | null;
  total_cancelled: number | null;
  avg_latency_ms: number | null;
  p50_latency_ms: number | null;
  p95_latency_ms: number | null;
  p99_latency_ms: number | null;
  total_tokens: number | null;
  total_input_tokens: number | null;
  total_output_tokens: number | null;
}

export interface TimeseriesRow {
  hour_bucket: string;
  provider: string;
  model: string;
  request_count: number;
  error_count: number;
  avg_latency_ms: number | null;
  p50_latency_ms: number | null;
  p95_latency_ms: number | null;
  p99_latency_ms: number | null;
  total_tokens: number;
}

export interface ProviderRow {
  provider: string;
  request_count: number;
  error_count: number;
  avg_latency_ms: number | null;
  total_tokens: number;
}

export interface DashboardData {
  range: string;
  since: string;
  totals: DashboardTotals;
  timeseries: TimeseriesRow[];
  by_provider: ProviderRow[];
}

export type Range = "1h" | "6h" | "24h" | "7d" | "30d";

export function useDashboard(range: Range = "24h", provider = "all") {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetch_ = useCallback(async () => {
    try {
      const res = await fetch(
        `${API_BASE}/dashboard/stats?range=${range}&provider=${provider}`,
      );
      if (!res.ok) throw new Error(`${res.status}`);
      const json = await res.json();
      setData(json);
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [range, provider]);

  useEffect(() => {
    setLoading(true);
    fetch_();
    timerRef.current = setInterval(fetch_, 30_000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [fetch_]);

  return { data, loading, error, refresh: fetch_ };
}
