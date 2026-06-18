# RAG Chatbot Stage Metrics Redesign and Dashboard Throughput Fix

## Background

The RAG chatbot currently monitors the pipeline using these stages:

* `stage_0_intent_classification`
* `stage_1_retrieval_bm25`
* `stage_1_retrieval_dense`
* `stage_1_retrieval_fusion`
* `stage_2_generation`

The dashboard currently displays these values per stage:

* `total`
* `success`
* `fail`
* `avg elapsed`
* `throughput`

The current throughput calculation and unit handling are not clearly separated by stage type. Some metrics are therefore misleading.

Two problems must be fixed:

1. Retrieval and intent classification stages are call-based stages, but throughput may be calculated from mixed units such as chars, tokens, or generic `work_units`.
2. Generation throughput is currently char-based, but the primary generation performance metric should be token-based while still preserving `chars/sec` as a secondary metric.

---

# 1. Retrieval and Intent Classification Throughput

## Problem

Retrieval and intent classification stages appear to calculate throughput as:

```text
throughput = unit / elapsed_sec
```

This becomes misleading when `unit` is not clearly defined per stage.

For example, if dense retrieval fails but records `unit = 1`:

```text
elapsed_sec = 0.2197
throughput = 1 / 0.2197 = 4.5514 calls/sec
```

This can look like a successful retrieval rate even though the retrieval failed.

The dashboard also showed this abnormal value:

```text
stage_0_intent_classification

total: 2
success: 2
fail: 0
avg elapsed: 1.008s
throughput: RPS 259.84
```

If `total = 2` and `avg elapsed = 1.008s`, call-based throughput should be close to:

```text
1 / 1.008 = about 0.99 calls/sec
```

or, if using a wall-clock aggregate:

```text
total_calls / total_wall_time
```

`RPS 259.84` is invalid for call-based throughput. Likely causes include:

1. Intent classification throughput uses chars, tokens, prompt length, or another unit count instead of calls.
2. The stage metric `unit` or `work_units` field is used inconsistently across stages.
3. The dashboard misinterprets backend throughput fields.
4. Seconds and milliseconds are mixed.
5. Generation `chars/sec` or `tokens/sec` logic is incorrectly applied to intent classification.
6. Aggregation uses `unit_count` instead of `total_count` as the numerator.

## Direction

Treat these stages as call-based stages:

```text
stage_0_intent_classification
stage_1_retrieval_bm25
stage_1_retrieval_dense
stage_1_retrieval_fusion
```

Their throughput must be call-based, not char-based or token-based:

```text
attempted_calls_per_sec
successful_calls_per_sec
```

`stage_2_generation` is not call-based. It uses the provider-agnostic generation metric schema described later.

## Implementation Requirements

### 1. Stage Type and Metric Schema Mapping

Separate all stages by metric schema:

| stage | stage_type | schema |
| --- | --- | --- |
| stage_0_intent_classification | call_based | Call-based stage metric schema |
| stage_1_retrieval_bm25 | call_based | Call-based stage metric schema |
| stage_1_retrieval_dense | call_based | Call-based stage metric schema |
| stage_1_retrieval_fusion | call_based | Call-based stage metric schema |
| stage_2_generation | generation | Provider-agnostic generation metric schema |

### 2. Call-Based Stage Metric Schema

Apply the call-based metric schema to:

```text
stage_0_intent_classification
stage_1_retrieval_bm25
stage_1_retrieval_dense
stage_1_retrieval_fusion
```

Each call-based stage must include at least:

```json
{
  "stage": "stage_1_retrieval_dense",
  "stage_type": "call_based",
  "elapsed_sec": 0.2197,
  "attempted_count": 1,
  "success_count": 0,
  "fail_count": 1,
  "result_count": 0,
  "attempted_calls_per_sec": 4.5514,
  "successful_calls_per_sec": 0.0,
  "status": "error",
  "error_type": "collection_not_found",
  "error_message": "..."
}
```

`stage_2_generation` must not use this schema.

### 3. Retrieval Status Semantics

Retrieval stages must distinguish system failures from valid zero-result retrievals.

#### A. System Failure

Examples:

* Chroma collection not found
* embedding dimension mismatch
* DB connection error
* timeout
* exception

Expected metric:

```text
status = error
attempted_count = 1
success_count = 0
fail_count = 1
result_count = 0
successful_calls_per_sec = 0
```

For timeout failures:

```text
status = timeout
attempted_count = 1
success_count = 0
fail_count = 1
result_count = 0
successful_calls_per_sec = 0
```

#### B. Valid Retrieval With No Results

Examples:

* retrieval logic completed successfully
* `top_k` result list is empty
* no document passes the score threshold

Expected metric:

```text
status = zero_result
attempted_count = 1
success_count = 1
fail_count = 0
result_count = 0
successful_calls_per_sec = 1 / elapsed_sec
```

#### C. Valid Retrieval With Results

Expected metric:

```text
status = success
attempted_count = 1
success_count = 1
fail_count = 0
result_count = len(results)
successful_calls_per_sec = 1 / elapsed_sec
```

### 4. Dashboard Table for Call-Based Stages

The dashboard stage summary must use a table, not a single generic throughput card.

In the aggregated dashboard summary, `elapsed_sec` means stage-level `avg_elapsed_sec`.

Call-based stage summary target stages:

```text
stage_0_intent_classification
stage_1_retrieval_bm25
stage_1_retrieval_dense
```

Table schema:

| stage | elapsed_sec | attempted_rps | successful_rps | success_count | result_count | status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| stage_1_retrieval_dense | 0.2197 | 4.5514 | 0.0000 | 0 | 0 | error |

Display rules:

* `attempted_rps` displays `attempted_calls_per_sec`.
* `successful_rps` displays `successful_calls_per_sec`.
* A failed retrieval request displays `successful_rps = 0.0000`.
* `status` must use the canonical schema values: `success`, `zero_result`, `error`, `timeout`.
* `stage_0_intent_classification` is call-based and must never display chars/sec or tokens/sec as RPS.

### 5. Dashboard Table for Fusion Stage

`stage_1_retrieval_fusion` is a micro-stage with near-zero elapsed time, so RPS is usually not meaningful. In the dashboard, show only stage and elapsed time. Show all other throughput/count/status fields as `N/A`.

| stage | elapsed_sec | attempted_rps | successful_rps | success_count | result_count | status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| stage_1_retrieval_fusion | 0.0001 | N/A | N/A | N/A | N/A | N/A |

### 6. Deprecated Generic `throughput` Field

The existing generic `throughput` field can mix units across stage types. Do not remove it immediately if existing code or logs depend on it. Preserve backward compatibility where possible and prefer explicit fields in new code:

```text
attempted_calls_per_sec
successful_calls_per_sec
output_tokens_per_sec
chars_per_sec
```

The dashboard must not label every stage with only a generic `throughput` value. Labels must be stage-type specific.

---

# 2. Generation Token-Based Throughput

## Problem

`stage_2_generation` currently appears to calculate throughput from answer character count:

```text
chars = 183
elapsed_sec = 3.0411
throughput = 183 / 3.0411 = 60.1758 chars/sec
```

For Korean-language service UX, `chars/sec` is still useful as a secondary metric. However, model performance comparison, provider changes, and bottleneck analysis require token-based metrics.

The project can use these generation providers:

```text
OpenAI API
Ollama
```

The generation metric schema must therefore be provider-agnostic.

## Direction

Treat `stage_2_generation` as a generation stage and record:

```text
input_tokens
output_tokens
total_tokens
generation_elapsed_sec
output_tokens_per_sec
input_tokens_per_sec
chars
chars_per_sec
provider
model
token_count_source
raw_usage
```

Do not remove `chars/sec`. Make `output_tokens_per_sec` the primary generation throughput metric and `chars_per_sec` a secondary metric.

## Implementation Requirements

### 1. Provider-Agnostic Generation Metric Schema

`stage_2_generation` must use this schema:

```json
{
  "stage": "stage_2_generation",
  "stage_type": "generation",
  "provider": "openai",
  "model": "gpt-4.1-mini",
  "generation_elapsed_sec": 3.0411,
  "input_tokens": 850,
  "output_tokens": 92,
  "total_tokens": 942,
  "output_tokens_per_sec": 30.25,
  "input_tokens_per_sec": null,
  "chars": 183,
  "chars_per_sec": 60.1758,
  "status": "success",
  "token_count_source": "provider_usage",
  "raw_usage": {
    "prompt_tokens": 850,
    "completion_tokens": 92,
    "total_tokens": 942
  }
}
```

### 2. OpenAI Usage Mapping

For OpenAI API responses, map usage fields into the common schema:

```text
prompt_tokens -> input_tokens
completion_tokens -> output_tokens
total_tokens -> total_tokens
```

Example:

```json
{
  "provider": "openai",
  "input_tokens": 850,
  "output_tokens": 92,
  "total_tokens": 942,
  "token_count_source": "provider_usage",
  "raw_usage": {
    "prompt_tokens": 850,
    "completion_tokens": 92,
    "total_tokens": 942
  }
}
```

Requirements:

* Support both streaming and non-streaming generation paths.
* For streaming, check whether usage is available in the final chunk or through an explicit usage option.
* If provider usage is unavailable, use fallback logic.

### 3. Ollama Usage Mapping

For Ollama responses, map these fields into the common schema:

```text
prompt_eval_count -> input_tokens
eval_count -> output_tokens
prompt_eval_count + eval_count -> total_tokens
```

Ollama duration values are usually nanoseconds. Convert them to seconds:

```text
prompt_eval_duration_sec = prompt_eval_duration / 1e9
eval_duration_sec = eval_duration / 1e9
total_duration_sec = total_duration / 1e9
```

Calculation:

```text
input_tokens_per_sec = prompt_eval_count / prompt_eval_duration_sec
output_tokens_per_sec = eval_count / eval_duration_sec
```

Example:

```json
{
  "provider": "ollama",
  "model": "llama3.2:3b",
  "generation_elapsed_sec": 3.0411,
  "input_tokens": 850,
  "output_tokens": 92,
  "total_tokens": 942,
  "output_tokens_per_sec": 30.25,
  "input_tokens_per_sec": 120.5,
  "chars": 183,
  "chars_per_sec": 60.1758,
  "status": "success",
  "token_count_source": "provider_usage",
  "raw_usage": {
    "prompt_eval_count": 850,
    "eval_count": 92,
    "prompt_eval_duration": 7053941000,
    "eval_duration": 3041100000,
    "total_duration": 10195041000
  }
}
```

### 4. Token Usage Fallback

When provider usage is unavailable:

1. Use provider usage if available.
2. If provider usage is missing, use tokenizer-based estimates.
3. If tokenizer estimates are unavailable, keep token-related metrics as `null`.
4. Always record `chars`, `chars_per_sec`, and `generation_elapsed_sec`.

Fallback details:

* OpenAI may add the `tiktoken` dependency and use it when provider usage is unavailable.
* Ollama may use an approximate tokenizer estimate when provider usage is unavailable because exact model tokenizer matching is difficult.
* If estimates are used, set `token_count_source = tokenizer_estimate`.
* If token counts cannot be estimated, set `token_count_source = unavailable` and set token-related numeric fields to `null`.

Allowed `token_count_source` values:

```text
provider_usage
tokenizer_estimate
unavailable
```

Unavailable example:

```json
{
  "stage": "stage_2_generation",
  "stage_type": "generation",
  "provider": "unknown",
  "model": "unknown",
  "generation_elapsed_sec": 3.0411,
  "input_tokens": null,
  "output_tokens": null,
  "total_tokens": null,
  "output_tokens_per_sec": null,
  "input_tokens_per_sec": null,
  "chars": 183,
  "chars_per_sec": 60.1758,
  "status": "success",
  "token_count_source": "unavailable",
  "raw_usage": null
}
```

### 5. Dashboard Table for Generation Stage

Generation stage dashboard summary must use this table schema:

| stage | elapsed_sec | output_tps | chars_per_sec | rpm | output_tpm | total_tpm | input_tokens | output_tokens | total_tokens | token_count_source | status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| stage_2_generation | 3.0411 | 30.2522 | 60.1758 | 19.7290 | 1815.1320 | 18585.6900 | 850 | 92 | 942 | provider_usage | success |

Calculation and label rules:

* `output_tps = output_tokens / generation_elapsed_sec`
* `chars_per_sec = chars / generation_elapsed_sec`
* `rpm = 60 / generation_elapsed_sec`
* `output_tpm = output_tokens_per_sec * 60`
* `total_tpm = (total_tokens / generation_elapsed_sec) * 60`
* Dashboard labels must be explicit: `Output TPS`, `Chars/sec`, `RPM`, `Output TPM`, `Total TPM`.

---

# 3. Dashboard Throughput Outlier Investigation

## Observed Outlier

After running two queries, the dashboard showed:

```text
stage_0_intent_classification
total: 2
success: 2
fail: 0
avg elapsed: 1.008s
throughput: RPS 259.84
```

This is impossible for call-based throughput.

If `avg elapsed = 1.008s`, per-call RPS should be approximately:

```text
1 / 1.008 = 0.99 RPS
```

`RPS 259.84` likely means:

```text
unit_count / elapsed_sec
```

where `unit_count` is around 262:

```text
262 / 1.008 = about 260
```

This suggests intent classification may be using query chars, prompt chars, token count, or another length-based unit as the numerator.

## Investigation Targets

Inspect these areas first:

1. Stage metric recorder/logger code.
2. Code that calculates `unit`, `throughput`, and `elapsed_sec`.
3. Dashboard API response schema.
4. Frontend dashboard component that displays throughput.
5. Aggregation logic.
6. Code that determines metric type or unit type per stage.

Confirm:

```text
what numerator stage_0_intent_classification uses
why stage_0_intent_classification throughput is labeled RPS
whether unit means calls, chars, or tokens
whether elapsed_sec is truly seconds, not milliseconds
whether generation chars/sec logic is applied to intent classification
whether backend and frontend metric field names match
```

## Required Fix

### 1. Branch Throughput Calculation by Stage Type

Use explicit stage types:

```text
call_based:
  - stage_0_intent_classification
  - stage_1_retrieval_bm25
  - stage_1_retrieval_dense
  - stage_1_retrieval_fusion

generation:
  - stage_2_generation
```

Call-based stage:

```text
attempted_calls_per_sec = attempted_count / elapsed_sec
successful_calls_per_sec = success_count / elapsed_sec
```

For aggregated dashboard summary, `elapsed_sec` means average elapsed time. Summary RPS may be derived from the average elapsed time:

```text
attempted_rps = attempted_count_per_call / avg_elapsed_sec
successful_rps = success_count_per_call / avg_elapsed_sec
```

Generation stage:

```text
output_tokens_per_sec = output_tokens / generation_elapsed_sec
chars_per_sec = chars / generation_elapsed_sec
```

Important:

* Call-based stages must not use char count or token count as the numerator.
* Token/char throughput applies only to generation stages.

### 2. Dashboard Label Fix

Do not display one generic `throughput` label for every stage.

Use stage-type-specific table schemas:

#### Call-Based Stage

| stage | elapsed_sec | attempted_rps | successful_rps | success_count | result_count | status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| stage_0_intent_classification | 1.0080 | 0.9921 | 0.9921 | 2 | N/A | success |
| stage_1_retrieval_bm25 | 0.0500 | 20.0000 | 20.0000 | 1 | 5 | success |
| stage_1_retrieval_dense | 0.2197 | 4.5514 | 0.0000 | 0 | 0 | error |

#### Generation Stage

| stage | elapsed_sec | output_tps | chars_per_sec | rpm | output_tpm | total_tpm | input_tokens | output_tokens | total_tokens | token_count_source | status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| stage_2_generation | 3.0411 | 30.2522 | 60.1758 | 19.7290 | 1815.1320 | 18585.6900 | 850 | 92 | 942 | provider_usage | success |

#### Fusion Stage

| stage | elapsed_sec | attempted_rps | successful_rps | success_count | result_count | status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| stage_1_retrieval_fusion | 0.0001 | N/A | N/A | N/A | N/A | N/A |

---

# 4. Acceptance Criteria

All of the following must be satisfied.

## Metric Schema

* [ ] Call-based stages and generation stages are clearly separated.
* [ ] `stage_0_intent_classification` is not calculated as chars/sec or tokens/sec.
* [ ] Retrieval stages separate `attempted_calls_per_sec` and `successful_calls_per_sec`.
* [ ] Retrieval stages distinguish `success`, `zero_result`, `error`, and `timeout`.
* [ ] Generation stage records `output_tokens_per_sec` as the primary throughput metric.
* [ ] Generation stage preserves `chars_per_sec` as a secondary metric.
* [ ] OpenAI API and Ollama token usage are mapped into the common schema.
* [ ] Missing provider usage falls back to tokenizer estimates or `unavailable`.

## Dashboard

* [ ] Call-based stage throughput labels are `RPS` or `calls/sec`.
* [ ] Generation throughput labels are explicit: `Output TPS`, `Chars/sec`, `RPM`, `Output TPM`, `Total TPM`.
* [ ] `stage_0_intent_classification` never displays impossible values such as `RPS 259.84` when `avg elapsed = 1.008s` and `total = 2`.
* [ ] Fusion micro-stage RPS is hidden or displayed as `N/A`.
* [ ] Failed retrieval requests display successful throughput as `0`.
* [ ] Dashboard stage summary uses the table schemas defined in this document.

## Test Cases

### Case 1. Intent Classification, Two Successes

Input:

```text
total = 2
success = 2
fail = 0
avg_elapsed = 1.008s
```

Expected:

```text
successful_rps ~= 0.99
```

Forbidden:

```text
RPS 259.84
```

### Case 2. Dense Retrieval System Failure

Input:

```text
elapsed_sec = 0.2197
attempted_count = 1
success_count = 0
fail_count = 1
result_count = 0
status = error
```

Expected:

```text
attempted_calls_per_sec = 4.5514
successful_calls_per_sec = 0.0
```

### Case 3. Dense Retrieval Zero Result

Input:

```text
elapsed_sec = 0.2197
attempted_count = 1
success_count = 1
fail_count = 0
result_count = 0
status = zero_result
```

Expected:

```text
attempted_calls_per_sec = 4.5514
successful_calls_per_sec = 4.5514
zero_result_count = 1
```

`zero_result_count` does not need to be displayed on the dashboard, but the `status` column must display `zero_result`.

### Case 4. OpenAI Generation

Input:

```json
{
  "prompt_tokens": 850,
  "completion_tokens": 92,
  "total_tokens": 942
}
```

Expected:

```text
input_tokens = 850
output_tokens = 92
total_tokens = 942
token_count_source = provider_usage
```

### Case 5. Ollama Generation

Input:

```json
{
  "prompt_eval_count": 850,
  "eval_count": 92,
  "prompt_eval_duration": 7053941000,
  "eval_duration": 3041100000
}
```

Expected:

```text
input_tokens = 850
output_tokens = 92
total_tokens = 942
input_tokens_per_sec = 850 / 7.053941
output_tokens_per_sec = 92 / 3.0411
token_count_source = provider_usage
```

---

# 5. Suggested Implementation Order

Work in this order:

1. Inspect the current metric recorder, logger, dashboard aggregation, API response, and frontend dashboard code.
2. Add explicit `stage_type`.
3. Separate call-based and generation metric schemas.
4. Add retrieval status classification.
5. Add OpenAI and Ollama provider usage mapping.
6. Add token fallback handling.
7. Update dashboard table schemas and labels.
8. Hide or mark fusion stage throughput as `N/A`.
9. Add unit/API tests.
10. Run unit/API verification for the acceptance test cases.

Live query execution is not required unless the local environment is already configured. If live verification is skipped, document the reason.

---

# 6. Implementation Constraints

* Preserve backward compatibility for existing metric logs as much as possible.
* Do not immediately delete the existing `throughput` field. Deprecate it or make the dashboard prefer explicit fields.
* Use field names with explicit units to avoid mixing stage units.
* Do not group `RPS`, `TPS`, `TPM`, and `chars/sec` under one ambiguous `throughput` label.
* OpenAI and Ollama have different usage response structures. Convert provider-specific usage in a provider adapter layer or equivalent mapping function.
* Missing token usage must never break metric logging.
* OpenAI may add the `tiktoken` dependency for fallback token estimates.
* Ollama may use token estimates when provider usage is unavailable.
