"use client";

import {
  BarChart,
  Bar,
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

const PROVIDER_COLORS: Record<string, string> = {
  gemini: "#4ade80",
  openai: "#818cf8",
  anthropic: "#f97316",
};

function fmtHour(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function ThroughputChart({ data }: Props) {
  const providers = Array.from(new Set(data.map((r) => r.provider)));

  // pivot: hour → { provider: count }
  const byHour = new Map<string, Record<string, number>>();
  for (const row of data) {
    if (!byHour.has(row.hour_bucket)) byHour.set(row.hour_bucket, {});
    byHour.get(row.hour_bucket)![row.provider] =
      (byHour.get(row.hour_bucket)![row.provider] ?? 0) + row.request_count;
  }

  const chartData = Array.from(byHour.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => ({ hour: fmtHour(k), ...v }));

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Requests / hour</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="hour" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend />
            {providers.map((p) => (
              <Bar
                key={p}
                dataKey={p}
                stackId="a"
                fill={PROVIDER_COLORS[p] ?? "#94a3b8"}
                name={p}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
