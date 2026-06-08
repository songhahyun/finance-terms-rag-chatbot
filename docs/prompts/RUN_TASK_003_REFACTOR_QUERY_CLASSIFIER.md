Follow the instructions in

1. docs/TASK_RULES.md
2. docs/tasks/TASK_003_REFACTOR_QUERY_CLASSIFIER.md

Process Task 003-1 through Task 003-4 sequentially.

Before each sub-task:
- Re-read the relevant section in docs/tasks/TASK_003_REFACTOR_QUERY_CLASSIFIER.md.
- Summarize the sub-task scope briefly.
- Do not proceed if requirements conflict with existing code.

Implementation constraints:
- Do not change classifier behavior.
- Do not change routing behavior.
- Do not change the `matched_terms -> needs_rag` policy.
- Do not create or split a strict intent-only finance dictionary.
- Do not add LLM evaluation.
- Do not change public API response schemas.
- Preserve existing imports through `src/generation/query_intent.py`.

After each sub-task:
- Run the most relevant targeted tests.
- Report changed files and test results.
- Commit only the changes related to that sub-task if tests pass.
