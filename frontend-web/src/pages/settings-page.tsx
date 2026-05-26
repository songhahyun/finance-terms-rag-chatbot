import { useEffect, useState } from "react";

type SearchMode = "dense" | "sparse" | "hybrid";

type RetrievalSettings = {
  searchMode: SearchMode;
  hybridTopK: number;
  updatedAt: string;
};

const SETTINGS_STORAGE_KEY = "finrag.retrievalSettings";
const DEFAULT_SETTINGS: RetrievalSettings = {
  searchMode: "hybrid",
  hybridTopK: 10,
  updatedAt: new Date().toISOString(),
};

function clampTopK(value: number): number {
  if (Number.isNaN(value)) return DEFAULT_SETTINGS.hybridTopK;
  return Math.min(50, Math.max(1, Math.round(value)));
}

function loadSettings(): RetrievalSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_STORAGE_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    const parsed = JSON.parse(raw) as Partial<RetrievalSettings>;
    const searchMode: SearchMode = parsed.searchMode === "dense" || parsed.searchMode === "sparse" || parsed.searchMode === "hybrid" ? parsed.searchMode : "hybrid";
    return {
      searchMode,
      hybridTopK: clampTopK(Number(parsed.hybridTopK)),
      updatedAt: typeof parsed.updatedAt === "string" ? parsed.updatedAt : new Date().toISOString(),
    };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function SettingsPage(): JSX.Element {
  const [settings, setSettings] = useState<RetrievalSettings>(() => loadSettings());

  useEffect(() => {
    localStorage.setItem(
      SETTINGS_STORAGE_KEY,
      JSON.stringify({
        ...settings,
        hybridTopK: clampTopK(settings.hybridTopK),
        updatedAt: new Date().toISOString(),
      }),
    );
  }, [settings]);

  const updateSearchMode = (searchMode: SearchMode) => {
    setSettings((prev) => ({ ...prev, searchMode }));
  };

  const updateHybridTopK = (value: number) => {
    setSettings((prev) => ({ ...prev, hybridTopK: clampTopK(value) }));
  };

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-[#e6ebf1] bg-white p-5">
        <h1 className="text-[30px] font-extrabold tracking-tight text-[#111827]">설정</h1>
      </div>

      <section className="rounded-xl border border-[#e6ebf1] bg-white p-5">
        <div>
          <label className="text-sm font-bold text-[#334155]">Search 방식 선택</label>
          <div className="mt-3 grid gap-2 md:grid-cols-3">
            {[
              { label: "Dense", value: "dense" },
              { label: "Sparse (BM25)", value: "sparse" },
              { label: "Hybrid", value: "hybrid" },
            ].map((option) => (
              <button
                key={option.value}
                type="button"
                className={`h-11 rounded-md border px-3 text-sm font-semibold ${
                  settings.searchMode === option.value
                    ? "border-[#2162ff] bg-[#e9f1ff] text-[#1e5eff]"
                    : "border-[#dce4ee] bg-white text-[#64758b] hover:bg-[#f8faff]"
                }`}
                onClick={() => updateSearchMode(option.value as SearchMode)}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-6">
          <label htmlFor="hybrid-top-k" className="text-sm font-bold text-[#334155]">
            Hybrid Search Top-K
          </label>
          <div className="mt-3 flex flex-col gap-3 md:flex-row md:items-center">
            <input
              id="hybrid-top-k"
              type="number"
              min={1}
              max={50}
              value={settings.hybridTopK}
              disabled={settings.searchMode !== "hybrid"}
              className="h-11 w-full rounded-md border border-[#dce4ee] px-3 text-sm text-[#334155] disabled:bg-[#f1f5f9] disabled:text-[#94a3b8] md:w-[180px]"
              onChange={(event) => updateHybridTopK(Number(event.target.value))}
              onBlur={(event) => updateHybridTopK(Number(event.target.value))}
            />
            <input
              type="range"
              min={1}
              max={50}
              value={settings.hybridTopK}
              disabled={settings.searchMode !== "hybrid"}
              className="w-full accent-[#2162ff] disabled:opacity-50"
              onChange={(event) => updateHybridTopK(Number(event.target.value))}
            />
          </div>
          {settings.searchMode !== "hybrid" && <p className="mt-2 text-xs font-medium text-[#8a97aa]">Hybrid 선택 시 적용됩니다.</p>}
        </div>
      </section>
    </div>
  );
}
