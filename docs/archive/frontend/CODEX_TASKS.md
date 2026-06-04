# CODEX_TASKS.md

## Context

This repository contains a TypeScript-based frontend for **FinRAG Chatbot**. The visual shell already exists, but several interactive behaviors are incomplete or currently no-op.

There are currently three primary screens:

1. Login screen
2. Chat screen
3. Monitoring dashboard screen

Implement the missing UI behavior and add two missing screens reachable from the chat layout sidebar:

4. Knowledge Documents screen
5. Admin-only Settings screen

Use the attached screenshots as the visual baseline. Preserve the current design language: white/light-gray surfaces, blue primary buttons, rounded cards, subtle borders, compact spacing, and Korean UI labels.

---

## Global Requirements

### Technical expectations

- Use TypeScript.
- Keep existing routing/layout conventions unless there is a clear reason to improve them.
- Do not introduce a large new UI framework unless the project already uses it.
- Prefer small, composable React components.
- Remove dead click handlers and non-functional UI affordances.
- Do not hard-code dummy data in production UI.
- Avoid browser-side filesystem reads from local Windows paths. Browsers cannot read `D:\...` directly.
- For `final_chunk.json`, implement one of the following:
  - Preferred: add/use a backend API endpoint that reads the JSON file from the project data directory.
  - Acceptable fallback for frontend-only development: copy or expose the JSON through a static/public asset path and document the limitation.
- The decided implementation is to add a backend API endpoint and manage the chunk file path through `src/common/config.py`.

### Data source for knowledge documents

Source file:

```text
D:\AI\projects\finance-terms-rag-chatbot\data\processed\final_chunk.json
```

Expected fields per chunk:

- `용어`
- `설명`
- `연관검색어`

The actual JSON schema may vary slightly. Implement defensive parsing so the UI supports common variants such as:

```ts
{
  "term": "...",
  "explanation": "...",
  "metadata": {
    "related_terms": [...]
  }
}
```

or

```ts
{
  "용어": "...",
  "설명": "...",
  "연관검색어": [...]
}
```

Display only valid chunks with a non-empty term and explanation. Log or gracefully ignore malformed rows.

### Decisions

- Use `/dashboard` as the canonical monitoring dashboard route.
- Keep `/admin` only as a backward-compatible redirect to `/dashboard`.
- Store chat conversations in `localStorage` under `finrag.conversations`.
- Chat conversations must persist across refresh, browser restart, and user logout. Do not clear `finrag.conversations` in the logout flow.
- Manage the knowledge document path through `src/common/config.py`. The user will add `FINRAG_CHUNK_PATH` to `.env`; the backend should read it through settings and fall back to `data/processed/final_chunk.json`.

---

## Task 01 — Login screen: password visibility toggle

### Current issue

On the login screen, clicking the eye icon on the right side of the password input does nothing.

### Required behavior

- Password input should default to hidden:
  - `type="password"`
- Clicking the eye icon should toggle visibility:
  - hidden → visible: `type="text"`
  - visible → hidden: `type="password"`
- Icon should visually reflect the current state:
  - hidden password: eye-off icon
  - visible password: eye icon
- Add accessible label:
  - `aria-label="비밀번호 보기"` when hidden
  - `aria-label="비밀번호 숨기기"` when visible

### Acceptance criteria

- User can toggle password visibility without losing typed password.
- No layout shift occurs when toggling.
- Button is keyboard accessible.

---

## Task 02 — Login screen: forgot password flow

### Current issue

`비밀번호 찾기` exists visually but has no implemented behavior.

### Required behavior

Implement a simple forgot-password screen or modal.

Minimum acceptable flow:

1. User clicks `비밀번호 찾기`.
2. A modal or route appears with:
   - title: `비밀번호 찾기`
   - email input
   - primary button: `재설정 링크 보내기`
   - secondary action: `로그인으로 돌아가기`
3. On submit:
   - Validate that the input is non-empty.
   - Validate basic email format.
   - Show a success message:
     - `입력하신 이메일로 비밀번호 재설정 안내를 보냈습니다.`
4. Do not call a real password-reset API or send a real email for this portfolio scope unless such backend already exists.

### Signup email requirement

To make the forgot-password flow coherent, collect an email address during signup.

- Add an email field to the signup UI.
- Validate that signup email is non-empty and uses a basic email format.
- If backend signup schemas/models are already implemented, extend them to store the email address.
- Login can continue to use username and password; email is only required for signup and forgot-password flow.

### Scope decision

This task implements a portfolio-friendly mock reset flow only.

- In scope:
  - email input
  - frontend validation
  - success message after submit
  - return to login
- Out of scope:
  - real email delivery
  - reset-token creation
  - reset-password page
  - password update API
  - identity verification

### Acceptance criteria

- Clicking `비밀번호 찾기` changes visible UI.
- Empty input shows validation message.
- Invalid email format shows validation message.
- Successful submit shows success message.
- User can return to login screen.
- Signup collects and validates an email address.

---

## Task 03 — Chat screen: recent conversations from real chat state

### Current issue

The left sidebar `최근 대화` list is hard-coded with dummy values:

- `ELS 상품 설명해줘`
- `신용등급 하락 원인`
- `금리 인상 영향 분석`
- `회사채 투자 리스크`
- `환율 전망 알려줘`

### Required behavior

Replace hard-coded recent conversations with user-generated chat history.

When the user sends a new message:

1. Create or update the current conversation session.
2. Generate a concise Korean title from the first user message.
3. Add it to the sidebar under `최근 대화`.
4. Persist recent conversations in `localStorage` so the list survives refresh, browser restart, and logout.

### Title generation rule

No LLM call is required. Use deterministic frontend logic.

Suggested logic:

```ts
function createConversationTitle(message: string): string {
  const normalized = message.trim().replace(/\s+/g, " ");
  if (!normalized) return "새 대화";
  return normalized.length > 18 ? `${normalized.slice(0, 18)}...` : normalized;
}
```

### Interaction requirements

- Clicking a recent conversation loads that conversation into the chat area.
- `+ 새 대화` starts a new empty conversation.
- Recent conversations should be ordered newest first.
- Limit sidebar list to the most recent 10 conversations.
- Empty state text:
  - `아직 최근 대화가 없습니다.`

### Suggested localStorage schema

```ts
type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
};

type Conversation = {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
};
```

Storage key:

```text
finrag.conversations
```

Persistence policy:

- Use `localStorage`, not `sessionStorage`.
- Do not remove `finrag.conversations` when the user logs out.
- The data remains browser- and origin-local. It is not shared across devices or browsers.

### Acceptance criteria

- No dummy recent conversations remain.
- Sending a message creates a recent conversation item.
- Refreshing the browser preserves recent conversations.
- Logging out and logging back in preserves recent conversations on the same browser and origin.
- Clicking a recent conversation restores its messages.
- `+ 새 대화` creates a clean chat state.

---

## Task 04 — Chat screen: remove unused admin dropdown arrow

### Current issue

In the top bar, an arrow icon next to `admin 님` is visible but clicking it opens nothing.

### Required behavior

- Remove the downward arrow icon beside `admin 님`.
- Keep the user avatar/icon and `admin 님` text.
- Keep `로그아웃` button.

### Acceptance criteria

- There is no visual dropdown affordance beside `admin 님`.
- No dead click target remains in that area.
- Top bar alignment remains clean.

---

## Task 05 — Monitoring dashboard: remove unused tab bar

### Current issue

The dashboard has a tab bar:

- `채팅 로그`
- `사용 통계`
- `지식 문서 통계`

These tabs are not needed.

### Required behavior

- Remove the tab bar entirely.
- The dashboard should directly show the current dashboard content.
- Keep page title `대시보드`.
- Keep filters/search/download controls if they are already implemented or visually present.

### Acceptance criteria

- No tab labels are visible.
- Dashboard layout spacing remains balanced after tab removal.

---

## Task 06 — Monitoring dashboard: fix chart card height and axis-label overflow

### Current issue

The chart cards for:

- `스테이지별 평균 처리시간`
- `스테이지별 성공률`

are too short. Axis labels such as `평균 처리시간(초)` and `성공률(%)` overflow outside the card.

### Required behavior

- Increase vertical height of both chart cards.
- Ensure chart labels stay inside their cards.
- Add enough bottom padding/margin inside chart containers.
- Preserve the two-column layout on desktop.
- Stack cards vertically on narrow screens if responsive design already exists.

### Suggested implementation

- Set a minimum height:
  - desktop: `min-height: 320px`
  - mobile: `min-height: 280px`
- Add chart container padding:
  - bottom padding at least `32px`
- If using Recharts, adjust:
  - `margin={{ top: 16, right: 24, bottom: 40, left: 24 }}`
  - `Label` offset
- If using CSS-only placeholder charts, make the placeholder canvas area smaller than the card body so labels do not overflow.

### Acceptance criteria

- `평균 처리시간(초)` is fully visible.
- `성공률(%)` is fully visible.
- Chart boxes are visibly taller than the current screenshot.
- No horizontal or vertical overflow in the dashboard card area.

---

## Task 07 — Add Knowledge Documents screen

### Current issue

The sidebar contains `지식 문서`, but the screen is not implemented.

### Required behavior

Implement a `지식 문서` screen reachable from the left sidebar.

The screen should show RAG source chunks from `final_chunk.json`.

Required UI:

- Page title: `지식 문서`
- Search input:
  - placeholder: `용어 또는 설명 검색`
- Initial consonant filter buttons:
  - `전체`
  - `ㄱ`, `ㄴ`, `ㄷ`, `ㄹ`, `ㅁ`, `ㅂ`, `ㅅ`, `ㅇ`, `ㅈ`, `ㅊ`, `ㅋ`, `ㅌ`, `ㅍ`, `ㅎ`
  - `abc`
- Document cards or table rows showing:
  - `용어`
  - `설명`
  - `연관검색어`

### Sorting and filtering

- Sort terms by Korean alphabetical order.
- Filter by initial consonant of the term.
- Filter English terms under the `abc` tab.
- Search should match:
  - term
  - explanation
  - related terms
- When no result exists, show:
  - `조건에 맞는 지식 문서가 없습니다.`

### Initial consonant utility

Implement a utility function similar to:

```ts
const CHO = [
  "ㄱ", "ㄲ", "ㄴ", "ㄷ", "ㄸ", "ㄹ", "ㅁ", "ㅂ", "ㅃ", "ㅅ",
  "ㅆ", "ㅇ", "ㅈ", "ㅉ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"
];

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
```

For grouped filter buttons, map double consonants to the base group:

```ts
const INITIAL_GROUP_MAP: Record<string, string> = {
  "ㄲ": "ㄱ",
  "ㄸ": "ㄷ",
  "ㅃ": "ㅂ",
  "ㅆ": "ㅅ",
  "ㅉ": "ㅈ"
};
```

For English terms, return an English group marker so they can be displayed under the `abc` filter:

```ts
export function getKnowledgeDocumentFilterGroup(value: string): string {
  const initial = getKoreanInitialConsonant(value);
  if (/^[A-Z]$/.test(initial)) return "abc";
  return INITIAL_GROUP_MAP[initial] ?? initial;
}
```

Filtering behavior:

- `전체` includes both Korean and English terms.
- Korean initial tabs include Hangul terms mapped to that consonant group.
- `abc` includes terms whose first non-empty character is an English alphabet letter.
- Non-Hangul, non-English terms should remain visible under `전체`; they do not need a dedicated tab unless a later requirement adds one.

### Data loading recommendation

Preferred backend endpoint:

```http
GET /knowledge-documents
```

Response shape:

```ts
type KnowledgeDocument = {
  id: string;
  term: string;
  explanation: string;
  relatedTerms: string[];
};
```

If backend is FastAPI, implement or reuse:

```py
@router.get("/knowledge-documents")
def list_knowledge_documents():
    ...
```

The backend should read from an environment variable first:

```text
FINRAG_CHUNK_PATH
```

Fallback relative path:

```text
data/processed/final_chunk.json
```

Implementation note:

- Add `FINRAG_CHUNK_PATH` handling in `src/common/config.py`, ideally by making `default_chunk_json_path` environment-overridable.
- The user is responsible for adding `FINRAG_CHUNK_PATH` to `.env`.

### Acceptance criteria

- Clicking `지식 문서` opens the screen.
- JSON data is loaded and rendered.
- Terms can be filtered by `ㄱ`, `ㄴ`, `ㄷ`, etc.
- English terms can be filtered by `abc`.
- Search works across term, explanation, and related terms.
- Malformed rows do not crash the page.
- Loading and error states are visible.

---

## Task 08 — Add Admin-only Settings screen

### Current issue

The sidebar contains `설정`, but the screen is not implemented. It should only be visible to Admin users.

### Required behavior

- Show `설정` tab only when the current user role is Admin.
- Hide `설정` tab for non-admin users.
- Implement a settings screen with controls for retrieval configuration.

### Required controls

#### Search method

Label:

```text
Search 방식 선택
```

Options:

- `Dense`
- `Sparse (BM25)`
- `Hybrid`

Suggested value type:

```ts
type SearchMode = "dense" | "sparse" | "hybrid";
```

#### Hybrid Search Top-K

Label:

```text
Hybrid Search Top-K
```

Input type:

- number input or slider

Validation:

- minimum: `1`
- maximum: `50`
- default: `10`

This setting is relevant when `Search 방식 선택 = Hybrid`.

Behavior:

- Disable the Top-K control unless `Hybrid` is selected, or keep it enabled but clearly mark it as Hybrid-only.
- Persist settings in localStorage.

Suggested storage key:

```text
finrag.retrievalSettings
```

Suggested schema:

```ts
type RetrievalSettings = {
  searchMode: "dense" | "sparse" | "hybrid";
  hybridTopK: number;
  updatedAt: string;
};
```

### Optional backend integration

If an existing backend config API exists, wire the UI to it. Otherwise, localStorage persistence is acceptable for this task.

Possible endpoint shape:

```http
GET /api/settings/retrieval
PUT /api/settings/retrieval
```

### Acceptance criteria

- Admin user can see `설정` in the sidebar.
- Non-admin user cannot see `설정`.
- Admin user can select Dense/Sparse/Hybrid.
- Admin user can set Hybrid Top-K.
- Invalid Top-K values are blocked or normalized.
- Settings persist after refresh.

---

## Task 09 — Navigation and route consistency

### Required behavior

Ensure sidebar navigation works consistently:

- `대화` → Chat screen
- `대시보드` → Monitoring dashboard screen at `/dashboard`
- `지식 문서` → Knowledge Documents screen
- `설정` → Admin-only Settings screen
- `/admin` → redirect to `/dashboard`

### Acceptance criteria

- Active sidebar item is highlighted.
- Browser refresh preserves the current route if router is used.
- No sidebar item is a dead button.
- `/admin` redirects to `/dashboard`.

---

## Task 10 — Cleanup and quality pass

### Required behavior

- Remove unused imports.
- Remove unused state and dead handlers.
- Remove hard-coded dummy recent conversations.
- Keep Korean labels consistent.
- Ensure TypeScript build passes.
- Ensure lint/test commands pass if configured.

### Final deliverables

At the end of the task, provide:

1. Summary of changed files
2. Implementation notes
3. Any assumptions made
4. How to run locally
5. Test results
