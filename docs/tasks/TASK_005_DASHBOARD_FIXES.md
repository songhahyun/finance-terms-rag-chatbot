# TASK_005_DASHBOARD_FIXES

## 0. Context

- A new dashboard page is required in `frontend-web` to replace the existing dashboard view.
- The dashboard must show monitor data from `stage_monitor.log` using backend APIs.
- Admin-only access is required, using `backend/app/auth/deps.py` and `backend/app/auth/rbac.py` with `require_roles("admin")`.
- The backend should reuse the existing in-memory queue implementation from `src/monitor/pipeline_monitor.py`.
- The dashboard page only needs refresh-on-click behavior; realtime streaming is not required.

## 1. Goal

Implement a compact dashboard that provides:
- overall row-level summaries,
- stage-level metrics and throughput,
- paginated recent logs with error filtering.

## 2. Data schema

The monitor data should follow this schema:
- `timestamp`: not an explicit JSON field name; the first value in each row is the timestamp.
- `trace_id`: exact field name exists.
- `stage`: exact field name exists.
- `user_query`
- `generated_answer`
- `status`: `success` or `fail` (the log uses `success` literally).
- `error_message`: present when `status == fail`.
- `elapsed_sec`
- `throughput`

## 3. Requirements and subtasks

### Task 005-1: Backend API and legacy compatibility
- Review existing chart monitor APIs in `backend/app/routers/monitor.py`.
- Maintain or extend the legacy API contract for:
  - `GET /api/monitor/summary`
  - `GET /api/monitor/recent`
- Protect endpoints with `require_roles("admin")`.
- Confirm existing `/api/monitor/summary` and `/api/monitor/recent` behavior before extending.

### Task 005-2: Log parsing and summary metrics
- Parse `stage_monitor.log` as JSON lines.
- Extract `timestamp` from the first row value and the explicit field values listed in the schema.
- Aggregate row-level totals from the current queue (not de-duplicated by `trace_id`).
- Count error rows as `status == fail`.
- Ignore `WARN`; the current log tags are all `INFO`.

### Task 005-3: Stage-level metrics and throughput
- For each stage, calculate:
  - total row count
  - success count
  - fail count
  - average elapsed time
  - success rate
- Compute throughput per stage:
  - `intent_classification`: RPS
  - `retrieval`: QPS
  - `generation`: Output TPS, RPM, TPM

### Task 005-4: Recent logs pagination and filtering
- Use the existing 1000-row in-memory queue.
- Return recent rows ordered by newest first.
- Support query params:
  - `limit` = 20, 50, 100
  - `page` = 1-based page index
  - `errors_only` = boolean
- Provide nested paging for row ranges: `1–20`, `21–40`, `41–60`, etc.

### Task 005-5: Frontend dashboard page
- Implement a new dashboard page in `frontend-web` that replaces the current left-menu dashboard.
- Display numeric summary cards for:
  - total rows, error rows, warning rows, last refresh.
- Display stage summary blocks for each stage.
- Add a stacked bar chart for throughput.
- Add a recent logs panel with:
  - error-only toggle,
  - rows-per-page dropdown (20 / 50 / 100),
  - nested page buttons, and
  - row-level columns.
- Refresh content on page load or manual refresh.

### Task 005-6: Retrieval throughput and empty-result failure semantics
- Change all `stage_1_retrieval_*` throughput measurements to use search call count:
  - use `throughput_fn=lambda out: 1`
  - use `throughput_unit="calls/sec"`
- Record retrieval stages with empty results as monitor failures without interrupting answer generation:
  - `dense`: when `len(out) == 0`, record `success=False`
  - `bm25`: when `len(out) == 0`, record `success=False`
  - `fusion`: record `success=False` only when both dense and bm25 search results are empty
- Do not raise exceptions for empty retrieval results.
  - The answer flow should continue.
  - Only the monitor metric should be marked as failed.
- Keep `stage_2_generation` throughput as `chars/sec` for now.
  - Do not add token counting in this task.
- Keep existing logs unchanged.
  - Apply the new metric meaning only to newly generated logs.
  - Do not add legacy/new metric separation in the dashboard.

### Task 005-7: Expand dashboard layout width
- Increase the overall app layout main container width so dashboard components do not get clipped on the right side.
- Apply the width change at the shared app layout level, not only inside the dashboard page.
- Preserve existing left navigation behavior.
- Keep responsive behavior for smaller screens:
  - dashboard content may scroll horizontally where table/chart width requires it
  - text and controls must not overlap or be cut off

### Task 005-8: Split throughput charts by stage and metric
- Replace the single combined throughput chart with separate charts that correspond to the stage summary blocks.
- Use raw stage names from the monitor data in chart titles and labels.
  - Do not map names to display aliases.
  - Example: use `stage_0_intent_classification`, not `Intent Classification`.
- Use recent row timestamps as the x-axis time source.
  - The chart data scope is the current in-memory monitor queue, up to 1000 rows.
- Use metric values on the y-axis.
- Add these throughput charts:
  - `stage_0_intent_classification` / RPS / line chart
  - `stage_1_retrieval_bm25` / RPS / line chart
  - `stage_1_retrieval_dense` / RPS / line chart
  - `stage_1_retrieval_fusion` / RPS / line chart
  - `stage_2_generation` / RPM / line chart
  - `stage_2_generation` / TPM / stacked bar chart
- For `stage_1_retrieval_bm25`, `stage_1_retrieval_dense`, and `stage_1_retrieval_fusion`:
  - label the chart metric as RPS
  - use the `calls/sec` throughput value from newly generated logs as-is
- For `stage_2_generation`:
  - keep the current generation throughput source as `chars/sec`
  - calculate approximate RPM as `60 / elapsed_sec`
  - calculate approximate TPM as `throughput * 60`
  - label the charts as RPM and TPM
  - document in the dashboard legend/help text that TPM is currently approximated from `chars/sec * 60`
  - note that a real `token_count()` implementation is planned for a future task
- For generation chart layout:
  - show the RPM and TPM charts as left/right blocks corresponding to `stage_2_generation`

### Task 005-9: Throughput legend and hover explanations
- Add `@radix-ui/react-tooltip` to `frontend-web`.
- Use Recharts `Legend` with the `content` prop to render a custom legend.
- Add hover explanations for each chart metric through Radix Tooltip.
- Tooltip text should explain:
  - metric name
  - source value used by the chart
  - calculation formula
  - known approximation caveats
- Required tooltip explanations:
  - RPS for retrieval stages: uses the new `calls/sec` monitor throughput value.
  - RPS for `stage_0_intent_classification`: uses the monitor throughput value for intent classification.
  - RPM for `stage_2_generation`: approximate requests per minute, calculated as `60 / elapsed_sec`.
  - TPM for `stage_2_generation`: approximate value, currently calculated as `chars/sec * 60`; real token-count-based TPM requires a future `token_count()` helper.
- Keep Recharts data-point hover behavior available for chart values.
- Do not implement websocket or realtime streaming as part of this task.

### Task 005-10: Dashboard content tabs
- Keep the top dashboard summary cards visible at all times:
  - `total_rows`
  - `error_rows`
  - warning rows
  - last refresh
- Replace the always-visible stacked dashboard content below the summary cards with tabs.
- Add three tabs:
  - `Stage summary`
  - `Throughput charts`
  - `Recent logs`
- Show only the selected tab panel below the summary cards.
- Move the existing stage summary component into the `Stage summary` tab.
- Move the existing throughput chart components into the `Throughput charts` tab.
- Move the existing recent logs component into the `Recent logs` tab.
- Preserve each component's current behavior inside its tab:
  - chart legends and hover explanations still work
  - recent logs filtering and pagination still work
  - manual refresh still refreshes all dashboard data
- Keep the tab UI consistent with the existing `frontend-web` dashboard styling.
- Do not introduce websocket or realtime streaming as part of this task.

## 4. Acceptance criteria

- A new dashboard page is available from the left menu as the dashboard entry.
- Admin-only access is enforced for dashboard monitor APIs.
- Dashboard shows overall totals, stage summaries, and paginated recent logs.
- The backend APIs support the required query params and schema.
- The implementation uses the existing in-memory queue and legacy API patterns.
- Retrieval dashboard throughput for new `stage_1_retrieval_*` logs uses `calls/sec`.
- Empty dense or bm25 retrieval results are marked as monitor failures without raising exceptions.
- Fusion retrieval is marked as a monitor failure only when both dense and bm25 results are empty.
- Generation throughput remains `chars/sec`.
- The shared app layout main content width is expanded so dashboard components are not clipped on the right.
- Throughput charts are split by raw stage name and metric as specified in Task 005-8.
- Retrieval throughput charts display RPS labels using the new `calls/sec` values.
- Generation RPM and TPM charts use the documented approximate formulas until token counting is added.
- Throughput chart legends expose hover explanations using `@radix-ui/react-tooltip` and Recharts custom legend content.
- The top summary cards remain visible above dashboard content tabs.
- `Stage summary`, `Throughput charts`, and `Recent logs` are shown as separate tabs, with only the selected panel visible.

## 5. Example dashboard layout

### Top row: summary cards
- `Total rows` (queue row count)
- `Error rows` (status fail count)
- `Warning rows` (if any)
- `Last refresh` timestamp

### Tabbed content below summary cards

#### Stage summary tab
- A summary block for each stage:
  - `intent_classification`: total / success / fail, avg elapsed, RPS
  - `retrieval`: total / success / fail, avg elapsed, QPS
  - `generation`: total / success / fail, avg elapsed, TPS / RPM / TPM

#### Throughput charts tab
- Split charts by raw stage name and metric as specified in Task 005-8.
- Keep chart legends and hover explanations from Task 005-9.

#### Recent logs tab
- `Errors only` toggle
- `Rows per page` dropdown: 20 / 50 / 100
- Nested page buttons: 1–20, 21–40, 41–60, ...
- Table columns: `timestamp`, `trace_id`, `stage`, `status`, `elapsed_sec`, `user_query`, `error_message`

### Navigation / behavior
- Left menu uses the existing dashboard entry.
- Page refreshes on navigation or manual refresh button.
- No websocket streaming required for this MVP.
