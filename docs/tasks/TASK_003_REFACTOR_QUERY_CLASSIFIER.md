# TASK 003: Refactor Query Intent Classifier

## 0. Context

- Goal: Refactor the query intent classifier implementation into smaller modules without changing runtime behavior.
- Current primary file:
  - `src/generation/query_intent.py`
- New implementation package:
  - `src/generation/intent/`
- Compatibility facade:
  - `src/generation/query_intent.py`
- Primary tests:
  - `tests/test_query_intent.py`
  - `tests/test_rag_service_query_intent.py`
  - `tests/test_query_intent_config.py`
- Related evaluation CLI:
  - `src/evaluation/evaluate_query_intent.py`

The current `src/generation/query_intent.py` has grown beyond 500 lines and contains several separate responsibilities in one module:

1. Public result types and enums
2. Fixed answer constants and rule patterns
3. Term normalization helpers
4. Finance term dictionary loading and matching
5. Rule-based query classifier
6. Optional OpenAI LLM classifier
7. Hybrid query intent classifier facade and cache

This task is a structure-only refactor. It must not change classifier behavior, routing behavior, public API schemas, or evaluation semantics.

## 1. Problem Summary

`src/generation/query_intent.py` is difficult to maintain because independent classifier responsibilities are co-located in one large file.

This makes future work harder, especially:

- creating a strict intent-only finance dictionary in a later task
- improving the `matched_terms -> needs_rag` routing policy in a later task
- evaluating LLM-based classification in a later task
- testing rule matching, dictionary loading, and facade behavior independently

Task 003 should prepare the codebase for those future changes without implementing those behavior changes now.

## 2. Refactor Scope

Move query intent implementation details into:

```text
src/generation/intent/
  __init__.py
  types.py
  constants.py
  normalization.py
  dictionary.py
  rule_classifier.py
  llm_classifier.py
  classifier.py
```

Keep this existing module as a compatibility facade:

```text
src/generation/query_intent.py
```

Existing imports must continue to work:

```python
from src.generation.query_intent import RuleBasedQueryClassifier
from src.generation.query_intent import QueryIntentClassifier
from src.generation.query_intent import QueryIntentResult
```

The compatibility facade should re-export the public names currently imported by production code and tests.

## 3. Proposed Module Responsibilities

### 3.1 `types.py`

Move public result types:

- `QueryIntent`
- `ClassifierMethod`
- `QueryIntentResult`

### 3.2 `constants.py`

Move fixed answers and rule pattern constants:

- `DEFAULT_CLARIFICATION_ANSWER`
- `NEEDS_WEB_FALLBACK_ANSWER`
- `GREETING_ANSWER`
- `CAPABILITY_ANSWER`
- `UNSUPPORTED_DOMAIN_ANSWER`
- `_CURRENT_INFO_PATTERNS`
- `_MARKET_INFO_PATTERNS`
- `_CONCEPTUAL_QUERY_PATTERNS`
- `_GREETING_PATTERNS`
- `_CAPABILITY_PATTERNS`
- `_UNSUPPORTED_PATTERNS`
- `_LLM_ALLOWED_INTENTS`

Keep constants importable through the compatibility facade if existing code or tests import them.

### 3.3 `normalization.py`

Move normalization helpers:

- `normalize_term`
- `_allows_short_substring_match`
- regex constants used by normalization

### 3.4 `dictionary.py`

Move finance dictionary structures and lookup:

- `FinanceTermDictionary`

This module may import normalization helpers, but it must not import classifiers.

### 3.5 `rule_classifier.py`

Move deterministic rule classifier:

- `RuleBasedQueryClassifier`

This module may import:

- types
- constants
- normalization helpers
- `FinanceTermDictionary`

### 3.6 `llm_classifier.py`

Move OpenAI fallback classifier:

- `OpenAILLMIntentClassifier`

This module may import:

- types
- constants

It must preserve the current lazy import behavior for the OpenAI SDK.

### 3.7 `classifier.py`

Move the facade/cache classifier:

- `QueryIntentClassifier`

This module may import:

- `QueryIntent`
- `QueryIntentResult`
- `RuleBasedQueryClassifier`
- `OpenAILLMIntentClassifier`

### 3.8 `intent/__init__.py`

Re-export the same public names as the compatibility facade where practical, so both of these can work:

```python
from src.generation.intent import RuleBasedQueryClassifier
from src.generation.query_intent import RuleBasedQueryClassifier
```

## 4. Public API Compatibility

The following imports must remain valid after the refactor:

```python
from src.generation.query_intent import (
    CAPABILITY_ANSWER,
    DEFAULT_CLARIFICATION_ANSWER,
    GREETING_ANSWER,
    NEEDS_WEB_FALLBACK_ANSWER,
    UNSUPPORTED_DOMAIN_ANSWER,
    ClassifierMethod,
    FinanceTermDictionary,
    OpenAILLMIntentClassifier,
    QueryIntent,
    QueryIntentClassifier,
    QueryIntentResult,
    RuleBasedQueryClassifier,
    normalize_term,
)
```

Do not require downstream modules to change import paths in this task unless the change is purely internal and all tests still pass.

## 5. Behavior Preservation Requirements

This task must preserve:

- all current intent labels for the same query and dictionary inputs
- all current `matched_terms` outputs
- all fixed answer text
- all classifier method values
- all routing metadata fields and values
- all LLM fallback parsing behavior
- all cache behavior in `QueryIntentClassifier`
- all existing public API response schemas

Do not change:

- `matched_terms -> needs_rag` routing policy
- current-info detection policy
- simple/capability/unsupported routing policy
- finance-term matching policy
- dictionary loading policy
- OpenAI prompt content
- evaluation metrics

## 6. Required Tests

Run targeted tests after the refactor:

```powershell
python -m pytest tests/test_query_intent.py tests/test_rag_service_query_intent.py tests/test_query_intent_config.py
```

If targeted tests pass, also run the broader relevant tests if practical:

```powershell
python -m pytest tests
```

Add a small import compatibility test if existing tests do not already cover the compatibility facade sufficiently.

Suggested assertions:

```python
from src.generation.query_intent import RuleBasedQueryClassifier
from src.generation.intent import RuleBasedQueryClassifier as PackageRuleBasedQueryClassifier

assert RuleBasedQueryClassifier is PackageRuleBasedQueryClassifier
```

## 7. Implementation Guidance

Recommended sequence:

1. Create `src/generation/intent/`.
2. Move public types into `types.py`.
3. Move constants into `constants.py`.
4. Move normalization helpers into `normalization.py`.
5. Move `FinanceTermDictionary` into `dictionary.py`.
6. Move `RuleBasedQueryClassifier` into `rule_classifier.py`.
7. Move `OpenAILLMIntentClassifier` into `llm_classifier.py`.
8. Move `QueryIntentClassifier` into `classifier.py`.
9. Update `src/generation/intent/__init__.py` to re-export public names.
10. Replace `src/generation/query_intent.py` with a compatibility re-export facade.
11. Run targeted tests.
12. Add import compatibility tests if needed.

Avoid opportunistic cleanup or behavior changes while moving code.

## 8. Subtasks

Implement this task as the following separate sub-tasks:

### Task 003-1: Create Intent Package and Move Shared Types

- Create `src/generation/intent/`.
- Add `src/generation/intent/__init__.py`.
- Move public result types into `types.py`:
  - `QueryIntent`
  - `ClassifierMethod`
  - `QueryIntentResult`
- Move fixed answers and rule pattern constants into `constants.py`.
- Move normalization helpers into `normalization.py`.
- Preserve imports through `src/generation/query_intent.py`.
- Run the relevant targeted tests after this sub-task.

### Task 003-2: Move Dictionary and Rule-Based Classifier

- Move `FinanceTermDictionary` into `dictionary.py`.
- Move `RuleBasedQueryClassifier` into `rule_classifier.py`.
- Keep the existing matching and routing behavior unchanged.
- Keep Kiwi dictionary loading behavior unchanged.
- Preserve `from src.generation.query_intent import FinanceTermDictionary`.
- Preserve `from src.generation.query_intent import RuleBasedQueryClassifier`.
- Run the relevant targeted tests after this sub-task.

### Task 003-3: Move LLM and Facade Classifiers

- Move `OpenAILLMIntentClassifier` into `llm_classifier.py`.
- Move `QueryIntentClassifier` into `classifier.py`.
- Preserve lazy OpenAI SDK import behavior.
- Preserve cache behavior in `QueryIntentClassifier`.
- Preserve all public imports through both:
  - `src.generation.intent`
  - `src.generation.query_intent`
- Run the relevant targeted tests after this sub-task.

### Task 003-4: Add Compatibility Tests and Final Validation

- Add or update tests for import compatibility if existing tests are insufficient.
- Verify that compatibility facade imports and package imports refer to the same classes/functions.
- Run:

```powershell
python -m pytest tests/test_query_intent.py tests/test_rag_service_query_intent.py tests/test_query_intent_config.py
```

- If practical, run:

```powershell
python -m pytest tests
```

- Confirm there are no behavior changes in classifier outputs.

## 9. Non-Goals

- Do not change classifier behavior.
- Do not change routing behavior.
- Do not change the `matched_terms -> needs_rag` policy in this task.
- Do not create a strict intent-only finance dictionary in this task.
- Do not split `data/processed/kiwi_user_dict.tsv` in this task.
- Do not add LLM evaluation in this task.
- Do not change the query intent evaluation CLI.
- Do not change public API response schemas.
- Do not change frontend behavior.

## 10. Follow-Up Tasks

Task 004 should address the routing quality issue separately.

Expected Task 004 scope:

- create or derive a strict intent classification finance-term dictionary
- prevent broad Kiwi tokenizer terms such as `차이`, `설명`, `용어`, `위험`, `효과`, `관계`, or `일반` from forcing `needs_rag`
- reconsider the `matched_terms -> needs_rag` policy
- compare baseline query intent evaluation before and after the routing change

Task 005 may evaluate LLM-based or hybrid query intent classification separately.

Expected Task 005 scope:

- compare `rule_only`, `llm_only`, and `hybrid_rule_then_llm`
- measure strict and acceptable accuracy
- measure category-level metrics
- compare confusion matrices
- track latency and cost
- avoid changing production routing until evaluation results justify it

## 11. Reporting Requirements

After completing this task, report:

1. Files created or changed
2. Public imports preserved
3. Tests run
4. Test results
5. Any behavior changes detected, if any
6. Any follow-up concerns for Task 004 or Task 005
