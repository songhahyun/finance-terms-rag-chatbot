import { useEffect, useMemo, useState, type ReactNode } from "react";
import { CalendarDays, Search } from "lucide-react";
import { ResponsiveContainer, Bar, BarChart, CartesianGrid, Legend, Tooltip, XAxis, YAxis } from "recharts";
import { useAuth } from "@/app/auth-context";
import { fetchMonitorRecent, fetchMonitorSummary } from "@/lib/api";
import type { MonitorRecentItem, MonitorSummaryResponse } from "@/types/api";

export function AdminDashboardPage(): JSX.Element {
  const { token } = useAuth();
  const [summary, setSummary] = useState<MonitorSummaryResponse | null>(null);
  const [recent, setRecent] = useState<MonitorRecentItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      if (!token) return;
      setError(null);
      try {
        const [summaryData, recentData] = await Promise.all([fetchMonitorSummary(token), fetchMonitorRecent(token, 20)]);
        setSummary(summaryData);
        setRecent(recentData.items ?? []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "대시보드 로딩 실패");
      }
    };
    void load();
  }, [token]);

  const tableRows = useMemo(() => {
    return recent.map((row, idx) => ({
      no: idx + 1,
      time: row.timestamp,
      sessionId: row.trace_id,
      question: row.query,
      model: "gpt-4o",
      status: row.success ? "성공" : "오류",
      elapsed: row.elapsed_sec ? `${row.elapsed_sec.toFixed(2)}초` : "-",
      docs: row.work_units ? String(Math.round(row.work_units)) : "-",
      tokens: row.throughput ? String(Math.round(row.throughput)) : "-",
    }));
  }, [recent]);

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-[#e6ebf1] bg-white p-5">
        <h1 className="text-[30px] font-extrabold tracking-tight text-[#111827]">대시보드</h1>

        <div className="mt-4 flex flex-wrap items-center gap-6 border-b border-[#e8edf4] pb-3 text-sm font-semibold">
          <button className="border-b-2 border-[#2162ff] pb-2 text-[#2162ff]">채팅 로그</button>
          <button className="pb-2 text-[#6f7f95]">사용 통계</button>
          <button className="pb-2 text-[#6f7f95]">지식 문서 통계</button>
        </div>

        <div className="mt-4 grid gap-3 lg:grid-cols-[1.2fr_1fr_1.3fr_auto]">
          <FilterBox icon={<CalendarDays className="h-4 w-4 text-[#9aabc0]" />} text="2024-05-20   ~   2024-05-27" />
          <FilterBox text="전체 상태" />
          <FilterBox icon={<Search className="h-4 w-4 text-[#9aabc0]" />} text="질문 또는 세션ID 검색" />
          <button className="h-11 rounded-md border border-[#dce4ee] px-4 text-sm font-semibold text-[#4b5d76]">CSV 다운로드</button>
        </div>

        {error && <p className="mt-3 text-sm text-[#ef4444]">{error}</p>}

        <div className="mt-4 overflow-auto rounded-lg border border-[#e6ebf1]">
          <table className="w-full min-w-[1040px] border-collapse text-sm">
            <thead className="bg-[#f8faff] text-[#607188]">
              <tr>
                <Th>No.</Th>
                <Th>시간</Th>
                <Th>세션 ID</Th>
                <Th>질문</Th>
                <Th>모델</Th>
                <Th>상태</Th>
                <Th>응답 시간</Th>
                <Th>사용 문서 수</Th>
                <Th>사용 토큰</Th>
                <Th>작업</Th>
              </tr>
            </thead>
            <tbody>
              {tableRows.map((row) => (
                <tr key={`${row.sessionId}-${row.no}`} className="border-t border-[#edf2f7] text-[#334155]">
                  <Td>{row.no}</Td>
                  <Td>{row.time}</Td>
                  <Td>{row.sessionId}</Td>
                  <Td className="max-w-[320px] truncate">{row.question}</Td>
                  <Td>{row.model}</Td>
                  <Td>
                    <span className={row.status === "성공" ? "rounded-md bg-[#e8f8ea] px-2 py-1 text-xs font-bold text-[#15a34a]" : "rounded-md bg-[#ffe9ea] px-2 py-1 text-xs font-bold text-[#dc2626]"}>
                      {row.status}
                    </span>
                  </Td>
                  <Td>{row.elapsed}</Td>
                  <Td>{row.docs}</Td>
                  <Td>{row.tokens}</Td>
                  <Td>
                    <button className="rounded-md border border-[#dce3ec] px-2 py-1 text-xs text-[#4f5f78]">상세 보기</button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="h-[300px] rounded-xl border border-[#e6ebf1] bg-white p-4">
          <p className="mb-2 text-sm font-bold text-[#334155]">스테이지별 평균 처리시간</p>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={summary?.stage_summary ?? []}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="stage" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              <Bar dataKey="avg_elapsed_sec" name="평균 처리시간(초)" fill="#2162ff" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="h-[300px] rounded-xl border border-[#e6ebf1] bg-white p-4">
          <p className="mb-2 text-sm font-bold text-[#334155]">스테이지별 성공률</p>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={summary?.stage_summary ?? []}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="stage" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} domain={[0, 100]} />
              <Tooltip />
              <Legend />
              <Bar dataKey="success_rate" name="성공률(%)" fill="#22c55e" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function FilterBox({ text, icon }: { text: string; icon?: JSX.Element }): JSX.Element {
  return (
    <button className="flex h-11 items-center justify-between rounded-md border border-[#dce4ee] px-3 text-sm text-[#64758b]">
      <span>{text}</span>
      {icon ?? <span className="text-[#9aabc0]">▼</span>}
    </button>
  );
}

function Th({ children }: { children: ReactNode }): JSX.Element {
  return <th className="px-3 py-3 text-left text-xs font-bold">{children}</th>;
}

function Td({ children, className = "" }: { children: ReactNode; className?: string }): JSX.Element {
  return <td className={`px-3 py-3 text-sm ${className}`}>{children}</td>;
}
