Follow the instructions in

1. docs/TASK_RULES.md
2. docs/tasks/TASK_004_CHAT_UI_SESSION_FIXES.md

Process Task 004-1 through Task 004-9 sequentially.

Before each sub-task:
- Re-read the relevant section in docs/tasks/TASK_004_CHAT_UI_SESSION_FIXES.md.
- Summarize the sub-task scope briefly.
- Do not proceed if requirements conflict with existing code.

Implementation constraints:
- Preserve existing chat API compatibility fields: `chunk_id`, `source`, and `text`.
- Do not show source documents for non-RAG intents.
- Do not limit source rendering to the first 3 items.
- Keep conversation history isolated by authenticated user.
- Keep frontend changes consistent with the existing app shell and chat page style.
- Do not introduce backend persistence for chat history unless the task document is updated.

After each sub-task:
- Run the most relevant targeted tests or build checks.
- Report changed files and test results.
- Commit only the changes related to that sub-task if tests pass.
