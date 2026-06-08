import type { ChatRequest } from "@/types/api";

export type SearchMode = "dense" | "sparse" | "hybrid";

export type RetrievalSettings = {
  searchMode: SearchMode;
  hybridTopK: number;
  updatedAt: string;
};

export const RETRIEVAL_SETTINGS_STORAGE_KEY = "finrag.retrievalSettings";
export const MAX_RETRIEVAL_TOP_K = 20;

export const DEFAULT_RETRIEVAL_SETTINGS: RetrievalSettings = {
  searchMode: "hybrid",
  hybridTopK: 10,
  updatedAt: new Date().toISOString(),
};

const DEFAULT_CHAT_RETRIEVAL = {
  mode: "hybrid",
  k: 5,
} as const;

export function clampTopK(value: number): number {
  if (Number.isNaN(value)) return DEFAULT_RETRIEVAL_SETTINGS.hybridTopK;
  return Math.min(MAX_RETRIEVAL_TOP_K, Math.max(1, Math.round(value)));
}

function normalizeSearchMode(value: unknown): SearchMode {
  return value === "dense" || value === "sparse" || value === "hybrid" ? value : DEFAULT_RETRIEVAL_SETTINGS.searchMode;
}

export function loadRetrievalSettings(): RetrievalSettings {
  try {
    const raw = localStorage.getItem(RETRIEVAL_SETTINGS_STORAGE_KEY);
    if (!raw) return DEFAULT_RETRIEVAL_SETTINGS;
    const parsed = JSON.parse(raw) as Partial<RetrievalSettings>;
    return {
      searchMode: normalizeSearchMode(parsed.searchMode),
      hybridTopK: clampTopK(Number(parsed.hybridTopK)),
      updatedAt: typeof parsed.updatedAt === "string" ? parsed.updatedAt : new Date().toISOString(),
    };
  } catch {
    return DEFAULT_RETRIEVAL_SETTINGS;
  }
}

export function saveRetrievalSettings(settings: RetrievalSettings): RetrievalSettings {
  const nextSettings = {
    ...settings,
    searchMode: normalizeSearchMode(settings.searchMode),
    hybridTopK: clampTopK(settings.hybridTopK),
    updatedAt: new Date().toISOString(),
  };
  localStorage.setItem(RETRIEVAL_SETTINGS_STORAGE_KEY, JSON.stringify(nextSettings));
  return nextSettings;
}

export function loadChatRetrievalPayload(): Pick<ChatRequest, "mode" | "k"> {
  try {
    const raw = localStorage.getItem(RETRIEVAL_SETTINGS_STORAGE_KEY);
    if (!raw) return DEFAULT_CHAT_RETRIEVAL;
    const parsed = JSON.parse(raw) as Partial<RetrievalSettings>;
    const searchMode = normalizeSearchMode(parsed.searchMode);
    return {
      mode: searchMode === "sparse" ? "bm25" : searchMode,
      k: searchMode === "hybrid" ? clampTopK(Number(parsed.hybridTopK)) : DEFAULT_CHAT_RETRIEVAL.k,
    };
  } catch {
    return DEFAULT_CHAT_RETRIEVAL;
  }
}
