# Codex Task Rules

This document defines reusable rules for running Codex CLI tasks in this repository.

Use this file together with a specific task file, such as:

```text
docs/tasks/TASK_001_ADD_QUERY_CLASSIFIER.md
```

and, if needed, a specific execution prompt file, such as:

```text
docs/prompts/RUN_TASK_001_ADD_QUERY_CLASSIFIER.md
```

---

## 1. Branch Rule

- Before starting any task, verify that the current Git branch is `dev`.
- If the current branch is not `dev`, stop immediately and report the current branch.
- Do not switch branches unless explicitly instructed by the user.

Recommended check:

```powershell
git branch --show-current
```

Expected result:

```text
dev
```

---

## 2. Encoding Rule

- Task files may contain Korean text.
- Always read Markdown task files using UTF-8 encoding.
- In PowerShell, use the following command format:

```powershell
Get-Content -Raw -Encoding UTF8 <TASK_FILE_PATH>
```

Example:

```powershell
Get-Content -Raw -Encoding UTF8 docs\tasks\TASK_001_ADD_QUERY_CLASSIFIER.md
```

- If Korean text appears corrupted, do not guess the content.
- Stop and report the encoding issue.

Use this format:

```text
NEED_USER_CONFIRMATION: The task file text appears corrupted due to an encoding issue. Please confirm the correct file content or encoding setup.
```

---

## 3. Task Execution Rule

- Implement only one task at a time.
- Before starting each task, re-read the corresponding task section from the task file.
- Do not skip tasks.
- Do not merge multiple tasks into a single implementation step unless explicitly instructed.
- After completing each task, run the relevant tests.
- After each completed task, run:

```powershell
git status
```

- Review the changed files before committing.
- Stage and commit only the changes related to the completed task.
- Do not include unrelated formatting, cleanup, or refactoring unless the task explicitly requires it.

---

## 4. Code Editing Permission Rule

- Do not ask for permission before editing code when the requested task scope is clear.
- Proceed with code changes directly within the specified task scope.
- This rule applies to normal implementation work, bug fixes, refactoring, tests, and documentation edits that are explicitly required by the current task.
- Ask for confirmation only when the implementation requires one of the following:
  - changing the task specification
  - expanding the task scope
  - modifying unrelated files
  - making a product, UX, architecture, or design decision not specified in the task file
  - choosing between multiple incompatible implementation approaches
  - deleting existing functionality
  - changing public APIs or data contracts
  - modifying deployment, authentication, billing, or security-related behavior
  - touching secrets, credentials, API keys, or environment files

When confirmation is needed, stop and ask in the CLI using this exact format:

```text
NEED_USER_CONFIRMATION: <question>
```

---

## 5. GitHub Issue Creation Rule

- Before starting implementation, summarize the task file content and create a GitHub Issue for the work.
- The issue summary should be based on the relevant task file, for example:

```text
docs/tasks/TASK_001_ADD_QUERY_CLASSIFIER.md
```

- If the task file contains multiple subtasks, summarize the overall goal and list the subtasks in the issue body.
- Use GitHub CLI to create the issue when available.

Example:

```powershell
gh issue create --title "Task 001: ADD_QUERY_CLASSIFIER" --body "<task summary and subtask list>"
```

- After creating the issue, capture the created issue number.
- Use that issue number in all commits related to the task.
- If an issue number is already specified in the task prompt or task file, use that issue instead of creating a duplicate issue.
- If issue creation fails, stop before implementation and ask for confirmation.

Use this format:

```text
NEED_USER_CONFIRMATION: Failed to create a GitHub Issue for this task. Should I continue without an issue reference, or should the issue be created manually first?
```

---

## 6. GitHub Issue Rule

- If an issue number was created before implementation, reference that issue in the commit message.
- If an issue number is already specified in the task prompt or task file, use that issue instead of creating a duplicate issue.
- If GitHub CLI is available, inspect the issue before implementing the task.

Example:

```powershell
gh issue view 8
```

- If the issue cannot be accessed, continue only if the task file contains enough information to implement safely.
- If the task file and GitHub issue conflict, stop and ask for confirmation.

Use this format:

```text
NEED_USER_CONFIRMATION: The task file and GitHub Issue #<ISSUE_NUMBER> contain conflicting requirements. Which source should I follow?
```

---

## 7. Test Rule

- Run the most relevant tests after each task.
- Prefer targeted tests first.
- If targeted tests pass and the change may affect broader behavior, run the broader test suite.
- If tests fail, do not commit the task.
- Report the failing command, error summary, and suspected cause.
- Do not hide or ignore failing tests.

Examples:

```powershell
pytest tests/path/to/relevant_tests.py
```

```powershell
pytest
```

For frontend projects, use the repository's configured commands, such as:

```powershell
npm test
npm run lint
npm run typecheck
```

Only run commands that are appropriate for the repository.

---

## 8. Git Commit Rule

- Commit after each completed task if the relevant tests pass.
- Each task should produce a separate commit.
- The commit should include only files changed for that task.
- Reference the GitHub Issue created or specified before implementation in each related commit message.
- Do not run `git push`.
- The user will review and push commits manually.

Commit message format:

```text
Task <TASK_NUMBER>: <summary of changes> (#<ISSUE_NUMBER>)
```

Example:

```text
Task 001: Add query classifier (#8)
```

If the task file uses subtask numbers such as Task 0 through Task 7, use a clear commit message that references both the parent task and the subtask when appropriate.

Example:

```text
Task 001-0: add dictionary loader and normalizer (#8)
```

---

## 9. Scope Control Rule

- Work only on files required by the current task.
- Do not perform opportunistic refactoring.
- Do not rewrite large modules unless the task explicitly requires it.
- Preserve existing public interfaces unless the task explicitly requires an interface change.
- Preserve existing behavior unless the task explicitly requires a behavior change.
- If additional work appears necessary, stop and ask for confirmation.

Use this format:

```text
NEED_USER_CONFIRMATION: Implementing this task safely appears to require changes outside the specified scope: <summary>. Should I proceed?
```

---

## 10. Specification Rule

- Do not modify the task specification unless explicitly instructed.
- Do not reinterpret vague requirements silently.
- Do not assume missing business logic.
- If the specification is ambiguous, ask for confirmation.
- If the specification is incomplete but a safe minimal implementation is possible, implement the minimal version and clearly report the assumption.

Use this format for ambiguity:

```text
NEED_USER_CONFIRMATION: <specific ambiguity or decision needed>
```

---

## 11. Safety Rule

- Do not run destructive commands unless explicitly instructed.
- Do not delete files unless the task explicitly requires deletion.
- Do not reset, rebase, force-push, or rewrite Git history.
- Do not modify secrets, credentials, API keys, or environment files unless explicitly instructed.
- Do not expose secrets in logs, commits, or documentation.
- Do not run `git push` under any circumstance.
- If pushing is required, stop and tell the user to push manually after review.

Forbidden commands unless explicitly instructed, except `git push`, which remains forbidden:

```powershell
git push
git push --force
git reset --hard
git clean -fd
Remove-Item -Recurse -Force
rm -rf
```

If a task appears to require `git push`, stop and use this exact format:

```text
NEED_USER_CONFIRMATION: This task appears to require pushing commits, but `git push` is prohibited by TASK_RULES.md. Please review the local commits and push manually if appropriate.
```

---

## 12. Reporting Rule

After each task, report:

1. Task number completed
2. Files changed
3. Tests run
4. Test result
5. Commit hash, if committed
6. GitHub Issue number referenced
7. Any assumptions or unresolved issues

Example:

```text
Completed Task 001-0.

Changed files:
- src/serving/query_intent.py
- tests/test_query_intent.py

Tests run:
- pytest tests/test_query_intent.py

Result:
- Passed

Issue:
- #8

Commit:
- abc1234 Task 001-0: add dictionary loader and normalizer (#8)

Assumptions / unresolved:
- None
```

---

## 13. Stop Conditions

Stop immediately and ask for confirmation if:

- the current branch is not `dev`
- the task file cannot be read correctly
- Korean text appears corrupted
- the task file and GitHub issue conflict
- the implementation requires scope expansion
- relevant tests fail and the fix is not obvious
- the task requires modifying secrets or environment files
- the task requires destructive Git operations
- the task requires `git push`

Use this exact format:

```text
NEED_USER_CONFIRMATION: <question or reason>
```

---

## 14. Final Rule

Codex should complete the requested task work, run tests, and create local commits only.

Codex must not run `git push`.

The user is responsible for final review and pushing to the remote repository.
