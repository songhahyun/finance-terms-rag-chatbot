import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useAuth } from "@/app/auth-context";
import { Button } from "@/components/ui/button";
import { fetchMonitorRecent, fetchMonitorSummary } from "@/lib/api";
import type { DashboardStageSummary, MonitorRecentPaging, MonitorRecentRow, MonitorSummaryResponse } from "@/types/api";

const PAGE_SIZES = [20, 50, 100] as const;
const STAGE_LABELS: Record<string, string> = {
  intent_classification: "Intent",
  retrieval: "Retrieval",
  generation: "Generation",
};

export function AdminDashboardPage(): JSX.Element {
  const { token } = useAuth();
  const [summary, setSummary] = useState<MonitorSummaryResponse | null>(null);
  const [rows, setRows] = useState<MonitorRecentRow[]>([]);
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
      setSummary(summaryData);
      setRows(recentData.rows ?? []);
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

  const chartData = useMemo(() => {
    return stageEntries.map(({ stage, metrics }) => ({
      stage: STAGE_LABELS[stage] ?? stage,
      rps: metrics.throughput.rps ?? 0,
      qps: metrics.throughput.qps ?? 0,
      tps: metrics.throughput.output_tps ?? 0,
      rpm: metrics.throughput.rpm ?? 0,
      tpm: metrics.throughput.tpm ?? 0,
    }));
  }, [stageEntries]);

  const refreshLabel = summary?.last_refresh ? formatDateTime(summary.last_refresh) : "-";

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-extrabold text-[#111827]">대시보드</h1>
          <p className="text-sm text-[#64748b]">stage_monitor.log</p>
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
          <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-1">
            {stageEntries.length > 0 ? (
              stageEntries.map(({ stage, metrics }) => <StageBlock key={stage} stage={stage} metrics={metrics} />)
            ) : (
              <EmptyState>스테이지 데이터가 없습니다.</EmptyState>
            )}
          </div>
        </section>

        <section className="rounded-lg border border-[#e6ebf1] bg-white p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-bold text-[#334155]">Throughput</h2>
            <span className="text-xs font-semibold text-[#64748b]">RPS / QPS / TPS / RPM / TPM</span>
          </div>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 12, right: 16, bottom: 10, left: 0 }}>
                <CartesianGrid stroke="#e6ebf1" vertical={false} />
                <XAxis dataKey="stage" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="rps" name="RPS" stackId="throughput" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
                <Bar dataKey="qps" name="QPS" stackId="throughput" fill="#14b8a6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="tps" name="TPS" stackId="throughput" fill="#6366f1" radius={[4, 4, 0, 0]} />
                <Bar dataKey="rpm" name="RPM" stackId="throughput" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                <Bar dataKey="tpm" name="TPM" stackId="throughput" fill="#ef4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
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

function StageBlock({ stage, metrics }: { stage: string; metrics: DashboardStageSummary }): JSX.Element {
  return (
    <article className="rounded-lg border border-[#e6ebf1] bg-[#fbfdff] p-3">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="truncate text-sm font-extrabold text-[#111827]">{STAGE_LABELS[stage] ?? stage}</h3>
        <span className="rounded-md bg-white px-2 py-1 text-xs font-bold text-[#64748b]">{formatPercent(metrics.success_rate)}</span>
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs">
        <Metric label="total" value={metrics.total_rows} />
        <Metric label="success" value={metrics.success_count} />
        <Metric label="fail" value={metrics.fail_count} tone="danger" />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <Metric label="avg elapsed" value={`${formatNumber(metrics.avg_elapsed_sec, 3)}s`} />
        <Metric label="throughput" value={formatThroughput(metrics.throughput)} />
      </div>
    </article>
  );
}

function Metric({ label, value, tone = "default" }: { label: string; value: ReactNode; tone?: "default" | "danger" }): JSX.Element {
  return (
    <div>
      <p className="font-bold text-[#64748b]">{label}</p>
      <p className={`mt-1 break-words font-extrabold ${tone === "danger" ? "text-[#dc2626]" : "text-[#111827]"}`}>{value}</p>
    </div>
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

function formatNumber(value: number | undefined, digits = 2): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "-";
  return value.toFixed(digits);
}

function formatPercent(value: number | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "-";
  return `${Math.round(value * 100)}%`;
}

function formatThroughput(throughput: Record<string, number>): string {
  const entries = Object.entries(throughput);
  if (entries.length === 0) return "-";
  return entries.map(([key, value]) => `${key.toUpperCase()} ${formatNumber(value, 2)}`).join(" / ");
}

function formatDateTime(value: string): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}
