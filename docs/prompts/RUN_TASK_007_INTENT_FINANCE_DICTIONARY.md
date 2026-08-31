Follow the instructions in

1. docs/TASK_RULES.md
2. docs/tasks/TASK_007_INTENT_FINANCE_DICTIONARY.md

Process Task 007-1 through Task 007-5 sequentially.

Before each sub-task:
- Re-read the relevant section in docs/tasks/TASK_007_INTENT_FINANCE_DICTIONARY.md.
- Summarize the sub-task scope briefly.
- Inspect the existing query intent dictionary, rule classifier, service integration, evaluation CLI, and tests before editing.
- Do not proceed if requirements conflict with the current RAG corpus or existing public API behavior.

Implementation constraints:
- Use only `data/raw/2020_경제금융용어 700선.pdf` and the currently indexed 700-term corpus as the source of truth.
- Do not use `data/raw/2026_경제금융용어 800선.pdf`.
- Do not include canonical intent terms that are absent from `data/processed/final_chunk.json` unless the task document explicitly allows it.
- Create the intent routing dictionary as `data/processed/finance_intent_terms.json`.
- Keep `data/processed/kiwi_user_dict.tsv` as the Kiwi tokenizer dictionary only.
- Do not use `kiwi_user_dict.tsv` as the production RAG-routing allowlist after this task.
- Load the JSON dictionary once and search using in-memory normalized lookup structures.
- Return canonical 700-term names in `matched_terms`, including when an alias matched.
- Do not add `trigger_strength`, `weak`, or any equivalent weak-term routing policy in this task.
- Exclude generic standalone aliases such as `차이`, `용어`, `설명`, `일반`, `효과`, and `금융`.
- Add English aliases only when they are high-confidence finance abbreviations or names explicitly present in the 700-term source, such as `ETF`, `LTV`, `DTI`, or a clear parenthesized English term.
- Do not mechanically translate every Korean term into English aliases.
- Preserve existing imports through `src/generation/query_intent.py`.
- Do not change API response schemas or frontend behavior unless required by a failing compatibility test.
- Keep TSV dictionary loading compatibility if it is needed by existing tests or call sites.

After each sub-task:
- Run the most relevant targeted tests.
- Report changed files and test results.
- Commit only the changes related to that sub-task if tests pass.

Final verification:
- Run query intent unit tests and any impacted RAG service tests.
- Run the query intent evaluation CLI with `finance_intent_terms.json` and `kiwi_user_dict.tsv`.
- Report the evaluation output paths.
- Report the canonical term count and alias count in `finance_intent_terms.json`.
- Document any skipped PDF extraction, live API, or vector DB verification and the reason.
