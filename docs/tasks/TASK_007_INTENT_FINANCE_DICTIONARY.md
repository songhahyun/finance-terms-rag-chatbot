# TASK 007: Add Dedicated Finance Intent Dictionary

## 0. Context

- Goal: Split query intent routing terms from the Kiwi tokenizer user dictionary.
- Primary production files:
  - `src/query_intent/dictionary.py`
  - `src/query_intent/rule_classifier.py`
  - `src/serving/rag_service.py`
- Primary evaluation file:
  - `src/evaluation/evaluate_query_intent.py`
- Primary tests:
  - `tests/test_query_intent.py`
  - `tests/test_rag_service_query_intent.py`
- Current tokenizer dictionary:
  - `data/processed/kiwi_user_dict.tsv`
- New intent dictionary:
  - `data/processed/finance_intent_terms.json`
- Source-of-truth raw document:
  - `data/raw/2020_경제금융용어 700선.pdf`

The query intent classifier currently uses `kiwi_user_dict.tsv` for two separate purposes:

1. Loading a Kiwi user dictionary for tokenization.
2. Deciding whether a user query contains a finance term that should route to RAG.

Those are different responsibilities. The Kiwi dictionary may contain terms that help tokenization but should not trigger `needs_rag` routing. The intent classifier needs a stricter finance-term allowlist that only contains terms supported by the current RAG knowledge base.

## 1. Problem Summary

The query intent evaluation report at:

```text
reports/260606_query_intent_classification_exp_001.md
```

identified false-positive RAG routing caused by using the tokenizer dictionary as the intent routing dictionary.

Examples of bad matches:

- `그거 차이가 뭐야?` matched `차이` and routed to `needs_rag`.
- `이 용어가 무슨 뜻이야?` matched `용어` and routed to `needs_rag`.
- `이 챗봇은 금융 용어만 설명해?` matched `금융`, `용어`, `설명` and routed to `needs_rag`.
- `공시라는 단어의 일반적인 뜻 알려줘` matched `공시`, `일반` and routed to `needs_rag`.

The classifier should not treat generic words such as `차이`, `용어`, `설명`, `일반`, `효과`, or `금융` as standalone RAG triggers.

## 2. Final Decisions

### 2.1 Dictionary Source

Use only:

```text
data/raw/2020_경제금융용어 700선.pdf
```

Do not use:

```text
data/raw/2026_경제금융용어 800선.pdf
```

Reason:

- The current vector DB and processed RAG documents contain the 700-term knowledge base.
- If the intent dictionary contains 2026-only terms, the classifier may route to `needs_rag` for terms that retrieval cannot answer reliably.
- The intent dictionary must stay aligned with the actual indexed knowledge base.

When possible, cross-check the generated dictionary against:

```text
data/processed/final_chunk.json
```

The final intent dictionary should not contain canonical terms that are absent from the current processed RAG corpus.

### 2.2 File Format

Use JSON for the source-managed intent dictionary:

```text
data/processed/finance_intent_terms.json
```

Rationale:

- JSON handles aliases and future metadata more clearly than TSV.
- Runtime search speed should not depend on the file format.
- The classifier must load the JSON once at startup and convert it into in-memory lookup structures.
- Do not read the JSON file on every user query.

Recommended JSON shape:

```json
[
  {
    "term": "가산금리",
    "aliases": ["가산 금리"]
  },
  {
    "term": "ETF",
    "aliases": ["상장지수펀드", "상장 지수 펀드"]
  }
]
```

At load time, flatten this into an alias lookup map similar to:

```python
{
    "가산금리": "가산금리",
    "상장지수펀드": "ETF",
    "상장 지수 펀드": "ETF",
}
```

The actual keys should use the existing `normalize_term()` behavior so spacing, separators, and casing are handled consistently.

### 2.3 No `trigger_strength` in the Initial Implementation

Do not add `trigger_strength`, `weak`, or equivalent routing-strength metadata in this task.

Reason:

- The first version should be a strict allowlist.
- Terms or aliases that should not route to RAG by themselves should be excluded from the intent dictionary.
- This keeps behavior easier to reason about and avoids adding policy branches before the dictionary quality has been evaluated.

Examples of terms or aliases that should generally be excluded as standalone aliases:

- `차이`
- `용어`
- `설명`
- `일반`
- `효과`
- `금융`

Ambiguous finance-looking words such as `공시`, `환율`, `금리`, and `주가` need careful handling. Include them only if they are canonical terms present in the 700-term corpus or high-confidence aliases. Do not add broad aliases that cause lexical traps.

## 3. Runtime Matching Policy

The runtime search structure should prioritize fast in-memory lookup.

Recommended load-time structures:

```python
canonical_terms: tuple[str, ...]
normalized_alias_to_terms: dict[str, tuple[str, ...]]
normalized_to_terms: dict[str, tuple[str, ...]]
```

Notes:

- `term` itself must be searchable even if it is not repeated in `aliases`.
- `aliases` should map back to the canonical `term`.
- Return canonical terms in `QueryIntentResult.matched_terms`.
- Keep stable deterministic ordering.
- Preserve longest-match filtering after substring and token matches are merged.

The classifier may continue to use both:

1. Normalized substring matching.
2. Kiwi token-form matching.

But the dictionary used for matching must be the new intent dictionary, not `kiwi_user_dict.tsv`.

## 4. Required Code Changes

### 4.1 Dictionary Loader

Update:

```text
src/query_intent/dictionary.py
```

Requirements:

- Support loading the new JSON format.
- Preserve existing TSV loading behavior if needed by tests or compatibility paths.
- Convert each canonical `term` and its `aliases` into normalized lookup entries.
- Return canonical terms from both substring and token match paths.
- Deduplicate duplicate aliases and duplicate canonical terms deterministically.
- Validate malformed JSON records with clear exceptions.

Suggested compatibility policy:

- `FinanceTermDictionary.load(path)` may dispatch by suffix:
  - `.json`: load intent dictionary JSON.
  - otherwise: load legacy TSV first-column terms.

### 4.2 Rule Classifier Constructor

Update:

```text
src/query_intent/rule_classifier.py
```

Current behavior:

```python
RuleBasedQueryClassifier(dictionary_path)
```

New behavior should allow separate paths:

```python
RuleBasedQueryClassifier(
    intent_dictionary_path,
    kiwi_dictionary_path=None,
)
```

Requirements:

- Load `FinanceTermDictionary` from `intent_dictionary_path`.
- Build Kiwi with `kiwi_dictionary_path` when provided.
- Keep backward compatibility where practical:
  - Existing `RuleBasedQueryClassifier(path)` should still work and use the same path for both intent matching and Kiwi loading.
- The production service should pass separate paths.

### 4.3 RAG Service Integration

Update:

```text
src/serving/rag_service.py
```

Current behavior:

```python
dictionary_path = self._settings.processed_data_dir / "kiwi_user_dict.tsv"
rule_classifier = RuleBasedQueryClassifier(dictionary_path)
```

Required behavior:

```python
intent_dictionary_path = self._settings.processed_data_dir / "finance_intent_terms.json"
kiwi_dictionary_path = self._settings.processed_data_dir / "kiwi_user_dict.tsv"
rule_classifier = RuleBasedQueryClassifier(
    intent_dictionary_path=intent_dictionary_path,
    kiwi_dictionary_path=kiwi_dictionary_path,
)
```

If the repository has settings patterns for configurable data paths, add a setting for the intent dictionary path. Otherwise, keep the path convention under `processed_data_dir`.

### 4.4 Evaluation CLI

Update:

```text
src/evaluation/evaluate_query_intent.py
```

Requirements:

- Default dictionary path should use `data/processed/finance_intent_terms.json`.
- Add separate CLI options if the classifier requires both paths:
  - `--intent-dictionary`
  - `--kiwi-dictionary`
- Keep old `--dictionary` behavior only if it is still needed for compatibility.
- Evaluation outputs should continue to use canonical `matched_terms`.

### 4.5 Notebook Reference

Update references in:

```text
notebooks/06_query_intent_classification.ipynb
```

At minimum, make the notebook use:

```text
data/processed/finance_intent_terms.json
```

for intent matching and keep `kiwi_user_dict.tsv` only as the tokenizer dictionary.

## 5. Dictionary Generation Requirements

Create the initial JSON dictionary from the current 700-term knowledge base.

Preferred source order:

1. Extract or derive canonical terms from `data/processed/final_chunk.json` if it contains the actual indexed 700 terms.
2. Cross-check with `data/raw/2020_경제금융용어 700선.pdf`.
3. Do not include terms that only appear in `data/raw/2026_경제금융용어 800선.pdf`.

Initial alias policy:

- Include the canonical term itself implicitly.
- Add only high-confidence aliases.
- Include spacing variants when they are clearly equivalent.
- Include common abbreviations only when unambiguous.
- Avoid broad generic aliases that could match non-finance or meta-chat queries.

The initial implementation may start with canonical terms only if alias generation would be risky. It is better to ship a precise dictionary with fewer aliases than a broad dictionary that causes RAG over-routing.

## 6. Required Tests

Update or add tests in:

```text
tests/test_query_intent.py
```

Required coverage:

- JSON intent dictionary loads canonical terms.
- JSON intent dictionary maps aliases back to canonical terms.
- Duplicate terms and aliases are deduplicated deterministically.
- `RuleBasedQueryClassifier(intent_dictionary_path, kiwi_dictionary_path)` uses the intent dictionary for RAG routing.
- Kiwi dictionary terms that are absent from the intent dictionary do not trigger `needs_rag`.
- `차이`, `용어`, `설명`, `일반`, `효과`, and `금융` do not route to `needs_rag` when they are absent from the intent dictionary.
- Existing TSV compatibility still works if backward compatibility is retained.
- Current-info routing still works with canonical matched terms where applicable.
- Longest-match filtering still returns canonical terms.

Add or update service tests in:

```text
tests/test_rag_service_query_intent.py
```

Required coverage:

- `RAGService` builds the rule classifier with separate intent and Kiwi dictionary paths, or an equivalent settings-backed path.
- `matched_terms` in the response remain canonical terms.

## 7. Evaluation Requirements

Run the query intent evaluation after implementation.

Recommended command shape:

```bash
python -m src.evaluation.evaluate_query_intent \
  --testset data/eval/testset/classify_query_intent_v1.csv \
  --intent-dictionary data/processed/finance_intent_terms.json \
  --kiwi-dictionary data/processed/kiwi_user_dict.tsv \
  --output-dir data/eval/outputs/query_intent/query_intent_007_intent_dictionary
```

If the CLI keeps a single dictionary option for compatibility, document the final command in the implementation report.

Expected directional improvement:

- Lower false-positive `needs_rag` routing for ambiguous and capability queries.
- Better `matched_terms` exactness for canonical finance terms.
- No regression for clear finance concept queries such as `가산금리란 무엇인가요?`.
- No regression for clear current-info queries such as `삼성전자 주가 지금 얼마야?`.

## 8. Subtasks

### Task 007-1: Add Intent Dictionary JSON

Create:

```text
data/processed/finance_intent_terms.json
```

Acceptance criteria:

- The file is valid UTF-8 JSON.
- Each record has a non-empty `term`.
- `aliases` is optional or a list of strings.
- Canonical terms align with the 700-term corpus currently indexed for RAG.
- 2026-only terms are not included.

### Task 007-2: Extend `FinanceTermDictionary`

Acceptance criteria:

- JSON and TSV loading both work if compatibility is retained.
- Alias matches return canonical terms.
- Duplicate aliases do not produce duplicate `matched_terms`.
- Invalid JSON records fail with actionable errors.

### Task 007-3: Split Intent and Kiwi Dictionary Paths

Acceptance criteria:

- `RuleBasedQueryClassifier` accepts separate intent and Kiwi dictionary paths.
- Production service uses `finance_intent_terms.json` for intent matching.
- Production service uses `kiwi_user_dict.tsv` only for Kiwi tokenization.
- Existing imports through `src.generation.query_intent` remain valid.

### Task 007-4: Update Evaluation and Notebook References

Acceptance criteria:

- Evaluation CLI defaults to the new intent dictionary.
- CLI supports both intent and Kiwi dictionary paths when needed.
- Notebook references no longer use `kiwi_user_dict.tsv` as the intent dictionary.

### Task 007-5: Add Tests and Run Validation

Acceptance criteria:

- Relevant unit tests pass.
- Query intent evaluation runs successfully.
- The implementation report includes the test command and evaluation output paths.

## 9. Non-Goals

- Do not add `trigger_strength`, weak-term routing, or a complex policy engine in this task.
- Do not ingest or index `data/raw/2026_경제금융용어 800선.pdf`.
- Do not rebuild the vector DB unless separately required by another task.
- Do not change API response schemas unless absolutely necessary.
- Do not change frontend behavior.
- Do not rely on LLM fallback to fix deterministic dictionary overmatching.

## 10. Acceptance Criteria

- The intent classifier no longer uses `kiwi_user_dict.tsv` as its RAG routing allowlist in production.
- The new intent dictionary is JSON and is loaded once into memory.
- Runtime query matching uses in-memory structures, not per-query file reads.
- `matched_terms` are canonical terms from the 700-term knowledge base.
- Generic tokenizer terms absent from the intent dictionary do not trigger `needs_rag`.
- Existing clear finance concept and current-info routing behavior is preserved.
- Tests cover dictionary loading, alias mapping, separated dictionary paths, and representative false-positive cases.
- Query intent evaluation can be rerun with the new dictionary path.

## 11. Reporting Requirements

When implementation is complete, report:

1. Files changed.
2. Dictionary source used and how it was generated.
3. Count of canonical terms and alias entries in `finance_intent_terms.json`.
4. Any excluded or ambiguous terms worth noting.
5. Test commands run and results.
6. Evaluation command run and output paths.
7. Any remaining false positives or follow-up recommendations.
