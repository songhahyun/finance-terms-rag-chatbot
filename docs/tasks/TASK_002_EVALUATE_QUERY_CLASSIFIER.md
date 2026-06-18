# TASK 002: Evaluate Query Intent Classifier

## 0. Context

- Goal: Improve and evaluate the query intent classifier added in Task 001.
- Primary file under test:
  - `src/generation/query_intent.py`
- Evaluation testset:
  - `data/eval/testset/classify_query_intent_v1.csv`
- Evaluation implementation location:
  - `src/evaluation/`
- Output directory:
  - `data/eval/outputs/query_intent/`

This task focuses on two related areas:

1. Improve finance-term matching inside the rule-based query intent classifier.
2. Add a repeatable rule-only evaluation CLI for query intent classification.

## 1. Problem Summary

The current classifier can produce noisy `matched_terms` because finance term matching uses normalized substring containment against `kiwi_user_dict.tsv`.

Example query:

```text
인플레이션과 스태그플레이션의 차이점은 무엇인가요?
```

Observed noisy matches:

```python
["레이션", "스태", "스태그플레이션", "이션", "인가", "인플", "인플레", "인플레이션", "차이"]
```

Expected matches:

```python
["인플레이션", "스태그플레이션"]
```

The root issue is not necessarily Kiwi itself. The issue is that the current dictionary and matching policy allow short fragments and common substrings to appear in `matched_terms`.

## 2. Agreed Short-Term Fix

For this task, do not split the dictionary into separate intent and tokenizer dictionaries.

Instead, implement a short-term classifier-side fix:

- Make substring matching stricter.
- Add longest-match filtering as post-processing.
- Do not add a hardcoded blacklist.
- Treat `인플레` as a valid alias when it appears alone.
- If `인플레` and `인플레이션` are both matched, keep the longest canonical match after filtering.

### 2.1 Substring Matching Policy

- Korean substring matches should require normalized term length of at least 3.
- English or alphanumeric abbreviations may still be matched even when short.
- This preserves valid abbreviations such as:
  - `ETF`
  - `CD`
  - `CP`
  - `RP`
  - `LTV`
  - `DTI`

### 2.2 Longest-Match Filtering

After combining substring matches and Kiwi token matches:

- If a shorter term is contained inside a longer matched term, remove the shorter term.
- Preserve stable output order as much as possible.

Example:

```python
["인플", "인플레", "인플레이션"] -> ["인플레이션"]
```

## 3. Matching Code Structure

Refactor finance-term matching in `src/generation/query_intent.py` so the responsibilities are clearer.

The current method:

```python
def _match_finance_terms(self, query: str) -> list[str]:
    ...
```

should be split into separate responsibilities:

1. Normalized substring matching
2. Kiwi token-based matching
3. Merge and longest-match filtering

Suggested structure:

```python
def _match_finance_terms_by_substring(self, query: str) -> list[str]:
    ...

def _match_finance_terms_by_tokens(self, query: str) -> list[str]:
    ...

def _merge_finance_term_matches(
    self,
    substring_matches: list[str],
    token_matches: list[str],
) -> list[str]:
    ...

def _match_finance_terms(self, query: str) -> list[str]:
    ...
```

Avoid adding a separate debug-only function. Evaluation code may use the structured matching methods if needed, but the production classifier should remain the source of truth.

## 4. Query Intent Evaluation Testset

Use:

```text
data/eval/testset/classify_query_intent_v1.csv
```

The testset columns are:

```text
id,query,expected_intent,acceptable_intents,category,expected_matched_terms,requires_realtime,expected_fixed_answer_key,notes
```

Column meanings:

- `id`: stable row identifier
- `query`: user query
- `expected_intent`: strict expected intent
- `acceptable_intents`: pipe-delimited accepted intents, such as `needs_rag|simple`
- `category`: evaluation category
- `expected_matched_terms`: JSON list of expected terms
- `requires_realtime`: whether the query requires current market/news data
- `expected_fixed_answer_key`: expected fixed answer constant name, if any
- `notes`: human-readable reason for the label

Categories currently include:

- `finance_concept`
- `realtime_market`
- `greeting`
- `capability`
- `unsupported_domain`
- `ambiguous`
- `lexical_trap`

## 5. Evaluation Metrics

Implement a rule-only evaluation CLI.

Do not use OpenAI or LLM fallback during evaluation.

### 5.1 Intent Metrics

Compute two intent scores:

1. Strict intent accuracy:

```text
predicted_intent == expected_intent
```

2. Acceptable intent accuracy:

```text
predicted_intent in acceptable_intents
```

Also compute category-level strict and acceptable accuracy.

### 5.2 Matched-Term Metrics

Compare `expected_matched_terms` with predicted `matched_terms`.

Use set-based comparison for exact match.

Recommended fields:

- `term_exact_ok`
- `term_precision`
- `term_recall`

Rules:

- If expected and predicted are both empty:
  - `term_exact_ok=true`
  - `term_precision=1.0`
  - `term_recall=1.0`
- If expected is empty but predicted is not empty:
  - `term_exact_ok=false`
  - `term_precision=0.0`
  - `term_recall=0.0`
- If expected is not empty but predicted is empty:
  - `term_exact_ok=false`
  - `term_precision=0.0`
  - `term_recall=0.0`
- Otherwise:
  - `term_precision = |expected ∩ predicted| / |predicted|`
  - `term_recall = |expected ∩ predicted| / |expected|`

## 6. Evaluation CLI

Create a CLI module under:

```text
src/evaluation/
```

Suggested command:

```powershell
python -m src.evaluation.evaluate_query_intent --testset data/eval/testset/classify_query_intent_v1.csv
```

Default behavior:

- Load `RuleBasedQueryClassifier`.
- Use `data/processed/kiwi_user_dict.tsv` as the dictionary path unless overridden.
- Do not instantiate or call `OpenAILLMIntentClassifier`.
- Evaluate all rows in the CSV.
- Save timestamped output files.

Suggested CLI options:

- `--testset`
- `--dictionary`
- `--output-dir`

Default output directory:

```text
data/eval/outputs/query_intent
```

## 7. Output Files

Use timestamped filenames.

Example timestamp format:

```text
260606_1625
```

Expected files:

```text
query_intent_eval_v1_260606_1625.csv
query_intent_eval_v1_260606_1625_errors.csv
query_intent_eval_v1_260606_1625_summary.json
```

The full CSV should include every test row with predictions and metrics.

The errors CSV should include only rows where at least one important check fails, such as:

- strict intent mismatch
- acceptable intent mismatch
- matched-term exact mismatch

The summary JSON should include:

- total row count
- strict intent accuracy
- acceptable intent accuracy
- term exact match rate
- average term precision
- average term recall
- category-level metrics
- confusion counts

## 8. Required Tests

Add or update tests in:

```text
tests/test_query_intent.py
```

Required edge cases:

1. Longest-match filtering:

```text
인플레이션과 스태그플레이션의 차이점은 무엇인가요?
```

Expected `matched_terms`:

```python
["스태그플레이션", "인플레이션"]
```

or equivalent set:

```python
{"스태그플레이션", "인플레이션"}
```

2. Unsupported programming query:

```text
파이썬 리스트 컴프리헨션 알려줘
```

Expected:

```text
simple
```

and no finance term false positive.

3. Conceptual market-word query:

```text
금리와 주가의 관계는?
```

Expected:

```text
needs_rag
```

not:

```text
needs_web
```

## 9. Subtasks

Implement this task as the following separate sub-tasks:

### Task 002-1: Improve Finance-Term Matching

- Update `src/generation/query_intent.py`.
- Make normalized substring matching stricter.
- Add longest-match filtering after combining substring and Kiwi token matches.
- Refactor matching code into substring matching, token matching, and merge/filter responsibilities.
- Do not add a hardcoded garbage-term blacklist.
- Preserve `인플레` as a valid alias when it appears alone.

### Task 002-2: Add Query Intent Evaluation CLI

- Add evaluation code under `src/evaluation/`.
- Implement a rule-only CLI for `data/eval/testset/classify_query_intent_v1.csv`.
- Compute strict intent accuracy, acceptable intent accuracy, matched-term exact match, matched-term precision, and matched-term recall.
- Save timestamped full results, error-only results, and summary JSON files under `data/eval/outputs/query_intent/`.
- Do not use OpenAI or any LLM fallback during evaluation.

### Task 002-3: Add Tests and Run Validation

- Add focused tests in `tests/test_query_intent.py`.
- Cover longest-match filtering, unsupported programming queries, and conceptual market-word queries.
- Run the relevant targeted tests.
- Run the new evaluation CLI once against `classify_query_intent_v1.csv` if the local environment has the required dependencies.

## 10. Non-Goals

- Do not add web lookup.
- Do not use LLM fallback in evaluation.
- Do not add a hardcoded garbage-term blacklist.
- Do not split the physical dictionary into multiple files in this task.
- Do not change public API response schemas unless required by the classifier changes.

## 11. Notes

The current testset was created to cover both normal cases and edge cases:

- strict finance concept routing
- real-time market routing
- greetings
- capability questions
- unsupported-domain questions
- ambiguous questions
- lexical traps caused by substring matching

The main success criterion is that `matched_terms` becomes useful for routing metadata and debugging, not just that the intent label is correct.
