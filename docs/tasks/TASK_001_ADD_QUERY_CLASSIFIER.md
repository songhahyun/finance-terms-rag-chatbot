# TASK 001: Add Query Intent Classifier

## 0. Context

- GitHub Issue: #8
- Goal: Add a query intent classification layer before answer generation.
- Primary route labels:
  - `simple`
  - `needs_rag`
  - `needs_web`
  - `clarify`
- The classifier must return routing metadata in API responses and monitoring logs.
- Web tool calling is planned but not implemented in this task. For now, `needs_web` is classified and returned as a label with a fallback response.

## 1. Final Routing Policy

The routing priority is:

1. If the query clearly needs current or real-time information, route to `needs_web`.
2. If the query contains a finance term from the dictionary, route to `needs_rag`.
3. If the query is a supported simple query, route to `simple`.
4. If the query is ambiguous, route to `clarify`.

Important exception:

- A finance term match does not always force `needs_rag`.
- If a query contains a finance term but asks for current prices, latest news, today/yesterday/tomorrow values, exchange rates, stock prices, or other real-time information, the final route should be `needs_web`.

Default clarification response:

```text
금융 용어 설명이 필요한지, 최신 시세/뉴스가 필요한지 조금 더 구체적으로 질문해주세요.
```

## 2. Classifier Architecture

Implement a hybrid classifier:

1. Rule-based classifier
2. Few-shot LLM classifier for grey-area queries
3. Final result merger returning:

```json
{
  "intent": "needs_rag",
  "confidence": 1.0,
  "reason": "matched_finance_terms"
}
```

API responses must include the following fields:

```json
{
  "intent": "needs_rag",
  "routing_reason": "matched_finance_terms",
  "matched_terms": ["가산금리"],
  "classifier": {
    "method": "rule",
    "confidence": 1.0
  }
}
```

## 3. Rule-Based Classifier Requirements

### 3.1 Finance Term Matching

Use this dictionary as the source of truth:

```text
data/processed/kiwi_user_dict.tsv
```

Requirements:

- Load the dictionary once at service/classifier initialization.
- Use normalized matching.
- Ignore spacing differences.
- Support Korean terms, English terms, abbreviations, and synonyms when present in the dictionary.
- Use Kiwi morphological analysis for query processing.
- Load the Kiwi tokenizer object only once and reuse it across requests.
- If a finance term is matched by Kiwi/dictionary rules, assign `confidence=1.0`.
- Track matched terms in `matched_terms`.

### 3.2 Current/Real-Time Information Rules

Detect `needs_web` before finalizing `needs_rag`.

Examples of signals:

- 오늘, 어제, 내일, 최근, 최신, 현재, 실시간
- 주가, 시세, 환율, 금리 현재값, 뉴스, 공시
- price, stock price, exchange rate, latest, recent, today, now, news

Examples:

- `기준금리 오늘 얼마야?` -> `needs_web`
- `삼성전자 주가 알려줘` -> `needs_web`
- `최근 환율 뉴스 알려줘` -> `needs_web`

Since web tool calling is not implemented yet, `needs_web` should return a fallback answer while preserving the `needs_web` route metadata.

### 3.3 Simple Rule-Based Answers

Some simple queries should return fixed rule-based answers without calling an LLM.

Examples:

- `안녕?`
- `너는 어떤 챗봇이야?`
- `너는 어떤 질문에 답할 수 있어?`
- `오늘 점심 메뉴 뭐야?`
- `오늘 서울 날씨가 어때?`
- `파이썬 리스트 컴프리헨션 알려줘`

Policy:

- Greeting and chatbot capability questions: return a fixed helpful answer.
- Unsupported non-finance questions: return a fixed unsupported-domain answer.
- Do not call an LLM for unsupported-domain simple answers.

## 4. LLM Classifier Requirements

Use the LLM classifier only for grey-area queries.

LLM classifier call condition:

- Rule-based `needs_rag` keyword matching fails, and
- the query is not already clearly routed by deterministic rules, and
- the query may still be one of:
  - `needs_web`
  - `simple`
  - `clarify`

The LLM classifier must:

- Use few-shot prompting.
- Return structured JSON with:
  - `intent`
  - `confidence`
  - `reason`
- Use enum-constrained labels:
  - `simple`
  - `needs_web`
  - `clarify`
- Use `temperature=0`.
- Use a small max token budget.
- Use a short timeout.

Model:

```env
INTENT_CLASSIFIER_PROVIDER=openai
INTENT_CLASSIFIER_MODEL=gpt-4.1-mini
INTENT_CLASSIFIER_TIMEOUT=10
INTENT_CLASSIFIER_CONFIDENCE_THRESHOLD=0.7
```

If LLM classifier confidence is below threshold, route to `clarify`.

LLM classifier failure policy:

```json
{
  "intent": "clarify",
  "confidence": 0.0,
  "reason": "llm_classifier_failed"
}
```

For clear OpenAI SDK/configuration errors, preserve the explicit error information according to current repo conventions. The repo currently does not define a dedicated OpenAI error dataclass.

## 5. Simple LLM Answer Policy

Use `gpt-4.1-mini` for supported simple LLM answers.

Examples:

- `인플레이션을 초등학생도 이해하게 설명해줘` -> `simple`, answer with LLM

Unsupported non-finance questions must not call the LLM.

Examples:

- `파이썬 리스트 컴프리헨션 알려줘` -> fixed unsupported-domain answer
- `오늘 점심 메뉴 뭐야?` -> fixed unsupported-domain answer
- `오늘 서울 날씨가 어때?` -> fixed unsupported-domain answer, not `needs_web`

## 6. Streaming Policy

Apply the classifier to both endpoints:

- `POST /api/chat`
- `POST /api/chat/stream`

For `/api/chat/stream`:

- Run classification before streaming answer events.
- `needs_rag`: use the existing RAG streaming behavior.
- `simple`: emit one token event for fixed or LLM-generated simple answer, then emit final payload.
- `clarify`: emit one token event with the clarification message, then emit final payload.
- `needs_web`: emit one fallback token event because web tool calling is not implemented yet, then emit final payload.

NDJSON event shape should remain compatible with the current implementation:

```json
{"type":"token","content":"..."}
```

```json
{"type":"final","question":"...","answer":"..."}
```

The final payload must include routing metadata.

## 7. Monitoring Requirements

Add classifier metadata to existing monitoring output.

Use stage name:

```text
stage_0_intent_classification
```

Record at minimum:

- `intent`
- `routing_reason`
- `matched_terms`
- `classifier_method`
- `confidence`

The metadata should be visible in:

- `logs/stage_monitor.log`
- `/api/monitor/recent`

## 8. Configuration Requirements

Add these settings to config and `.env.example`:

```env
INTENT_CLASSIFIER_PROVIDER=openai
INTENT_CLASSIFIER_MODEL=gpt-4.1-mini
INTENT_CLASSIFIER_TIMEOUT=10
INTENT_CLASSIFIER_CONFIDENCE_THRESHOLD=0.7
```

Do not modify the user's real `.env` file.

The user will add real environment variables manually.

## 9. Performance Requirements

Implement these performance safeguards:

- Kiwi tokenizer must be loaded once and reused.
- Finance dictionary must be loaded once and reused.
- Use cheap normalized string matching before expensive checks where possible.
- Call the LLM classifier only for grey-area queries.
- Keep the few-shot classifier prompt short.
- Use `temperature=0`.
- Keep classifier max tokens low.
- Use timeout.
- Add a small in-memory cache for repeated classification results if the implementation remains simple and safe.

## 10. Subtasks

### Task 001-0: Add Intent Classifier Domain Types

- Add intent enum/type definitions.
- Add classifier result schema/dataclass.
- Include:
  - `intent`
  - `confidence`
  - `reason`
  - `matched_terms`
  - `classifier_method`

Acceptance criteria:

- Types are importable without loading OpenAI or Kiwi.
- Unit tests cover basic result construction.

### Task 001-1: Add Dictionary Loader and Normalizer

- Load `data/processed/kiwi_user_dict.tsv`.
- Build normalized lookup structures.
- Ignore spacing differences.
- Preserve original matched terms for response metadata.

Acceptance criteria:

- Dictionary is loaded once per classifier/service instance.
- Tests cover Korean term, spacing-insensitive match, and abbreviation/synonym match if dictionary data supports it.

### Task 001-2: Add Kiwi-Based Rule Classifier

- Initialize Kiwi once.
- Analyze query with Kiwi.
- Implement finance term matching.
- Implement real-time/current-information rules.
- Implement deterministic simple and unsupported-domain rules.

Acceptance criteria:

- `가산금리란 무엇인가요?` -> `needs_rag`
- `기준금리 오늘 얼마야?` -> `needs_web`
- `안녕?` -> `simple`
- `파이썬 리스트 컴프리헨션 알려줘` -> `simple` with unsupported-domain fixed answer metadata

### Task 001-3: Add Few-Shot LLM Classifier

- Add OpenAI-backed classifier using `gpt-4.1-mini`.
- Use structured JSON output.
- Limit labels to:
  - `simple`
  - `needs_web`
  - `clarify`
- Apply confidence threshold.
- Implement failure fallback:
  - `intent=clarify`
  - `reason=llm_classifier_failed`

Acceptance criteria:

- LLM classifier is called only when rule-based matching does not resolve the query.
- JSON parse failure routes to `clarify`.
- Low confidence routes to `clarify`.

### Task 001-4: Add Final Classification Merger

- Combine rule-based and LLM classifier results.
- Enforce routing priority:
  1. `needs_web`
  2. `needs_rag`
  3. `simple`
  4. `clarify`
- Ensure finance term match can still become `needs_web` when real-time signals are present.

Acceptance criteria:

- `기준금리란 무엇인가요?` -> `needs_rag`
- `기준금리 오늘 얼마야?` -> `needs_web`
- ambiguous query -> `clarify`

### Task 001-5: Integrate Classifier into RAG Service

- Run classification before RAG retrieval/generation.
- Route:
  - `needs_rag` -> existing RAG pipeline
  - `simple` fixed answer -> no LLM call
  - `simple` LLM answer -> OpenAI `gpt-4.1-mini`
  - `needs_web` -> fallback answer for now
  - `clarify` -> clarification response

Acceptance criteria:

- Non-RAG routes do not perform vector retrieval.
- Existing RAG behavior is preserved for `needs_rag`.

### Task 001-6: Update API Schemas and Responses

- Add routing metadata to `/api/chat` response.
- Add routing metadata to `/api/chat/stream` final event.

Response fields:

- `intent`
- `routing_reason`
- `matched_terms`
- `classifier`

Acceptance criteria:

- `/api/chat` includes routing metadata.
- `/api/chat/stream` final event includes routing metadata.
- Existing client-compatible fields remain present:
  - `question`
  - `answer`
  - `retrieved_ids`
  - `sources`

### Task 001-7: Add Monitoring Stage

- Add `stage_0_intent_classification`.
- Write routing metadata to existing monitor trace/log path.

Acceptance criteria:

- `logs/stage_monitor.log` includes classifier stage metadata.
- `/api/monitor/recent` exposes classifier stage details.

### Task 001-8: Update Configuration and Examples

- Add settings to config.
- Add env vars to `.env.example`.
- Do not modify `.env`.
- Update backend API docs if response fields change.

Acceptance criteria:

- Missing classifier env vars use safe defaults.
- `.env.example` includes classifier settings.
- Documentation shows routing metadata in response examples.

### Task 001-9: Add Tests

Add focused tests for:

- term dictionary loading
- normalization
- Kiwi/rule classification
- needs_web priority over needs_rag
- deterministic simple fixed answers
- unsupported-domain fixed answers
- LLM classifier fallback behavior
- API response schema metadata
- streaming final payload metadata

Acceptance criteria:

- Targeted tests pass.
- Broader existing tests still pass if impacted modules are touched.

## 11. Out of Scope

- Implementing actual web search/tool-calling.
- Creating the final classifier evaluation testset. The user will provide the testset path later.
- Modifying real `.env` secrets.
- Changing frontend UI unless required by response contract changes in a later task.

## 12. Implementation Notes

- Prefer a small, isolated module for classification, for example:

```text
src/generation/query_intent.py
```

or:

```text
src/serving/query_intent.py
```

- Keep classifier code independent from FastAPI routers.
- Avoid request-time filesystem reads.
- Avoid request-time Kiwi initialization.
- Avoid LLM calls for deterministic routes.
- Keep response contract additive to avoid breaking existing clients.
