"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
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

export function ErrorRateChart({ data }: Props) {
  const byHour = new Map<string, { requests: number; errors: number }>();
  for (const row of data) {
    const k = row.hour_bucket;
    if (!byHour.has(k)) byHour.set(k, { requests: 0, errors: 0 });
    const b = byHour.get(k)!;
    b.requests += row.request_count;
    b.errors += row.error_count;
  }

  const chartData = Array.from(byHour.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => ({
      hour: fmtHour(k),
      error_pct: v.requests > 0 ? +((v.errors / v.requests) * 100).toFixed(1) : 0,
    }));

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Error rate (%)</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="errGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="hour" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} unit="%" domain={[0, "auto"]} />
            <Tooltip formatter={(v) => `${v}%`} />
            <Area
              type="monotone"
              dataKey="error_pct"
              stroke="#ef4444"
              fill="url(#errGrad)"
              strokeWidth={2}
              name="Error %"
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
