Follow the instructions in

1. docs/TASK_RULES.md
2. docs/tasks/TASK_005_DASHBOARD_FIXES.md

Process Task 005-1 through Task 005-5 sequentially.

Before each sub-task:
- Re-read the relevant section in docs/tasks/TASK_005_DASHBOARD_FIXES.md.
- Summarize the sub-task scope briefly.
- Do not proceed if requirements conflict with existing code.

Implementation constraints:
- Preserve existing legacy monitor API behavior where possible.
- Enforce admin-only access using `require_roles("admin")`.
- Keep dashboard refresh-on-click only; do not add realtime websocket streaming.
- Keep frontend UI consistent with existing `frontend-web` styling and navigation.
- Do not introduce new persistence beyond the existing in-memory queue unless the task document is updated.

After each sub-task:
- Run the most relevant targeted tests or build checks.
- Report changed files and test results.
- Commit only the changes related to that sub-task if tests pass.
