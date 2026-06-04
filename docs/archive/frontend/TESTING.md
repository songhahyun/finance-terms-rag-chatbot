# TESTING.md

## FinRAG Chatbot Frontend Testing Guide

This document defines the test plan for the FinRAG Chatbot frontend implementation.

Run automated tests where the repository supports them. If the repository does not yet have a test framework, perform the manual test checklist and document the result.

---

## Recommended commands

Use the commands that match the package manager used by the repository.

### Install dependencies

```bash
npm install
```

or

```bash
pnpm install
```

or

```bash
yarn install
```

### Development server

```bash
npm run dev
```

### TypeScript build

```bash
npm run build
```

### Lint

```bash
npm run lint
```

### Unit tests

```bash
npm test
```

or

```bash
npm run test
```

If any script does not exist, note that clearly in the final implementation summary.

---

## Test environment

Test with:

- Chrome or Edge latest stable version
- Desktop viewport matching the screenshots
- Narrow viewport around 390px width if the app has responsive behavior
- Fresh browser profile or cleared localStorage for first-run behavior

Useful localStorage keys to clear:

```js
localStorage.removeItem("finrag.conversations");
localStorage.removeItem("finrag.retrievalSettings");
```

Confirmed persistence policy:

- `finrag.conversations` is stored in `localStorage`.
- Chat history should survive refresh, browser restart, and logout on the same browser and origin.
- Do not treat logout as a reason to clear chat history.

Confirmed route policy:

- `/dashboard` is the canonical dashboard route.
- `/admin` should redirect to `/dashboard`.

Knowledge document path policy:

- The backend should read the chunk path from `src/common/config.py`.
- `FINRAG_CHUNK_PATH` should override the default `data/processed/final_chunk.json` path.
- The user will add `FINRAG_CHUNK_PATH` to `.env`.

---

## Manual test checklist

## 1. Login screen

### 1.1 Password hidden by default

Steps:

1. Open the login screen.
2. Type a password into the password input.

Expected result:

- The password is masked.
- Input type is effectively `password`.

Status:

```text
PASS / FAIL:
Notes:
```

---

### 1.2 Password visibility toggle

Steps:

1. Type a password.
2. Click the eye icon.
3. Click the eye icon again.

Expected result:

- First click shows the password as plain text.
- Second click hides it again.
- The typed password value is not cleared.
- No layout shift occurs.

Status:

```text
PASS / FAIL:
Notes:
```

---

### 1.3 Forgot password opens flow

Steps:

1. Click `비밀번호 찾기`.

Expected result:

- A modal or page appears.
- It contains:
  - `비밀번호 찾기`
  - input field
  - `재설정 링크 보내기`
  - `로그인으로 돌아가기`

Status:

```text
PASS / FAIL:
Notes:
```

---

### 1.4 Forgot password validation

Steps:

1. Open forgot-password flow.
2. Submit with empty input.

Expected result:

- Validation message appears.
- The app does not crash.

Status:

```text
PASS / FAIL:
Notes:
```

---

### 1.5 Forgot password success state

Steps:

1. Enter a valid email or account ID.
2. Submit.

Expected result:

- Success message appears:
  - `입력하신 계정으로 비밀번호 재설정 안내를 보냈습니다.`
- User can return to login screen.

Status:

```text
PASS / FAIL:
Notes:
```

---

## 2. Chat screen

### 2.1 Admin dropdown arrow removed

Steps:

1. Open the chat screen.
2. Inspect the top bar near `admin 님`.

Expected result:

- There is no downward arrow beside `admin 님`.
- There is no dead dropdown click target.
- `로그아웃` remains visible.

Status:

```text
PASS / FAIL:
Notes:
```

---

### 2.2 No hard-coded recent conversations

Steps:

1. Clear localStorage.
2. Open the chat screen.
3. Inspect `최근 대화`.

Expected result:

- The old dummy values are not shown:
  - `ELS 상품 설명해줘`
  - `신용등급 하락 원인`
  - `금리 인상 영향 분석`
  - `회사채 투자 리스크`
  - `환율 전망 알려줘`
- Empty state appears:
  - `아직 최근 대화가 없습니다.`

Status:

```text
PASS / FAIL:
Notes:
```

---

### 2.3 Sending first message creates recent conversation

Steps:

1. Open a new chat.
2. Send: `ELS 상품 설명해줘`.

Expected result:

- User message appears in the chat area.
- A recent conversation item appears in the sidebar.
- The title is generated from the user message.

Status:

```text
PASS / FAIL:
Notes:
```

---

### 2.4 Recent conversation persists after refresh

Steps:

1. Send a message.
2. Refresh the browser.
3. Inspect `최근 대화`.

Expected result:

- The generated recent conversation remains visible.

Status:

```text
PASS / FAIL:
Notes:
```

---

### 2.4a Recent conversation persists after logout

Steps:

1. Send a message and confirm it appears under `최근 대화`.
2. Click `로그아웃`.
3. Log in again with the same browser and deployed origin.
4. Inspect `최근 대화`.

Expected result:

- The generated recent conversation remains visible.
- `finrag.conversations` was not removed by the logout flow.

Status:

```text
PASS / FAIL:
Notes:
```

---

### 2.5 Clicking recent conversation restores messages

Steps:

1. Create at least one conversation with messages.
2. Click its item under `최근 대화`.

Expected result:

- The corresponding messages are loaded into the chat area.
- Active conversation state updates.

Status:

```text
PASS / FAIL:
Notes:
```

---

### 2.6 New chat resets active conversation

Steps:

1. Open an existing conversation.
2. Click `+ 새 대화`.

Expected result:

- Chat area becomes empty or shows the default empty state.
- New user input creates a separate conversation.

Status:

```text
PASS / FAIL:
Notes:
```

---

## 3. Dashboard screen

### 3.1 Tab bar removed

Steps:

1. Open the dashboard screen.

Expected result:

- These labels are not visible:
  - `채팅 로그`
  - `사용 통계`
  - `지식 문서 통계`
- Dashboard content appears directly below the title/filter area.

Status:

```text
PASS / FAIL:
Notes:
```

---

### 3.2 Chart cards are taller

Steps:

1. Open the dashboard screen.
2. Inspect:
   - `스테이지별 평균 처리시간`
   - `스테이지별 성공률`

Expected result:

- Both chart cards are visibly taller than before.
- Desktop two-column layout is preserved.

Status:

```text
PASS / FAIL:
Notes:
```

---

### 3.3 Chart labels do not overflow

Steps:

1. Inspect bottom axis labels:
   - `평균 처리시간(초)`
   - `성공률(%)`

Expected result:

- Labels are fully visible inside their respective cards.
- No text is clipped or outside the card boundary.

Status:

```text
PASS / FAIL:
Notes:
```

---

## 4. Knowledge Documents screen

### 4.1 Sidebar route works

Steps:

1. Click `지식 문서` in the sidebar.

Expected result:

- Knowledge Documents screen opens.
- Page title `지식 문서` is visible.
- Active sidebar item is highlighted.

Status:

```text
PASS / FAIL:
Notes:
```

---

### 4.2 Data loads from final_chunk.json

Steps:

1. Open the Knowledge Documents screen.

Expected result:

- Terms from `final_chunk.json` are displayed.
- The backend reads the file path through `src/common/config.py`.
- If `FINRAG_CHUNK_PATH` is set in `.env`, that path is used.
- If `FINRAG_CHUNK_PATH` is not set, `data/processed/final_chunk.json` is used.
- Each row/card shows:
  - `용어`
  - `설명`
  - `연관검색어`

Status:

```text
PASS / FAIL:
Notes:
```

---

### 4.3 Loading and error states

Steps:

1. Temporarily make the data endpoint or asset unavailable.
2. Open the screen.

Expected result:

- Loading state appears while fetching.
- Error state appears if fetch fails.
- App does not crash.

Status:

```text
PASS / FAIL:
Notes:
```

---

### 4.4 Initial consonant filter

Steps:

1. Click `ㄱ`.
2. Click `ㄴ`.
3. Click `전체`.

Expected result:

- `ㄱ` shows terms starting with the Korean initial consonant ㄱ.
- `ㄴ` shows terms starting with ㄴ.
- `전체` restores all terms.
- Double consonants such as ㄲ are grouped under the matching base consonant ㄱ.

Status:

```text
PASS / FAIL:
Notes:
```

---

### 4.5 Search works

Steps:

1. Search by a known term.
2. Search by a word inside an explanation.
3. Search by a related term.

Expected result:

- Matching rows are shown.
- Non-matching rows are hidden.
- Search is case-insensitive for English text if English exists.

Status:

```text
PASS / FAIL:
Notes:
```

---

### 4.6 Empty state

Steps:

1. Enter a query that should not match anything.

Expected result:

- Empty state appears:
  - `조건에 맞는 지식 문서가 없습니다.`

Status:

```text
PASS / FAIL:
Notes:
```

---

## 5. Admin Settings screen

### 5.1 Settings visible to Admin

Steps:

1. Log in or run the app as Admin.
2. Inspect the sidebar.

Expected result:

- `설정` is visible.
- Clicking it opens the Settings screen.

Status:

```text
PASS / FAIL:
Notes:
```

---

### 5.2 Settings hidden from non-admin

Steps:

1. Switch current user role to non-admin.
2. Inspect the sidebar.

Expected result:

- `설정` is not visible.

Status:

```text
PASS / FAIL:
Notes:
```

---

### 5.3 Direct non-admin access blocked

Steps:

1. As a non-admin user, navigate directly to `/settings`.

Expected result:

- User is redirected to `/chat`, or
- User sees:
  - `관리자만 접근할 수 있습니다.`

Status:

```text
PASS / FAIL:
Notes:
```

---

### 5.4 Search mode selection

Steps:

1. Open Settings as Admin.
2. Select each option:
   - Dense
   - Sparse (BM25)
   - Hybrid

Expected result:

- Selected option updates correctly.
- UI state is clear.

Status:

```text
PASS / FAIL:
Notes:
```

---

### 5.5 Hybrid Search Top-K validation

Steps:

1. Select Hybrid.
2. Enter valid value: `10`.
3. Try invalid values:
   - `0`
   - `-1`
   - `51`
   - non-number text if input allows it

Expected result:

- Valid value is accepted.
- Invalid values are blocked, clamped, or show validation error.
- Final saved value is between 1 and 50.

Status:

```text
PASS / FAIL:
Notes:
```

---

### 5.6 Settings persist after refresh

Steps:

1. Set Search mode to `Hybrid`.
2. Set Top-K to `15`.
3. Refresh browser.
4. Reopen Settings.

Expected result:

- Search mode remains `Hybrid`.
- Top-K remains `15`.

Status:

```text
PASS / FAIL:
Notes:
```

---

## 6. Routing and navigation

### 6.1 Sidebar navigation

Steps:

1. Click each sidebar item:
   - `대화`
   - `대시보드`
   - `지식 문서`
   - `설정` as Admin

Expected result:

- Each item opens the correct screen.
- Active item styling updates.
- No item is a dead button.
- `대시보드` navigates to `/dashboard`.

Status:

```text
PASS / FAIL:
Notes:
```

---

### 6.2 Refresh preserves route

Steps:

1. Open `대시보드`.
2. Refresh browser.
3. Open `지식 문서`.
4. Refresh browser.

Expected result:

- Current route remains stable after refresh if router is used.
- If hash or state-based routing is used, document the behavior.

Status:

```text
PASS / FAIL:
Notes:
```

---

### 6.3 Legacy admin route redirects

Steps:

1. As an Admin user, navigate directly to `/admin`.

Expected result:

- The app redirects to `/dashboard`.
- Dashboard content is visible after the redirect.

Status:

```text
PASS / FAIL:
Notes:
```

---

## 7. Build quality

### 7.1 TypeScript build

Command:

```bash
npm run build
```

Expected result:

- Build passes.
- No TypeScript errors.

Status:

```text
PASS / FAIL:
Notes:
```

---

### 7.2 Lint

Command:

```bash
npm run lint
```

Expected result:

- Lint passes, or existing unrelated lint failures are documented.

Status:

```text
PASS / FAIL:
Notes:
```

---

### 7.3 Unit tests

Command:

```bash
npm test
```

or:

```bash
npm run test
```

Expected result:

- Tests pass.
- If no tests exist, document that no test script exists.

Status:

```text
PASS / FAIL:
Notes:
```

---

## Suggested automated tests

If the project uses Vitest/Jest and React Testing Library, add tests for these units.

### Password visibility utility/component

Test cases:

- password hidden by default
- clicking toggle shows password
- clicking toggle again hides password
- input value persists

### Conversation title utility

Test cases:

```ts
createConversationTitle("") === "새 대화"
createConversationTitle("ELS 상품 설명해줘") === "ELS 상품 설명해줘"
createConversationTitle("아주 긴 금융 질문 문장입니다 이것은 잘려야 합니다") // max length + ...
```

### Korean initial consonant utility

Test cases:

```ts
getKoreanInitialConsonant("금리") === "ㄱ"
getKoreanInitialConsonant("나스닥") === "ㄴ"
getKoreanInitialConsonant("환율") === "ㅎ"
```

### Retrieval settings validation

Test cases:

- Top-K below 1 is rejected or clamped.
- Top-K above 50 is rejected or clamped.
- Valid Top-K is saved.
- Settings are loaded from localStorage.

---

## Final implementation report format

After completing the implementation, report in this format:

```md
## Summary
- ...

## Changed files
- ...

## Assumptions
- ...

## How to run
- ...

## Test results
- `npm run build`: PASS / FAIL
- `npm run lint`: PASS / FAIL / N/A
- `npm test`: PASS / FAIL / N/A

## Manual QA
- Login password toggle: PASS / FAIL
- Forgot password flow: PASS / FAIL
- Recent conversations: PASS / FAIL
- Recent conversations after logout: PASS / FAIL
- Dashboard layout: PASS / FAIL
- Knowledge documents: PASS / FAIL
- Admin settings: PASS / FAIL
```
