import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import * as RadixTooltip from "@radix-ui/react-tooltip";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip as ChartTooltip, XAxis, YAxis } from "recharts";
import { useAuth } from "@/app/auth-context";
import { Button } from "@/components/ui/button";
import { fetchMonitorRecent, fetchMonitorSummary } from "@/lib/api";
import type { DashboardStageSummary, MonitorRecentPaging, MonitorRecentRow, MonitorSummaryResponse } from "@/types/api";

const PAGE_SIZES = [20, 50, 100] as const;
const CHART_PAGE_SIZE = 100;
const THROUGHPUT_CHARTS = [
  { stage: "stage_0_intent_classification", metric: "successful_rps", label: "Successful RPS", type: "line", color: "#0ea5e9" },
  { stage: "stage_1_retrieval_bm25", metric: "successful_rps", label: "Successful RPS", type: "line", color: "#14b8a6" },
  { stage: "stage_1_retrieval_dense", metric: "successful_rps", label: "Successful RPS", type: "line", color: "#6366f1" },
  { stage: "stage_2_generation", metric: "rpm", label: "RPM", type: "line", color: "#84cc16" },
  { stage: "stage_2_generation", metric: "output_tpm", label: "Output TPM", type: "bar", color: "#ef4444" },
  { stage: "stage_2_generation", metric: "total_tpm", label: "Total TPM", type: "bar", color: "#a855f7" },
] as const;

type ThroughputMetric = (typeof THROUGHPUT_CHARTS)[number]["metric"];

interface ChartPoint {
  time: string;
  value: number;
}

export function AdminDashboardPage(): JSX.Element {
  const { token } = useAuth();
  const [summary, setSummary] = useState<MonitorSummaryResponse | null>(null);
  const [rows, setRows] = useState<MonitorRecentRow[]>([]);
  const [chartRows, setChartRows] = useState<MonitorRecentRow[]>([]);
  const [paging, setPaging] = useState<MonitorRecentPaging | null>(null);
  const [limit, setLimit] = useState<(typeof PAGE_SIZES)[number]>(20);
  const [page, setPage] = useState(1);
  const [errorsOnly, setErrorsOnly] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    setError(null);
    try {
      const [summaryData, recentData] = await Promise.all([
        fetchMonitorSummary(token),
        fetchMonitorRecent(token, limit, page, errorsOnly),
      ]);
      const chartData = await fetchMonitorChartRows(token);
      setSummary(summaryData);
      setRows(recentData.rows ?? []);
      setChartRows(chartData);
      setPaging(recentData.paging ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "대시보드 로딩 실패");
    } finally {
      setIsLoading(false);
    }
  }, [errorsOnly, limit, page, token]);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  const stageEntries = useMemo(() => {
    return Object.entries(summary?.dashboard_stage_summary ?? {}).map(([stage, metrics]) => ({ stage, metrics }));
  }, [summary]);

  const throughputSeries = useMemo(() => buildThroughputSeries(chartRows), [chartRows]);

  const refreshLabel = summary?.last_refresh ? formatDateTime(summary.last_refresh) : "-";

  return (
    <RadixTooltip.Provider delayDuration={150}>
      <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-extrabold text-[#111827]">대시보드</h1>
        </div>
        <Button onClick={() => void loadDashboard()} disabled={isLoading} className="gap-2">
          <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
          새로고침
        </Button>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-[#fecaca] bg-[#fef2f2] px-4 py-3 text-sm font-semibold text-[#b91c1c]">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-4">
        <SummaryCard label="Total rows" value={summary?.total_rows ?? 0} />
        <SummaryCard label="Error rows" value={summary?.error_rows ?? 0} tone="danger" />
        <SummaryCard label="Warning rows" value={summary?.warning_rows ?? 0} />
        <SummaryCard label="Last refresh" value={refreshLabel} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1.2fr]">
        <section className="rounded-lg border border-[#e6ebf1] bg-white p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-bold text-[#334155]">Stage summary</h2>
            <span className="text-xs font-semibold text-[#64748b]">{stageEntries.length} stages</span>
          </div>
          <div className="space-y-4">
            {stageEntries.length > 0 ? (
              <>
                <CallBasedStageTable entries={stageEntries.filter(({ metrics }) => metrics.stage_type === "call_based")} />
                <GenerationStageTable entries={stageEntries.filter(({ metrics }) => metrics.stage_type === "generation")} />
              </>
            ) : (
              <EmptyState>스테이지 데이터가 없습니다.</EmptyState>
            )}
          </div>
        </section>

        <section className="rounded-lg border border-[#e6ebf1] bg-white p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-bold text-[#334155]">Throughput charts</h2>
            <span className="text-xs font-semibold text-[#64748b]">recent rows, time series</span>
          </div>
          <div className="grid gap-3 xl:grid-cols-2">
            {THROUGHPUT_CHARTS.map((chart) => (
              <ThroughputChart
                key={`${chart.stage}-${chart.metric}`}
                stage={chart.stage}
                metric={chart.metric}
                label={chart.label}
                type={chart.type}
                color={chart.color}
                description={metricDescription(chart.stage, chart.metric)}
                data={throughputSeries[`${chart.stage}:${chart.metric}`] ?? []}
              />
            ))}
          </div>
        </section>
      </div>

      <section className="rounded-lg border border-[#e6ebf1] bg-white p-4">
        <div className="mb-3 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-sm font-bold text-[#334155]">Recent logs</h2>
            <p className="text-xs font-semibold text-[#64748b]">
              {paging ? `${paging.start_row}-${paging.end_row} / ${paging.total_rows}` : "0-0 / 0"}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex h-10 items-center gap-2 rounded-md border border-[#dce4ee] bg-white px-3 text-sm font-semibold text-[#334155]">
              <input
                type="checkbox"
                checked={errorsOnly}
                onChange={(event) => {
                  setErrorsOnly(event.target.checked);
                  setPage(1);
                }}
                className="h-4 w-4"
              />
              Errors only
            </label>
            <select
              value={limit}
              onChange={(event) => {
                setLimit(Number(event.target.value) as (typeof PAGE_SIZES)[number]);
                setPage(1);
              }}
              className="h-10 rounded-md border border-[#dce4ee] bg-white px-3 text-sm font-semibold text-[#334155]"
            >
              {PAGE_SIZES.map((size) => (
                <option key={size} value={size}>
                  {size} rows
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mb-3 flex flex-wrap gap-2">
          {(paging?.pages ?? []).map((pageRange) => (
            <button
              key={pageRange.page}
              onClick={() => setPage(pageRange.page)}
              className={`h-8 rounded-md border px-3 text-xs font-bold ${
                pageRange.page === page
                  ? "border-[#0ea5e9] bg-[#e0f2fe] text-[#0369a1]"
                  : "border-[#dce4ee] bg-white text-[#475569] hover:bg-[#f8fafc]"
              }`}
            >
              {pageRange.label}
            </button>
          ))}
        </div>

        <div className="overflow-auto rounded-lg border border-[#e6ebf1]">
          <table className="w-full min-w-[1100px] border-collapse text-sm">
            <thead className="bg-[#f8faff] text-[#607188]">
              <tr>
                <Th>timestamp</Th>
                <Th>trace_id</Th>
                <Th>stage</Th>
                <Th>status</Th>
                <Th>elapsed_sec</Th>
                <Th>user_query</Th>
                <Th>error_message</Th>
              </tr>
            </thead>
            <tbody>
              {rows.length > 0 ? (
                rows.map((row) => (
                  <tr key={`${row.trace_id}-${row.timestamp}-${row.stage}`} className="border-t border-[#edf2f7] text-[#334155]">
                    <Td>{formatDateTime(row.timestamp)}</Td>
                    <Td className="max-w-[220px] truncate font-mono text-xs">{row.trace_id}</Td>
                    <Td>{row.stage}</Td>
                    <Td>
                      <StatusBadge status={row.status} />
                    </Td>
                    <Td>{formatNumber(row.elapsed_sec, 3)}</Td>
                    <Td className="max-w-[360px] truncate">{row.user_query || "-"}</Td>
                    <Td className="max-w-[320px] truncate text-[#b91c1c]">{row.error_message || "-"}</Td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="px-3 py-10 text-center text-sm font-semibold text-[#64748b]">
                    로그 데이터가 없습니다.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
      </div>
    </RadixTooltip.Provider>
  );
}

function SummaryCard({ label, value, tone = "default" }: { label: string; value: ReactNode; tone?: "default" | "danger" }): JSX.Element {
  return (
    <section className="rounded-lg border border-[#e6ebf1] bg-white p-4">
      <p className="text-xs font-bold uppercase text-[#64748b]">{label}</p>
      <p className={`mt-2 break-words text-2xl font-extrabold ${tone === "danger" ? "text-[#dc2626]" : "text-[#111827]"}`}>
        {value}
      </p>
    </section>
  );
}

function CallBasedStageTable({ entries }: { entries: Array<{ stage: string; metrics: DashboardStageSummary }> }): JSX.Element {
  if (entries.length === 0) return <EmptyState>Call-based stage data is unavailable.</EmptyState>;
  return (
    <div className="overflow-auto rounded-lg border border-[#e6ebf1]">
      <table className="w-full min-w-[760px] border-collapse text-xs">
        <thead className="bg-[#f8faff] text-[#607188]">
          <tr>
            <Th>stage</Th>
            <Th>elapsed_sec</Th>
            <Th>attempted_rps</Th>
            <Th>successful_rps</Th>
            <Th>success_count</Th>
            <Th>result_count</Th>
            <Th>status</Th>
          </tr>
        </thead>
        <tbody>
          {entries.map(({ stage, metrics }) => (
            <tr key={stage} className="border-t border-[#edf2f7] text-[#334155]">
              <Td className="font-mono text-xs">{stage}</Td>
              <Td>{formatNumber(metrics.elapsed_sec ?? metrics.avg_elapsed_sec, 4)}</Td>
              <Td>{formatNullable(metrics.attempted_rps, 4)}</Td>
              <Td>{formatNullable(metrics.successful_rps, 4)}</Td>
              <Td>{formatNullable(metrics.stage_type === "call_based" && stage === "stage_1_retrieval_fusion" ? null : metrics.success_count, 0)}</Td>
              <Td>{formatNullable(metrics.result_count, 0)}</Td>
              <Td>{metrics.status ? <StatusBadge status={metrics.status} /> : "N/A"}</Td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function GenerationStageTable({ entries }: { entries: Array<{ stage: string; metrics: DashboardStageSummary }> }): JSX.Element | null {
  if (entries.length === 0) return null;
  return (
    <div className="overflow-auto rounded-lg border border-[#e6ebf1]">
      <table className="w-full min-w-[1100px] border-collapse text-xs">
        <thead className="bg-[#f8faff] text-[#607188]">
          <tr>
            <Th>stage</Th>
            <Th>elapsed_sec</Th>
            <Th>Output TPS</Th>
            <Th>Chars/sec</Th>
            <Th>RPM</Th>
            <Th>Output TPM</Th>
            <Th>Total TPM</Th>
            <Th>input_tokens</Th>
            <Th>output_tokens</Th>
            <Th>total_tokens</Th>
            <Th>token_count_source</Th>
            <Th>status</Th>
          </tr>
        </thead>
        <tbody>
          {entries.map(({ stage, metrics }) => (
            <tr key={stage} className="border-t border-[#edf2f7] text-[#334155]">
              <Td className="font-mono text-xs">{stage}</Td>
              <Td>{formatNumber(metrics.elapsed_sec ?? metrics.avg_elapsed_sec, 4)}</Td>
              <Td>{formatNullable(metrics.output_tps, 4)}</Td>
              <Td>{formatNullable(metrics.chars_per_sec, 4)}</Td>
              <Td>{formatNullable(metrics.rpm, 4)}</Td>
              <Td>{formatNullable(metrics.output_tpm, 4)}</Td>
              <Td>{formatNullable(metrics.total_tpm, 4)}</Td>
              <Td>{formatNullable(metrics.input_tokens, 0)}</Td>
              <Td>{formatNullable(metrics.output_tokens, 0)}</Td>
              <Td>{formatNullable(metrics.total_tokens, 0)}</Td>
              <Td>{metrics.token_count_source ?? "unavailable"}</Td>
              <Td>{metrics.status ? <StatusBadge status={metrics.status} /> : "N/A"}</Td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ThroughputChart({
  stage,
  metric,
  label,
  type,
  color,
  description,
  data,
}: {
  stage: string;
  metric: ThroughputMetric;
  label: string;
  type: "line" | "bar";
  color: string;
  description: string;
  data: ChartPoint[];
}): JSX.Element {
  return (
    <article className="min-h-[260px] rounded-lg border border-[#e6ebf1] bg-[#fbfdff] p-3">
      <div className="mb-2 min-w-0">
        <h3 className="truncate text-xs font-extrabold text-[#111827]" title={stage}>
          {stage}
        </h3>
        <p className="text-xs font-bold text-[#64748b]">{label}</p>
      </div>
      <div className="h-[205px] min-w-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          {type === "line" ? (
            <LineChart data={data} margin={{ top: 10, right: 16, bottom: 8, left: 0 }}>
              <CartesianGrid stroke="#e6ebf1" vertical={false} />
              <XAxis dataKey="time" tick={{ fontSize: 11 }} minTickGap={20} />
              <YAxis tick={{ fontSize: 11 }} />
              <ChartTooltip formatter={(value) => formatNumber(Number(value), 2)} />
              <Legend content={() => <MetricLegend color={color} label={label} description={description} />} />
              <Line type="monotone" dataKey="value" name={label} stroke={color} strokeWidth={2} dot={false} />
            </LineChart>
          ) : (
            <BarChart data={data} margin={{ top: 10, right: 16, bottom: 8, left: 0 }}>
              <CartesianGrid stroke="#e6ebf1" vertical={false} />
              <XAxis dataKey="time" tick={{ fontSize: 11 }} minTickGap={20} />
              <YAxis tick={{ fontSize: 11 }} />
              <ChartTooltip formatter={(value) => formatNumber(Number(value), 2)} />
              <Legend content={() => <MetricLegend color={color} label={label} description={description} />} />
              <Bar dataKey="value" name={label} stackId={metric} fill={color} radius={[4, 4, 0, 0]} />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </article>
  );
}

function MetricLegend({ color, label, description }: { color: string; label: string; description: string }): JSX.Element {
  return (
    <RadixTooltip.Root>
      <RadixTooltip.Trigger asChild>
        <button type="button" className="mx-auto mt-1 flex items-center gap-2 rounded-md px-2 py-1 text-xs font-bold text-[#475569] hover:bg-white">
          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
          {label}
        </button>
      </RadixTooltip.Trigger>
      <RadixTooltip.Portal>
        <RadixTooltip.Content
          side="top"
          align="center"
          className="z-50 max-w-[320px] rounded-md border border-[#dbe2ea] bg-white px-3 py-2 text-xs font-semibold leading-5 text-[#334155] shadow-lg"
        >
          {description}
          <RadixTooltip.Arrow className="fill-white" />
        </RadixTooltip.Content>
      </RadixTooltip.Portal>
    </RadixTooltip.Root>
  );
}

function StatusBadge({ status }: { status: string }): JSX.Element {
  const isFail = status === "fail";
  return (
    <span className={`rounded-md px-2 py-1 text-xs font-bold ${isFail ? "bg-[#fee2e2] text-[#b91c1c]" : "bg-[#dcfce7] text-[#166534]"}`}>
      {status}
    </span>
  );
}

function EmptyState({ children }: { children: ReactNode }): JSX.Element {
  return <div className="rounded-lg border border-dashed border-[#cbd5e1] px-4 py-8 text-center text-sm font-semibold text-[#64748b]">{children}</div>;
}

function Th({ children }: { children: ReactNode }): JSX.Element {
  return <th className="px-3 py-3 text-left text-xs font-bold">{children}</th>;
}

function Td({ children, className = "" }: { children: ReactNode; className?: string }): JSX.Element {
  return <td className={`px-3 py-3 align-top text-sm ${className}`}>{children}</td>;
}

async function fetchMonitorChartRows(token: string): Promise<MonitorRecentRow[]> {
  const firstPage = await fetchMonitorRecent(token, CHART_PAGE_SIZE, 1, false);
  const totalPages = firstPage.paging?.total_pages ?? 1;
  if (totalPages <= 1) {
    return firstPage.rows ?? [];
  }

  const rest = await Promise.all(
    Array.from({ length: totalPages - 1 }, (_, index) => fetchMonitorRecent(token, CHART_PAGE_SIZE, index + 2, false)),
  );
  return [firstPage, ...rest].flatMap((response) => response.rows ?? []);
}

function buildThroughputSeries(rows: MonitorRecentRow[]): Record<string, ChartPoint[]> {
  const series: Record<string, ChartPoint[]> = {};
  for (const chart of THROUGHPUT_CHARTS) {
    const points = rows
      .filter((row) => row.stage === chart.stage)
      .slice()
      .sort((a, b) => timestampMs(a.timestamp) - timestampMs(b.timestamp))
      .map((row) => ({
        time: formatChartTime(row.timestamp),
        value: metricValue(row, chart.metric),
      }));
    series[`${chart.stage}:${chart.metric}`] = points;
  }
  return series;
}

function metricValue(row: MonitorRecentRow, metric: ThroughputMetric): number {
  if (metric === "rpm") {
    return row.elapsed_sec > 0 ? 60 / row.elapsed_sec : 0;
  }
  if (metric === "output_tpm") {
    return (row.output_tokens_per_sec ?? 0) * 60;
  }
  if (metric === "total_tpm") {
    const elapsed = row.generation_elapsed_sec ?? row.elapsed_sec;
    return row.total_tokens && elapsed > 0 ? (row.total_tokens / elapsed) * 60 : 0;
  }
  if (metric === "successful_rps") {
    return row.successful_calls_per_sec ?? row.throughput;
  }
  return 0;
}

function metricDescription(stage: string, metric: ThroughputMetric): string {
  if (metric === "rpm") {
    return "RPM: approximate requests per minute for stage_2_generation, calculated as 60 / elapsed_sec.";
  }
  if (metric === "output_tpm") {
    return "Output TPM: generated output tokens per minute for stage_2_generation.";
  }
  if (metric === "total_tpm") {
    return "Total TPM: total input plus output tokens per minute for stage_2_generation.";
  }
  if (stage.startsWith("stage_1_retrieval")) {
    return "Successful RPS: retrieval calls completed successfully per second.";
  }
  return "Successful RPS: intent classification calls completed successfully per second.";
}

function formatNumber(value: number | undefined, digits = 2): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "-";
  return value.toFixed(digits);
}

function formatNullable(value: number | null | undefined, digits = 2): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "N/A";
  return value.toFixed(digits);
}

function formatDateTime(value: string): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function formatChartTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function timestampMs(value: string): number {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 0 : date.getTime();
}
