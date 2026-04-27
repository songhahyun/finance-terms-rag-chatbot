from __future__ import annotations

import ast
import json
import os
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st

LOG_LINE_RE = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \| "
    r"(?P<level>[A-Z]+) \| (?P<logger>[^|]+) \| (?P<message>.*)$"
)
STAGE_EVENT_RE = re.compile(
    r"trace_id=(?P<trace_id>[^\s]+) stage=(?P<stage>[^\s]+) success=(?P<success>True|False) "
    r"elapsed_sec=(?P<elapsed_sec>[-+]?\d*\.?\d+) throughput=(?P<throughput>[-+]?\d*\.?\d+) "
    r"(?P<throughput_unit>.+?) work_units=(?P<work_units>[-+]?\d*\.?\d+) error=(?P<error>.*)$"
)


def _post_chat(api_url: str, question: str, mode: str, k: int, language: str, timeout_sec: int) -> dict[str, Any]:
    """Send a standard chat request to the backend API.
    Return the parsed JSON response for the current question."""
    resp = requests.post(
        api_url,
        json={"question": question, "mode": mode, "k": k, "language": language},
        timeout=timeout_sec,
    )
    resp.raise_for_status()
    return resp.json()


def _stream_chat(
    api_url: str,
    question: str,
    mode: str,
    k: int,
    language: str,
    timeout_sec: int,
):
    """Stream chat events from the backend endpoint.
    Yield each decoded JSON event as it arrives."""
    with requests.post(
        api_url,
        json={"question": question, "mode": mode, "k": k, "language": language},
        timeout=timeout_sec,
        stream=True,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            yield json.loads(line)


def _init_state() -> None:
    """Initialize Streamlit session state for chat history.
    Create the message list only when it is missing."""
    if "messages" not in st.session_state:
        st.session_state.messages = []


def _render_sources(sources: list[dict[str, Any]]) -> None:
    """Render retrieved source snippets in an expandable panel.
    Show chunk metadata and text for each cited result."""
    if not sources:
        return
    with st.expander("Sources"):
        for idx, item in enumerate(sources, start=1):
            chunk_id = item.get("chunk_id")
            source = item.get("source")
            text = item.get("text", "")
            st.markdown(f"**{idx}. chunk_id:** `{chunk_id}`")
            st.markdown(f"**source:** `{source}`")
            st.markdown(f"**text:** {text}")
            st.divider()


def _render_history() -> None:
    """Replay prior chat messages from session state.
    Render any attached source entries with each assistant turn."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            _render_sources(message.get("sources") or [])


def _safe_literal_eval(raw: str) -> Any:
    """Parse logged Python repr payloads without failing the UI."""
    try:
        return ast.literal_eval(raw)
    except (SyntaxError, ValueError):
        return raw


def _parse_query_event(message: str) -> dict[str, Any] | None:
    """Parse query_received log lines while tolerating quotes inside the query."""
    prefix = " event=query_received query="
    if prefix not in message or " metadata=" not in message:
        return None

    trace_prefix, remainder = message.split(prefix, 1)
    if not trace_prefix.startswith("trace_id="):
        return None

    query_raw, metadata_raw = remainder.rsplit(" metadata=", 1)
    return {
        "trace_id": trace_prefix.removeprefix("trace_id=").strip(),
        "query": _safe_literal_eval(query_raw),
        "metadata": _safe_literal_eval(metadata_raw),
    }


@st.cache_data(show_spinner=False)
def _load_monitor_log(log_path: str, modified_time: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse the monitor log into query and stage dataframes."""
    path = Path(log_path)
    if not path.exists():
        return pd.DataFrame(), pd.DataFrame()

    traces: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "trace_id": None,
            "query": None,
            "query_timestamp": None,
            "query_date": None,
            "metadata": None,
            "stages": [],
        }
    )

    with path.open("r", encoding="utf-8", errors="replace") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line:
                continue

            match = LOG_LINE_RE.match(line)
            if not match:
                continue

            timestamp = pd.to_datetime(match.group("timestamp"), format="%Y-%m-%d %H:%M:%S,%f", errors="coerce")
            message = match.group("message")

            query_event = _parse_query_event(message)
            if query_event is not None:
                trace_id = str(query_event["trace_id"])
                trace = traces[trace_id]
                trace["trace_id"] = trace_id
                trace["query"] = query_event["query"]
                trace["query_timestamp"] = timestamp
                trace["query_date"] = timestamp.date() if pd.notna(timestamp) else None
                trace["metadata"] = query_event["metadata"]
                continue

            stage_match = STAGE_EVENT_RE.match(message)
            if not stage_match:
                continue

            trace_id = stage_match.group("trace_id")
            trace = traces[trace_id]
            trace["trace_id"] = trace_id
            if trace["query_timestamp"] is None:
                trace["query_timestamp"] = timestamp
                trace["query_date"] = timestamp.date() if pd.notna(timestamp) else None

            trace["stages"].append(
                {
                    "trace_id": trace_id,
                    "timestamp": timestamp,
                    "date": timestamp.date() if pd.notna(timestamp) else None,
                    "stage": stage_match.group("stage"),
                    "success": stage_match.group("success") == "True",
                    "elapsed_sec": float(stage_match.group("elapsed_sec")),
                    "throughput": float(stage_match.group("throughput")),
                    "throughput_unit": stage_match.group("throughput_unit").strip(),
                    "work_units": float(stage_match.group("work_units")),
                    "error": None if stage_match.group("error") == "-" else stage_match.group("error").strip(),
                }
            )

    query_rows: list[dict[str, Any]] = []
    stage_rows: list[dict[str, Any]] = []
    for trace in traces.values():
        query_rows.append(
            {
                "trace_id": trace["trace_id"],
                "query": trace["query"] or "(query missing in log)",
                "query_timestamp": trace["query_timestamp"],
                "query_date": trace["query_date"],
                "metadata": trace["metadata"],
            }
        )
        for stage in trace["stages"]:
            stage_rows.append(
                {
                    **stage,
                    "query": trace["query"] or "(query missing in log)",
                    "query_timestamp": trace["query_timestamp"],
                    "query_date": trace["query_date"],
                }
            )

    queries_df = (
        pd.DataFrame(query_rows).sort_values(
            by=["query_timestamp", "trace_id"], ascending=[False, False], na_position="last"
        )
        if query_rows
        else pd.DataFrame()
    )
    stages_df = (
        pd.DataFrame(stage_rows).sort_values(
            by=["timestamp", "trace_id", "stage"], ascending=[False, False, True], na_position="last"
        )
        if stage_rows
        else pd.DataFrame()
    )

    return queries_df, stages_df


def _format_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _format_number(value: float) -> str:
    return f"{value:.2f}"


def _filter_monitor_data(queries_df: pd.DataFrame, stages_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply date and stage filters from the sidebar."""
    st.subheader("Monitoring Filters")

    if queries_df.empty:
        st.info("No query logs found yet.")
        return queries_df, stages_df

    available_dates = sorted([item for item in queries_df["query_date"].dropna().unique()], reverse=True)
    if not available_dates:
        st.info("No valid timestamps were found in the selected log.")
        return queries_df.iloc[0:0].copy(), stages_df.iloc[0:0].copy()
    min_date = available_dates[-1]
    max_date = available_dates[0]
    default_range = (min_date, max_date)
    selected_dates = st.date_input("Date range", value=default_range, min_value=min_date, max_value=max_date)

    if isinstance(selected_dates, tuple):
        start_date, end_date = selected_dates
    else:
        start_date = end_date = selected_dates

    available_stages = sorted(stages_df["stage"].dropna().unique().tolist()) if not stages_df.empty else []
    selected_stages = st.multiselect("Stages", options=available_stages, default=available_stages)

    filtered_queries = queries_df[
        queries_df["query_date"].apply(lambda item: isinstance(item, date) and start_date <= item <= end_date)
    ].copy()

    filtered_stages = stages_df[stages_df["trace_id"].isin(filtered_queries["trace_id"])].copy()
    if selected_stages:
        filtered_stages = filtered_stages[filtered_stages["stage"].isin(selected_stages)].copy()
    else:
        filtered_stages = filtered_stages.iloc[0:0].copy()

    return filtered_queries, filtered_stages


def _render_monitor_summary(queries_df: pd.DataFrame, stages_df: pd.DataFrame) -> None:
    """Render high-level metrics and per-stage summary."""
    st.subheader("Summary")

    total_queries = len(queries_df)
    if total_queries == 0:
        st.info("No queries match the current filters.")
        return

    if stages_df.empty:
        successful_queries = 0
        overall_elapsed = 0.0
        overall_throughput = 0.0
    else:
        stage_success_by_trace = stages_df.groupby("trace_id")["success"].all()
        successful_queries = int(stage_success_by_trace.sum())
        overall_elapsed = float(stages_df["elapsed_sec"].mean())
        overall_throughput = float(stages_df["throughput"].mean())

    metric_cols = st.columns(4)
    metric_cols[0].metric("Total Queries", f"{total_queries}")
    metric_cols[1].metric("Success Rate (All Stages)", _format_percent(successful_queries / total_queries))
    metric_cols[2].metric("Avg Elapsed Sec (All Stages)", _format_number(overall_elapsed))
    metric_cols[3].metric("Avg Throughput (All Stages)", _format_number(overall_throughput))
    st.caption(
        "Overall throughput is averaged across stage log values and may mix different units such as keywords/sec, "
        "docs/sec, labels/sec, and chars/sec."
    )

    if stages_df.empty:
        st.info("No stage records match the selected stage filter.")
        return

    grouped = stages_df.groupby("stage", dropna=False)
    stage_summary = grouped.agg(
        stage_runs=("stage", "count"),
        successful_stage_runs=("success", "sum"),
        avg_elapsed_sec=("elapsed_sec", "mean"),
        avg_throughput=("throughput", "mean"),
    ).reset_index()

    success_queries_by_stage = stages_df[stages_df["success"]].groupby("stage")["trace_id"].nunique().to_dict()
    throughput_units_by_stage = grouped["throughput_unit"].agg(
        lambda values: ", ".join(sorted(set(values.dropna().tolist())))
    ).to_dict()

    stage_summary["success_rate"] = stage_summary["stage"].map(
        lambda stage_name: ((success_queries_by_stage.get(stage_name, 0) / total_queries) * 100.0)
        if total_queries
        else 0.0
    )
    stage_summary["throughput_unit"] = stage_summary["stage"].map(
        lambda stage_name: throughput_units_by_stage.get(stage_name, "")
    )
    stage_summary = stage_summary[
        [
            "stage",
            "success_rate",
            "avg_elapsed_sec",
            "avg_throughput",
            "throughput_unit",
            "stage_runs",
            "successful_stage_runs",
        ]
    ].rename(
        columns={
            "stage": "Stage",
            "success_rate": "Success Rate",
            "avg_elapsed_sec": "Avg Elapsed Sec",
            "avg_throughput": "Avg Throughput",
            "throughput_unit": "Throughput Unit",
            "stage_runs": "Stage Runs",
            "successful_stage_runs": "Successful Stage Runs",
        }
    )

    st.dataframe(
        stage_summary,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Success Rate": st.column_config.NumberColumn(format="%.1f%%"),
            "Avg Elapsed Sec": st.column_config.NumberColumn(format="%.2f"),
            "Avg Throughput": st.column_config.NumberColumn(format="%.2f"),
        },
    )


def _render_error_logs(stages_df: pd.DataFrame) -> None:
    """Render failed stage runs with the originating query."""
    st.subheader("Error Logs")

    if stages_df.empty:
        st.info("No stage records match the current filters.")
        return

    error_df = stages_df[~stages_df["success"] | stages_df["error"].notna()].copy()
    if error_df.empty:
        st.success("No errors found for the current filters.")
        return

    error_df = error_df.sort_values(by="timestamp", ascending=False)
    error_df = error_df.rename(
        columns={
            "timestamp": "Timestamp",
            "trace_id": "Trace ID",
            "query": "User Query",
            "stage": "Stage",
            "elapsed_sec": "Elapsed Sec",
            "error": "Error",
        }
    )
    st.dataframe(
        error_df[["Timestamp", "Trace ID", "User Query", "Stage", "Elapsed Sec", "Error"]],
        use_container_width=True,
        hide_index=True,
        column_config={"Elapsed Sec": st.column_config.NumberColumn(format="%.2f")},
    )


def _render_recent_stage_logs(stages_df: pd.DataFrame) -> None:
    """Render raw stage log rows for filtered inspection."""
    with st.expander("Filtered Stage Logs", expanded=False):
        if stages_df.empty:
            st.write("No stage rows to display.")
            return
        display_df = stages_df.copy()
        display_df["success"] = display_df["success"].map(lambda value: "Y" if bool(value) else "N")
        display_df = display_df.rename(
            columns={
                "timestamp": "Timestamp",
                "trace_id": "Trace ID",
                "query": "User Query",
                "stage": "Stage",
                "success": "Success",
                "elapsed_sec": "Elapsed Sec",
                "throughput": "Throughput",
                "throughput_unit": "Throughput Unit",
                "work_units": "Work Units",
                "error": "Error",
            }
        )
        st.dataframe(
            display_df[
                [
                    "Timestamp",
                    "Trace ID",
                    "User Query",
                    "Stage",
                    "Success",
                    "Elapsed Sec",
                    "Throughput",
                    "Throughput Unit",
                    "Work Units",
                    "Error",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Elapsed Sec": st.column_config.NumberColumn(format="%.2f"),
                "Throughput": st.column_config.NumberColumn(format="%.2f"),
                "Work Units": st.column_config.NumberColumn(format="%.2f"),
            },
        )


def _render_monitoring_tab() -> None:
    """Render monitoring dashboard from the stage monitor log."""
    st.subheader("Pipeline Monitoring")
    default_log_path = str(Path("logs") / "stage_monitor.log")
    log_path = st.text_input("Monitor log path", value=default_log_path).strip()
    log_file = Path(log_path)

    if not log_path:
        st.warning("Enter a log path to load monitoring data.")
        return

    if not log_file.exists():
        st.warning(f"Log file not found: `{log_path}`")
        return

    queries_df, stages_df = _load_monitor_log(str(log_file), log_file.stat().st_mtime)

    filter_container = st.container(border=True)
    with filter_container:
        filtered_queries, filtered_stages = _filter_monitor_data(queries_df, stages_df)

    _render_monitor_summary(filtered_queries, filtered_stages)
    st.divider()
    _render_error_logs(filtered_stages)
    _render_recent_stage_logs(filtered_stages)


def _render_chat_tab() -> None:
    """Render the existing chat interface."""
    st.subheader("Chat")
    st.caption("Streamlit frontend connected to FastAPI `/chat` and `/chat/stream` endpoints")

    _init_state()

    with st.sidebar:
        st.subheader("Chat Settings")
        backend_base_url = st.text_input(
            "Backend base URL",
            value=os.getenv("CHAT_API_BASE_URL", "http://localhost:8000"),
            help="FastAPI server URL",
        ).strip().rstrip("/")
        mode = st.selectbox("Retrieval mode", options=["hybrid", "dense", "bm25"], index=0)
        language_label = st.selectbox("Answer language", options=["Korean", "English"], index=0)
        language = "ko" if language_label == "Korean" else "en"
        k = st.slider("Top-K", min_value=1, max_value=20, value=5)
        timeout_sec = st.number_input("API timeout (sec)", min_value=5, max_value=300, value=120, step=5)
        if st.button("Clear conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    api_url = f"{backend_base_url}/chat"
    stream_api_url = f"{backend_base_url}/chat/stream"
    _render_history()

    prompt = st.chat_input("Type your question")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Generating answer..."):
            try:
                answer_placeholder = st.empty()
                answer = ""
                sources: list[dict[str, Any]] = []
                for event in _stream_chat(stream_api_url, prompt, mode, int(k), language, int(timeout_sec)):
                    event_type = str(event.get("type", ""))
                    if event_type == "token":
                        answer += str(event.get("content", ""))
                        answer_placeholder.markdown(answer)
                    elif event_type == "final":
                        if not answer:
                            answer = str(event.get("answer", ""))
                            answer_placeholder.markdown(answer)
                        sources = event.get("sources", []) or []
                    elif event_type == "error":
                        raise requests.RequestException(str(event.get("message", "unknown stream error")))
                if not answer:
                    result = _post_chat(api_url, prompt, mode, int(k), language, int(timeout_sec))
                    answer = result.get("answer", "")
                    sources = result.get("sources", [])
                    answer_placeholder.markdown(answer)
            except requests.RequestException as exc:
                answer = f"API request failed: {exc}"
                sources = []
                st.markdown(answer)
            _render_sources(sources)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
        }
    )


def main() -> None:
    """Run the Streamlit application entry point."""
    st.set_page_config(page_title="Finance Terms RAG Chat", page_icon="F", layout="wide")
    st.title("Finance Terms RAG Chat")

    chat_tab, monitor_tab = st.tabs(["Chat", "Monitoring"])
    with chat_tab:
        _render_chat_tab()
    with monitor_tab:
        _render_monitoring_tab()


if __name__ == "__main__":
    main()
