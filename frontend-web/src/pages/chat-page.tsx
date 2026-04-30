import { useState } from "react";
import { Bot, FileText, SendHorizontal, UserCircle2 } from "lucide-react";
import { useAuth } from "@/app/auth-context";
import { postChat } from "@/lib/api";
import type { ChatResponse } from "@/types/api";
import { Button } from "@/components/ui/button";

interface ChatHistoryItem {
  question: string;
  response: ChatResponse;
}

export function ChatPage(): JSX.Element {
  const { token } = useAuth();
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<ChatHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ask = async () => {
    if (!token || !question.trim()) return;
    const asked = question.trim();
    setIsLoading(true);
    setError(null);
    try {
      const response = await postChat({ question: asked, mode: "hybrid", k: 5, language: "ko" }, token);
      setHistory((prev) => [{ question: asked, response }, ...prev]);
      setQuestion("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "답변 생성에 실패했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  const latest = history[0];

  return (
    <div className="flex h-full min-h-[72vh] flex-col rounded-xl border border-[#e6ebf1] bg-white">
      <div className="border-b border-[#e6ebf1] px-5 py-4">
        <h1 className="text-2xl font-extrabold text-[#111827]">{latest?.question ?? "새 대화"}</h1>
        <p className="mt-1 text-xs text-[#8a97aa]">{new Date().toLocaleString()}</p>
      </div>

      <div className="flex-1 space-y-5 overflow-auto p-5">
        {latest ? (
          <>
            <div className="flex justify-end gap-3">
              <div className="max-w-[70%] rounded-xl bg-[#2b6cff] px-4 py-3 text-sm font-medium text-white shadow-sm">{latest.question}</div>
              <UserCircle2 className="mt-1 h-9 w-9 text-[#9aa8be]" />
            </div>

            <div className="flex items-start gap-3">
              <div className="mt-1 inline-flex h-9 w-9 items-center justify-center rounded-full bg-[#0b4476] text-white">
                <Bot className="h-5 w-5" />
              </div>
              <div className="w-full rounded-xl border border-[#dfe5ed] bg-white">
                <div className="whitespace-pre-wrap border-b border-[#ecf0f5] px-4 py-4 text-[15px] leading-7 text-[#334155]">{latest.response.answer}</div>
                <div className="px-4 py-3">
                  <p className="mb-2 text-sm font-bold text-[#4f5f78]">참고 문서 ({latest.response.sources.length})</p>
                  <div className="space-y-1">
                    {latest.response.sources.slice(0, 3).map((source, idx) => (
                      <div key={`${source.chunk_id ?? "na"}-${idx}`} className="flex items-center gap-2 text-sm text-[#5f6f84]">
                        <FileText className="h-4 w-4" />
                        <span className="truncate">{source.source ?? "Unknown source"}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex h-full min-h-[360px] items-center justify-center rounded-lg border border-dashed border-[#dbe2ec] bg-[#f9fbff] text-sm text-[#8a97aa]">
            질문을 입력하면 대화가 시작됩니다.
          </div>
        )}
      </div>

      <div className="border-t border-[#e6ebf1] p-4">
        <div className="flex items-center gap-3 rounded-lg border border-[#d8e0eb] bg-white px-3 py-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="메시지를 입력하세요..."
            className="h-10 flex-1 border-0 bg-transparent text-sm outline-none placeholder:text-[#98a4b6]"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void ask();
              }
            }}
          />
          <Button onClick={ask} disabled={isLoading || !question.trim()} className="h-9 w-9 rounded-md bg-[#2162ff] p-0 hover:bg-[#1e56e8]">
            <SendHorizontal className="h-4 w-4" />
          </Button>
        </div>
        {error && <p className="mt-2 text-sm text-[#ef4444]">{error}</p>}
        <p className="mt-2 text-xs text-[#95a1b3]">본 답변은 참고용이며, 최종 투자 판단은 투자자 본인의 책임입니다.</p>
      </div>
    </div>
  );
}
