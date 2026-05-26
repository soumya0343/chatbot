"use client";

import { useState } from "react";
import { useDashboard, Range } from "@/hooks/useDashboard";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { LatencyChart } from "@/components/dashboard/LatencyChart";
import { ThroughputChart } from "@/components/dashboard/ThroughputChart";
import { ErrorRateChart } from "@/components/dashboard/ErrorRateChart";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { RefreshCw } from "lucide-react";

const RANGES: Range[] = ["1h", "6h", "24h", "7d", "30d"];

function fmt(n: number | null | undefined, unit = ""): string {
  if (n == null) return "—";
  return `${Math.round(n).toLocaleString()}${unit}`;
}

function errorPct(total: number | null, errors: number | null): string {
  if (!total || errors == null) return "—";
  return `${((errors / total) * 100).toFixed(1)}%`;
}

export function DashboardClient() {
  const [range, setRange] = useState<Range>("24h");
  const { data, loading, error, refresh } = useDashboard(range);

  const t = data?.totals;

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-6xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h1 className="text-2xl font-bold">Analytics Dashboard</h1>
          <div className="flex items-center gap-2">
            <div className="flex gap-1">
              {RANGES.map((r) => (
                <Button
                  key={r}
                  variant={range === r ? "default" : "outline"}
                  size="sm"
                  onClick={() => setRange(r)}
                >
                  {r}
                </Button>
              ))}
            </div>
            <Button variant="ghost" size="icon" onClick={refresh} title="Refresh">
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
          </div>
        </div>

        {error && (
          <div className="text-sm text-destructive border border-destructive/30 rounded px-3 py-2">
            {error} — is the API running?
          </div>
        )}

        {data && (
          <>
            {/* Metric cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <MetricCard
                title="Total Requests"
                value={fmt(t?.total_requests)}
                sub={`${fmt(t?.total_errors)} errors`}
              />
              <MetricCard
                title="Error Rate"
                value={errorPct(t?.total_requests ?? null, t?.total_errors ?? null)}
                sub={`${fmt(t?.total_cancelled)} cancelled`}
              />
              <MetricCard
                title="Avg Latency"
                value={fmt(t?.avg_latency_ms, "ms")}
                sub={`p95: ${fmt(t?.p95_latency_ms, "ms")}`}
              />
              <MetricCard
                title="Total Tokens"
                value={fmt(t?.total_tokens)}
                sub={`in: ${fmt(t?.total_input_tokens)} / out: ${fmt(t?.total_output_tokens)}`}
              />
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <LatencyChart data={data.timeseries} />
              <ThroughputChart data={data.timeseries} />
            </div>
            <ErrorRateChart data={data.timeseries} />

            {/* Per-provider table */}
            {data.by_provider.length > 0 && (
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50">
                    <tr>
                      {["Provider", "Requests", "Errors", "Avg Latency", "Tokens"].map((h) => (
                        <th key={h} className="text-left px-4 py-2 font-medium text-xs text-muted-foreground uppercase">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {data.by_provider.map((row) => (
                      <tr key={row.provider} className="hover:bg-muted/30">
                        <td className="px-4 py-2">
                          <Badge variant="outline">{row.provider}</Badge>
                        </td>
                        <td className="px-4 py-2">{row.request_count.toLocaleString()}</td>
                        <td className="px-4 py-2 text-destructive">{row.error_count}</td>
                        <td className="px-4 py-2">{fmt(row.avg_latency_ms, "ms")}</td>
                        <td className="px-4 py-2">{row.total_tokens.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {data.timeseries.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-8">
                No data for this range — send some messages first.
              </p>
            )}

            <p className="text-xs text-muted-foreground">
              Auto-refreshes every 30s · Last updated: {new Date().toLocaleTimeString()}
            </p>
          </>
        )}

        {loading && !data && (
          <div className="flex items-center justify-center py-20">
            <RefreshCw className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        )}
      </div>
    </div>
  );
}
