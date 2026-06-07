Follow the instructions in

1. docs/TASK_RULES.md
2. docs/tasks/TASK_002_EVALUATE_QUERY_CLASSIFIER.md

Process Task 002-1 through Task 002-3 sequentially.

Before each sub-task:
- Re-read the relevant section in docs/tasks/TASK_002_EVALUATE_QUERY_CLASSIFIER.md.
- Summarize the sub-task scope briefly.
- Do not proceed if requirements conflict with existing code.

Implementation constraints:
- Do not add a hardcoded garbage-term blacklist.
- Do not use OpenAI or LLM fallback during evaluation.
- Do not split the physical dictionary into multiple files.
- Do not modify public API response schemas unless required.

After each sub-task:
- Run the most relevant targeted tests.
- Report changed files and test results.
- Commit only the changes related to that sub-task if tests pass.