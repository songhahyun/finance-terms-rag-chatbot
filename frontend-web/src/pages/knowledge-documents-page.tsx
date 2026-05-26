import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import { useAuth } from "@/app/auth-context";
import { fetchKnowledgeDocuments } from "@/lib/api";
import type { KnowledgeDocument } from "@/types/api";

const INITIAL_FILTERS = ["전체", "ㄱ", "ㄴ", "ㄷ", "ㄹ", "ㅁ", "ㅂ", "ㅅ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ", "abc"];
const CHO = ["ㄱ", "ㄲ", "ㄴ", "ㄷ", "ㄸ", "ㄹ", "ㅁ", "ㅂ", "ㅃ", "ㅅ", "ㅆ", "ㅇ", "ㅈ", "ㅉ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"];
const INITIAL_GROUP_MAP: Record<string, string> = {
  ㄲ: "ㄱ",
  ㄸ: "ㄷ",
  ㅃ: "ㅂ",
  ㅆ: "ㅅ",
  ㅉ: "ㅈ",
};

export function getKoreanInitialConsonant(value: string): string {
  const first = value.trim().charAt(0);
  if (!first) return "";

  const code = first.charCodeAt(0);
  const hangulStart = 0xac00;
  const hangulEnd = 0xd7a3;

  if (code < hangulStart || code > hangulEnd) {
    return first.toUpperCase();
  }

  const index = Math.floor((code - hangulStart) / 588);
  return CHO[index] ?? "";
}

export function getKnowledgeDocumentFilterGroup(value: string): string {
  const initial = getKoreanInitialConsonant(value);
  if (/^[A-Z]$/.test(initial)) return "abc";
  return INITIAL_GROUP_MAP[initial] ?? initial;
}

export function KnowledgeDocumentsPage(): JSX.Element {
  const { token } = useAuth();
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [initialFilter, setInitialFilter] = useState("전체");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      if (!token) return;
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetchKnowledgeDocuments(token);
        setDocuments(response.items);
      } catch (err) {
        setError(err instanceof Error ? err.message : "지식 문서 로딩 실패");
      } finally {
        setIsLoading(false);
      }
    };

    void load();
  }, [token]);

  const filteredDocuments = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase();
    return documents
      .filter((document) => {
        if (initialFilter === "전체") return true;
        return getKnowledgeDocumentFilterGroup(document.term) === initialFilter;
      })
      .filter((document) => {
        if (!normalizedSearch) return true;
        const searchable = [document.term, document.explanation, ...document.relatedTerms].join(" ").toLowerCase();
        return searchable.includes(normalizedSearch);
      })
      .sort((a, b) => a.term.localeCompare(b.term, "ko"));
  }, [documents, initialFilter, searchTerm]);

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-[#e6ebf1] bg-white p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <h1 className="text-[30px] font-extrabold tracking-tight text-[#111827]">지식 문서</h1>
          <div className="relative w-full lg:max-w-[360px]">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9aabc0]" />
            <input
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="용어 또는 설명 검색"
              className="h-11 w-full rounded-md border border-[#dce4ee] bg-white pl-10 pr-3 text-sm text-[#334155] outline-none placeholder:text-[#98a4b6] focus:border-[#2162ff]"
            />
          </div>
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          {INITIAL_FILTERS.map((filter) => (
            <button
              key={filter}
              type="button"
              className={`h-9 rounded-md border px-3 text-sm font-semibold ${
                initialFilter === filter
                  ? "border-[#2162ff] bg-[#e9f1ff] text-[#1e5eff]"
                  : "border-[#dce4ee] bg-white text-[#64758b] hover:bg-[#f8faff]"
              }`}
              onClick={() => setInitialFilter(filter)}
            >
              {filter}
            </button>
          ))}
        </div>
      </div>

      {isLoading && <div className="rounded-xl border border-[#e6ebf1] bg-white p-8 text-center text-sm text-[#7b889b]">지식 문서를 불러오는 중입니다.</div>}
      {error && <div className="rounded-xl border border-[#fee2e2] bg-[#fff7f7] p-4 text-sm font-medium text-[#dc2626]">{error}</div>}

      {!isLoading && !error && (
        <div className="space-y-3">
          {filteredDocuments.length > 0 ? (
            filteredDocuments.map((document) => (
              <article key={document.id} className="rounded-xl border border-[#e6ebf1] bg-white p-5">
                <h2 className="text-lg font-extrabold text-[#111827]">{document.term}</h2>
                <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-[#334155]">{document.explanation}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  {document.relatedTerms.length > 0 ? (
                    document.relatedTerms.map((term) => (
                      <span key={term} className="rounded-md bg-[#f1f5f9] px-2 py-1 text-xs font-semibold text-[#526174]">
                        {term}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs font-medium text-[#9aa6b6]">연관검색어 없음</span>
                  )}
                </div>
              </article>
            ))
          ) : (
            <div className="rounded-xl border border-dashed border-[#dbe2ec] bg-[#f9fbff] p-8 text-center text-sm text-[#8a97aa]">
              조건에 맞는 지식 문서가 없습니다.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
