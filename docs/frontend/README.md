# README.md

## FinRAG Chatbot Frontend Implementation Guide

This document describes the expected frontend behavior for the FinRAG Chatbot UI implementation. Use this together with `docs/CODEX_TASKS.md` and `docs/TESTING.md`.

---

## Product scope

FinRAG Chatbot is a finance-domain RAG chatbot UI with the following screens:

1. **Login**
2. **Chat**
3. **Monitoring Dashboard**
4. **Knowledge Documents**
5. **Admin Settings**

The existing TypeScript frontend already has the base visual shell. The implementation goal is to complete missing interactions, remove dead UI affordances, replace dummy data, and add the missing sidebar screens.

---

## Confirmed Decisions

- Use `/dashboard` as the canonical Monitoring Dashboard route.
- Keep `/admin` as a backward-compatible redirect to `/dashboard`.
- Store chat history in `localStorage` under `finrag.conversations`.
- Chat history must survive refresh, browser restart, and logout on the same browser and origin.
- Do not clear `finrag.conversations` during logout.
- Serve Knowledge Documents through a backend endpoint.
- Manage the chunk JSON path through `src/common/config.py`; `FINRAG_CHUNK_PATH` should override the default `data/processed/final_chunk.json` path.
- The user will add `FINRAG_CHUNK_PATH` to `.env`.

---

## Screens

### 1. Login screen

Purpose:

- Let a user log in.
- Let a user toggle password visibility.
- Provide a basic forgot-password flow.

Required elements:

- App title: `FinRAG Chatbot`
- Username or ID input
- Password input
- Password visibility toggle button
- Login button
- Remember ID checkbox
- Forgot password link: `비밀번호 찾기`
- Signup link can remain visual-only unless signup is already implemented.

Password behavior:

- Default password input type: `password`
- Clicking the eye icon toggles between `password` and `text`
- The typed password must remain unchanged while toggling

Forgot-password behavior:

- Clicking `비밀번호 찾기` should open a modal or route.
- Required fields:
  - email or account ID input
  - submit button
  - back-to-login action
- For now, show a mock success message after validation. Do not require a real email backend.

---

### 2. Chat screen

Purpose:

- Let the user ask finance questions.
- Show conversation history.
- Keep recent conversations in the sidebar.

Required layout:

- Top bar:
  - user icon
  - `admin 님`
  - `로그아웃`
- Left sidebar:
  - `+ 새 대화`
  - `대화`
  - `대시보드`
  - `지식 문서`
  - `설정` only for Admin users
  - `최근 대화`
- Main chat area:
  - conversation title
  - message list
  - input box
  - send button
  - disclaimer text

Remove:

- The unused downward arrow beside `admin 님`
- Hard-coded recent conversation dummy values

Recent conversation behavior:

- When a user sends the first message in a new conversation, create a conversation record.
- Generate a title from the first message.
- Add it to the `최근 대화` list.
- Store conversations in `localStorage`.
- Conversations should remain available after refresh, browser restart, and logout on the same browser and origin.
- The logout flow must not remove `finrag.conversations`.

Suggested localStorage key:

```text
finrag.conversations
```

Suggested data model:

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

---

### 3. Monitoring Dashboard screen

Purpose:

- Show chat logs and basic operational metrics.

Required fixes:

- Remove the unused top tab bar:
  - `채팅 로그`
  - `사용 통계`
  - `지식 문서 통계`
- Increase the height of these chart cards:
  - `스테이지별 평균 처리시간`
  - `스테이지별 성공률`
- Prevent axis labels from overflowing:
  - `평균 처리시간(초)`
  - `성공률(%)`

Recommended chart card sizing:

```css
.dashboard-chart-card {
  min-height: 320px;
}

.dashboard-chart-body {
  padding-bottom: 32px;
}
```

If the project uses Recharts, use sufficient chart margin:

```tsx
margin={{ top: 16, right: 24, bottom: 40, left: 24 }}
```

---

### 4. Knowledge Documents screen

Purpose:

- Let users inspect the RAG source chunks used by the chatbot.

Sidebar entry:

```text
지식 문서
```

Data source:

```text
data/processed/final_chunk.json
```

Source path in local development:

```text
D:\AI\projects\finance-terms-rag-chatbot\data\processed\final_chunk.json
```

Browser warning:

- The frontend must not attempt to read the Windows path directly.
- Use a backend endpoint. Static asset exposure is no longer the target implementation.

Backend API:

```http
GET /knowledge-documents
```

Response:

```ts
type KnowledgeDocument = {
  id: string;
  term: string;
  explanation: string;
  relatedTerms: string[];
};
```

Backend path configuration:

- Read the chunk JSON path from `get_settings().default_chunk_json_path`.
- In `src/common/config.py`, make `default_chunk_json_path` use `FINRAG_CHUNK_PATH` when set.
- Fall back to `data/processed/final_chunk.json`.

Required fields to display:

- `용어`
- `설명`
- `연관검색어`

Required UI:

- Page title: `지식 문서`
- Search input: `용어 또는 설명 검색`
- Initial consonant filters:
  - `전체`, `ㄱ`, `ㄴ`, `ㄷ`, `ㄹ`, `ㅁ`, `ㅂ`, `ㅅ`, `ㅇ`, `ㅈ`, `ㅊ`, `ㅋ`, `ㅌ`, `ㅍ`, `ㅎ`
- Cards or table rows for each knowledge document

Filtering behavior:

- `전체` shows all documents.
- Selecting a consonant shows terms whose first Hangul syllable maps to that initial consonant.
- Search matches term, explanation, and related terms.
- Empty state:
  - `조건에 맞는 지식 문서가 없습니다.`

---

### 5. Admin Settings screen

Purpose:

- Let Admin users configure retrieval behavior.

Visibility:

- Show `설정` tab only when the current user is Admin.
- Hide it for non-admin users.

Required controls:

#### Search 방식 선택

Options:

- `Dense`
- `Sparse (BM25)`
- `Hybrid`

Internal values:

```ts
type SearchMode = "dense" | "sparse" | "hybrid";
```

#### Hybrid Search Top-K

- Number input or slider
- Minimum: `1`
- Maximum: `50`
- Default: `10`
- Relevant for Hybrid search mode

Suggested localStorage key:

```text
finrag.retrievalSettings
```

Suggested model:

```ts
type RetrievalSettings = {
  searchMode: "dense" | "sparse" | "hybrid";
  hybridTopK: number;
  updatedAt: string;
};
```

---

## Routing expectations

Use existing routing if present. Otherwise, implement a simple route structure equivalent to:

```text
/login
/chat
/dashboard
/admin -> /dashboard
/knowledge-documents
/settings
```

Sidebar behavior:

| Sidebar item | Target screen |
|---|---|
| `대화` | Chat |
| `대시보드` | Monitoring Dashboard |
| `지식 문서` | Knowledge Documents |
| `설정` | Admin Settings |
| `+ 새 대화` | New empty chat session |

---

## Role handling

If the app already has authentication/authorization state, use it.

If it does not, use a minimal placeholder model:

```ts
type User = {
  id: string;
  name: string;
  role: "admin" | "user";
};
```

For current development, `admin` can be treated as Admin.

Do not expose the settings page to non-admin users. If a non-admin user navigates directly to `/settings`, redirect to `/chat` or show a simple unauthorized message:

```text
관리자만 접근할 수 있습니다.
```

---

## Data and persistence

Use localStorage for frontend-only persistence unless a backend API already exists.

Chat conversations are intentionally stored in `localStorage` and are not cleared on logout. This means the history is browser- and origin-local: it persists for the same deployed domain in the same browser, but it does not sync across browsers, devices, or domains.

Suggested keys:

```text
finrag.conversations
finrag.retrievalSettings
```

Do not use dummy hard-coded recent conversation items in the production UI.

---

## Implementation priorities

1. Fix no-op UI elements:
   - password visibility toggle
   - forgot password flow
   - remove admin dropdown arrow
2. Replace hard-coded recent conversations with real chat state.
3. Fix dashboard layout issues.
4. Add Knowledge Documents screen.
5. Add Admin-only Settings screen.
6. Run build, lint, and tests.

---

## Definition of done

The implementation is complete when:

- All sidebar items route to implemented screens.
- No visible button or icon is a dead click target.
- Login password visibility works.
- Forgot-password flow is visible and validates input.
- Recent conversations are generated from actual user messages.
- Dashboard tabs are removed.
- Dashboard chart labels no longer overflow.
- Knowledge documents load from `final_chunk.json` through a safe frontend-accessible path.
- Knowledge document file path is configurable through `FINRAG_CHUNK_PATH` in backend settings.
- Settings are visible only to Admin users.
- TypeScript build passes.
- Tests pass or manual testing evidence is documented.
