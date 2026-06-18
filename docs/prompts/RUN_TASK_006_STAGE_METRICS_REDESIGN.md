Follow the instructions in

1. docs/TASK_RULES.md
2. docs/tasks/TASK_006_STAGE_METRICS_REDESIGN.md

Process Task 006 sequentially according to the implementation order in the task document.

Before each implementation step:
- Re-read the relevant section in docs/tasks/TASK_006_STAGE_METRICS_REDESIGN.md.
- Summarize the step scope briefly.
- Inspect the existing recorder, logger, dashboard aggregation, API response, and frontend dashboard code before editing.
- Do not proceed if requirements conflict with existing code or existing public API behavior.

Implementation constraints:
- Preserve backward compatibility for existing monitor logs and legacy `throughput` fields where possible.
- Do not use chars, prompt length, token count, or `work_units` as the numerator for call-based RPS.
- Keep `stage_0_intent_classification`, `stage_1_retrieval_bm25`, `stage_1_retrieval_dense`, and `stage_1_retrieval_fusion` as `call_based` stages.
- Keep `stage_2_generation` as a `generation` stage using the provider-agnostic generation metric schema.
- Use status values from the task document: `success`, `zero_result`, `error`, and `timeout`.
- Distinguish retrieval system failures from valid zero-result retrievals.
- Preserve `chars_per_sec` for generation, but make `output_tokens_per_sec` the primary generation throughput metric.
- Map OpenAI and Ollama usage into the common generation schema.
- If provider usage is unavailable, use tokenizer estimates where supported; OpenAI may add `tiktoken`, and Ollama may use an estimate.
- Ensure metric logging never fails only because token usage is missing.
- Display dashboard stage summaries as the table schemas defined in the task document.
- For `stage_1_retrieval_fusion`, display only `stage` and `elapsed_sec`; show other table fields as `N/A`.
- Show both `Output TPM` and `Total TPM` for generation dashboard metrics.
- Keep frontend UI consistent with the existing dashboard styling and navigation.

After each implementation step:
- Run the most relevant targeted unit or API tests.
- Report changed files and test results.
- Commit only the changes related to that step if tests pass.

Final verification:
- Run unit/API tests covering the acceptance test cases in docs/tasks/TASK_006_STAGE_METRICS_REDESIGN.md.
- Do not require live query execution or external provider calls unless the local environment is already configured.
- Document any skipped live verification and the reason.
