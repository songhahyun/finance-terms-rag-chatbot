# TASK 004: Chat UI Source Display and User-Scoped Conversations

## 0. Context

- Goal: Improve the chat screen source-document UI, loading feedback, sidebar usability, and prevent chat history leakage between logged-in users.
- Primary frontend files:
  - `frontend-web/src/pages/chat-page.tsx`
  - `frontend-web/src/app/app-shell.tsx`
  - `frontend-web/src/lib/conversations.ts`
  - `frontend-web/src/types/api.ts`
- Primary backend files:
  - `backend/app/schemas/chat.py`
  - `src/serving/rag_service.py`
  - `src/common/schema.py`
- Relevant processed data:
  - `data/processed/final_chunk.json`

## 1. Problem Summary

The current chat UI always renders a source-document area whenever an assistant message has a `sources` field, even when the query intent is not `needs_rag`.

For non-RAG routed queries such as `needs_web`, `clarify`, or `simple`, the backend returns `sources: []`. The frontend still renders:

```text
참고 문서 (0)
```

This makes it look like source retrieval was attempted or source documents are relevant when the query was intentionally routed away from RAG.

The source-document display is also too limited and too implementation-oriented:

- It shows the raw PDF path from `source`.
- It truncates source display to 3 items with `slice(0, 3)`.
- It is always expanded under the assistant answer.

Chat history is stored in browser `localStorage` under one global key. Because the storage key is not scoped by authenticated user, admin and regular user accounts on the same browser share the same local chat history after logout/login.

## 2. Root Cause Notes

### 2.1 Source Visibility

Current UI logic in `frontend-web/src/pages/chat-page.tsx` uses a truthy check:

```tsx
{message.sources && (...)}
```

An empty array is truthy in JavaScript, so the source block renders even when `message.sources.length === 0`.

The UI also does not store or check the backend `intent` field per message, so it cannot distinguish `needs_rag` from `needs_web`, `clarify`, or `simple`.

### 2.2 Source Format

The backend source item currently exposes:

- `chunk_id`
- `source`
- `text`

`source` is a raw local file path such as:

```text
D:\AI\projects\finance-terms-rag-chatbot\data\raw\2020_경제금융용어 700선.pdf
```

The processed chunk data already contains the desired semantic fields:

- `용어`
- `설명`
- `metadata.연관검색어`

`src/common/schema.py` converts chunks into LangChain documents with metadata:

- `term`
- `related_terms`
- `source`
- `page`

`src/serving/rag_service.py` can serialize those fields into the chat response.

### 2.3 Source Count

The frontend currently limits display to 3 source items:

```tsx
message.sources.slice(0, 3).map(...)
```

This is the direct reason only 3 sources are shown even when the backend returns more.

### 2.4 Loading Feedback

The chat page sets `isLoading`, but it does not render an assistant placeholder message while the request is pending. The current UX only disables the send button until the backend response arrives.

### 2.5 Sidebar Width

The app shell uses a fixed desktop sidebar grid column:

```tsx
md:grid-cols-[220px_1fr]
```

Recent conversation titles are rendered in that narrow column with `truncate`, causing longer Korean titles to be clipped.

### 2.6 User-Scoped Chat History

`frontend-web/src/lib/conversations.ts` stores all conversations under one key:

```ts
finrag.conversations
```

This is browser-local state, not backend session state. Logging out clears auth state, but it does not clear or switch the conversation storage key.

## 3. Requirements

### 3.1 Chat Screen: Source Visibility

Only show the source-document section when all conditions are true:

- assistant message intent is `needs_rag`
- source list exists
- source list has at least one item

Do not render `참고 문서 (0)` for `needs_web`, `clarify`, or `simple`.

### 3.2 Chat Screen: Source Format

Change source display from raw PDF path to the semantic format:

```text
용어명: XX
용어 설명: XX
연관 용어: XX, XX
```

If `연관 용어` is empty or `"없음"`, display a consistent empty-state value such as:

```text
연관 용어: 없음
```

### 3.3 Chat Screen: Source Count

Display every source returned by the backend. Remove the hard-coded `slice(0, 3)` limit.

The backend request currently sends `k: 5`, so the normal result count is expected to be up to 5 unless the request value changes.

### 3.4 Chat Screen: Collapsible Sources

The source-document section should be collapsed by default.

Render a toggle button such as:

```text
참고 문서 보기 (5)
참고 문서 숨기기 (5)
```

The source items should appear only after the user opens the section.

### 3.5 Chat Screen: Pending Answer Animation

When the user sends a question:

- immediately show the user's message in the chat
- show an assistant bubble while the answer is being generated
- use the chatbot icon/avatar
- show a repeated `"..."` style animation inside the assistant bubble

The pending bubble should be replaced or followed by the real assistant answer when the API response arrives.

### 3.6 Sidebar: Expandable Width

Add a sidebar expand/collapse control.

The expanded state should give recent conversation titles more room than the current 220px sidebar.

Example titles that should become easier to read:

```text
인플레이션과 스태그플레이션의 차이...
금리, 채권 가격, 주가 사이의 ...
```

### 3.7 Chat History Isolation

Separate locally stored conversations by authenticated user.

Expected behavior:

1. Login as `admin`.
2. Chat.
3. Logout.
4. Login as a regular `user`.
5. The regular user should not see the admin user's local conversation history.

Implementation should scope the frontend storage key by username, for example:

```text
finrag.conversations.admin
finrag.conversations.user
```

## 4. Sub-task Breakdown

### Task 004-1: Backend: Enrich Source Metadata

- Status: Not started
- Files:
  - `backend/app/schemas/chat.py`
  - `src/serving/rag_service.py`
- Work:
  - Extend `SourceItem` with `term`, `explanation`, and `related_terms`.
  - Serialize retrieved document metadata into those fields.
  - Preserve existing `chunk_id`, `source`, and `text` fields for compatibility.
- Done when:
  - Chat API responses include semantic source fields for `needs_rag` results.
  - Existing response schema tests still pass.

### Task 004-2: Frontend: Store Intent Per Assistant Message

- Status: Not started
- Files:
  - `frontend-web/src/types/api.ts`
  - `frontend-web/src/lib/conversations.ts`
  - `frontend-web/src/pages/chat-page.tsx`
- Work:
  - Add routing metadata to frontend `ChatResponse`.
  - Store `response.intent` on assistant `ChatMessage`.
  - Keep older saved messages without `intent` from breaking the UI.
- Done when:
  - New assistant messages retain the backend intent.
  - The chat screen can distinguish `needs_rag` from non-RAG intents.

### Task 004-3: Frontend: Render Sources Only for RAG Answers

- Status: Not started
- Files:
  - `frontend-web/src/pages/chat-page.tsx`
- Work:
  - Render source documents only when `message.intent === "needs_rag"`.
  - Require `message.sources.length > 0`.
  - Remove the `참고 문서 (0)` state for `needs_web`, `clarify`, and `simple`.
- Done when:
  - Non-RAG answers never show an empty source section.

### Task 004-4: Frontend: Redesign Source Document Display

- Status: Not started
- Files:
  - `frontend-web/src/pages/chat-page.tsx`
- Work:
  - Replace raw PDF path display with:

    ```text
    용어명: XX
    용어 설명: XX
    연관 용어: XX, XX
    ```

  - Show `연관 용어: 없음` when there are no related terms.
  - Remove the current `slice(0, 3)` limit and render all returned sources.
- Done when:
  - Every returned source is visible after opening the source area.
  - The UI no longer displays local file paths as the primary source label.

### Task 004-5: Frontend: Make Source Documents Collapsible

- Status: Not started
- Files:
  - `frontend-web/src/pages/chat-page.tsx`
- Work:
  - Collapse source documents by default.
  - Add a per-message toggle button with the source count.
  - Keep expanded/collapsed state stable while viewing the conversation.
- Done when:
  - A `needs_rag` answer initially shows only a source toggle.
  - Clicking the toggle reveals and hides the source list.

### Task 004-6: Frontend: Add Pending Assistant Bubble

- Status: Not started
- Files:
  - `frontend-web/src/pages/chat-page.tsx`
- Work:
  - Show the user's message immediately after submit.
  - Render a chatbot assistant bubble while the API request is pending.
  - Show a repeated `"..."` animation inside the pending bubble.
  - Replace or follow the pending bubble with the real assistant answer when the response arrives.
- Done when:
  - The user gets immediate visual feedback after pressing send.
  - The send button loading state and pending bubble clear after success or failure.

### Task 004-7: Frontend: Add Expandable Sidebar

- Status: Not started
- Files:
  - `frontend-web/src/app/app-shell.tsx`
- Work:
  - Add a sidebar expand/collapse button.
  - Increase desktop sidebar width in expanded mode.
  - Keep recent conversation titles readable in expanded mode.
- Done when:
  - Long recent conversation titles have more horizontal space after expanding the sidebar.

### Task 004-8: Frontend: Scope Conversation History by User

- Status: Not started
- Files:
  - `frontend-web/src/lib/conversations.ts`
  - `frontend-web/src/pages/chat-page.tsx`
  - `frontend-web/src/app/app-shell.tsx`
- Work:
  - Derive the localStorage key from the authenticated username.
  - Load and save conversations with `user?.username`.
  - Ensure logout/login as another user switches to that user's conversation list.
- Done when:
  - Admin conversations are not shown to a regular user in the same browser.
  - Regular user conversations are not shown to admin unless that user logs back in.

### Task 004-9: Verification

- Status: Not started
- Work:
  - Run frontend build/type checks.
  - Run backend chat schema and routing tests.
  - Manually verify RAG, `needs_web`, `clarify`, sidebar, loading bubble, and user-switch scenarios.
- Done when:
  - Automated checks pass or failures are documented.
  - Manual acceptance criteria are checked.

### Task 004-10: Frontend: Upgrade Pending Animation to Bouncing Dots

- Status: Not started
- Files:
  - `frontend-web/src/pages/chat-page.tsx`
  - `frontend-web/src/styles.css`
- Work:
  - Upgrade the pending assistant bubble animation from a repeated text `"..."` indicator to a Bouncing Dots / Three Dots animation.
  - Render three small dots inside the assistant bubble.
  - Animate the dots with staggered vertical bounce or opacity timing.
  - Keep the animation visually aligned with the existing chatbot avatar and message bubble style.
- Done when:
  - While the chatbot answer is being generated, the pending assistant bubble shows three animated dots instead of static or repeated text.
  - The animation does not shift the message layout while running.
  - The animation clears when the real assistant answer is rendered or when the request fails.

### Task 004-11: Frontend: Generate Better Conversation Titles

- Status: Not started
- Files:
  - `frontend-web/src/lib/conversations.ts`
  - `frontend-web/src/pages/chat-page.tsx`
  - `frontend-web/src/app/app-shell.tsx`
- Work:
  - Improve chat room title generation so titles summarize the user's first question instead of cutting it at a fixed character count.
  - Avoid titles such as:

    ```text
    sk 하이닉스 올해 실적 전망 어...
    ```

  - Prefer concise titles such as:

    ```text
    sk 하이닉스 올해 실적 전망
    ```

  - Implement a deterministic frontend title helper first, using simple Korean question-ending cleanup and length control.
  - Keep title generation local to the frontend unless the task document is updated to introduce an LLM/backend title-generation API.
- Done when:
  - A first user question like `sk 하이닉스 올해 실적 전망 어떻게 보나요?` produces a title close to `sk 하이닉스 올해 실적 전망`.
  - The sidebar and chat header show the improved title.
  - Existing saved conversations without the new title logic still render normally.

### Task 004-12: Frontend: Connect Retrieval Settings to Chat API

- Status: Not started
- Files:
  - `frontend-web/src/pages/settings-page.tsx`
  - `frontend-web/src/pages/chat-page.tsx`
  - `frontend-web/src/lib/conversations.ts` or a new frontend settings helper module if needed
  - `frontend-web/src/types/api.ts`
- Work:
  - Reuse the settings screen values currently stored in `localStorage`:
    - `searchMode`
    - `hybridTopK`
  - Use `searchMode` as the `mode` value in `postChat`.
  - Use `hybridTopK` as the `k` value in `postChat` when the selected mode is `hybrid`.
  - Keep a safe fallback to the current behavior when settings are missing or invalid:

    ```ts
    mode: "hybrid"
    k: 5
    ```

  - Avoid duplicating settings parsing logic between the settings page and chat page.
  - Ensure frontend settings values are compatible with the backend `ChatRequest` schema.
- Done when:
  - Changing `Search 방식 선택` in the settings screen changes the next chat request `mode`.
  - Changing `Hybrid Search Top-K` in the settings screen changes the next chat request `k` for hybrid mode.
  - Missing or malformed local settings do not break chat submission.
  - Frontend build/type checks pass.

## 5. Proposed Implementation

### 5.1 Backend Response Schema

Extend `SourceItem` with optional semantic fields:

- `term`
- `explanation`
- `related_terms`

Keep existing fields for compatibility:

- `chunk_id`
- `source`
- `text`

### 5.2 Backend Source Serialization

Update `RAGService._serialize_result()` to populate semantic fields from retrieved document metadata:

- `term` from `doc.metadata["term"]`
- `related_terms` from `doc.metadata["related_terms"]`
- `explanation` from `doc.page_content`, with the term heading removed when possible

Normalize related terms:

- list input remains a list
- string `"없음"` becomes `[]`
- comma-separated string becomes a trimmed list

### 5.3 Frontend Types

Update `SourceItem` and `ChatResponse` in `frontend-web/src/types/api.ts` to include:

- source semantic fields
- `intent`
- routing metadata already returned by the backend

Update `ChatMessage` to store assistant message `intent`.

### 5.4 Frontend Source UI

In `chat-page.tsx`:

- render sources only for `message.intent === "needs_rag"`
- require `message.sources.length > 0`
- remove source slicing
- replace raw path display with term, explanation, and related terms
- add per-message collapse state for the source section

### 5.5 Frontend Pending UI

In `chat-page.tsx`:

- save the user message before awaiting `postChat`
- track the pending conversation id
- render a temporary assistant loading bubble while `isLoading` is true for that conversation
- clear pending state when the request finishes

### 5.6 Frontend Conversation Storage

In `conversations.ts`:

- add a helper that derives the storage key from username
- update `loadConversations(username)` and `saveConversations(conversations, username)`

In `chat-page.tsx` and `app-shell.tsx`:

- read `user` from auth context
- pass `user?.username` to conversation load/save calls

### 5.7 Sidebar

In `app-shell.tsx`:

- add expanded/collapsed sidebar state
- add an icon button for the toggle
- increase the sidebar width in expanded mode
- keep the current compact width as the collapsed/default width unless product preference says otherwise

## 6. Acceptance Criteria

- `needs_web`, `clarify`, and `simple` answers do not show a source-document section.
- `needs_rag` answers with sources show a collapsed source toggle.
- Opening the toggle shows all returned sources, not only the first 3.
- Each source displays term name, explanation, and related terms instead of a raw file path.
- Sending a question immediately shows the user's message and a chatbot loading bubble.
- The chatbot loading bubble uses a Bouncing Dots / Three Dots animation.
- Sidebar can be expanded so recent conversation titles have more horizontal space.
- New conversation titles summarize the first user question instead of using a fixed truncation only.
- Settings screen retrieval options are reflected in subsequent chat API requests.
- Admin and regular user local chat histories are separated after logout/login.
- Existing chat API consumers remain compatible with `chunk_id`, `source`, and `text`.

## 7. Open Questions

- Should the sidebar default to collapsed or expanded on desktop?
- Should expanded/collapsed sidebar state persist in `localStorage`?
- Should source explanations be shown in full, or should long explanations be clamped with a separate "더보기" interaction?
- Should chat history isolation be username-based only, or should it use a stable backend user id if one is added later?
- Should conversation title generation remain deterministic in the frontend, or should a backend/LLM title-generation endpoint be added later?
- What maximum title length should be used for Korean and mixed Korean/English titles?
- For non-hybrid search modes, should `hybridTopK` still be sent as `k`, or should each search mode have its own top-k setting?

## 8. Suggested Verification

Run frontend type/build checks:

```bash
cd frontend-web
npm run build
```

Run backend tests covering chat response schema and routing:

```bash
pytest tests/test_chat_response_schema.py tests/test_rag_service_query_intent.py
```

Manual browser checks:

- ask a RAG finance-term question and open source documents
- ask a current-market question that routes to `needs_web`
- ask an ambiguous question that routes to `clarify`
- verify source sections are absent for non-RAG answers
- verify the pending assistant bubble uses animated three dots
- verify first-question title generation with a long Korean question
- verify settings screen `searchMode` and `hybridTopK` affect subsequent `/api/chat` payloads
- verify user-specific conversation history after admin/user logout-login switch
