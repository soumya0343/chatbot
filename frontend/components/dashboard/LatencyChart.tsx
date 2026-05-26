"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { TimeseriesRow } from "@/hooks/useDashboard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  data: TimeseriesRow[];
}

function fmtHour(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function LatencyChart({ data }: Props) {
  // Aggregate across providers per hour bucket
  const byHour = new Map<string, { p50: number[]; p95: number[]; p99: number[] }>();
  for (const row of data) {
    const k = row.hour_bucket;
    if (!byHour.has(k)) byHour.set(k, { p50: [], p95: [], p99: [] });
    const bucket = byHour.get(k)!;
    if (row.p50_latency_ms != null) bucket.p50.push(row.p50_latency_ms);
    if (row.p95_latency_ms != null) bucket.p95.push(row.p95_latency_ms);
    if (row.p99_latency_ms != null) bucket.p99.push(row.p99_latency_ms);
  }

  const chartData = Array.from(byHour.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => ({
      hour: fmtHour(k),
      p50: v.p50.length ? Math.round(v.p50.reduce((a, b) => a + b) / v.p50.length) : null,
      p95: v.p95.length ? Math.round(v.p95.reduce((a, b) => a + b) / v.p95.length) : null,
      p99: v.p99.length ? Math.round(v.p99.reduce((a, b) => a + b) / v.p99.length) : null,
    }));

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Latency (ms)</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="hour" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} unit="ms" />
            <Tooltip formatter={(v) => `${v}ms`} />
            <Legend />
            <Line type="monotone" dataKey="p50" stroke="#3b82f6" dot={false} name="p50" strokeWidth={2} />
            <Line type="monotone" dataKey="p95" stroke="#f59e0b" dot={false} name="p95" strokeWidth={2} />
            <Line type="monotone" dataKey="p99" stroke="#ef4444" dot={false} name="p99" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
