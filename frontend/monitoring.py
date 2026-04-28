from __future__ import annotations

import ast
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.common.config import get_settings

LOG_LINE_RE = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \| "
    r"(?P<level>[A-Z]+) \| (?P<logger>[^|]+) \| (?P<message>.*)$"
)
STAGE_EVENT_RE = re.compile(
    r"trace_id=(?P<trace_id>[^\s]+) stage=(?P<stage>[^\s]+) success=(?P<success>True|False) "
    r"elapsed_sec=(?P<elapsed_sec>[-+]?\d*\.?\d+) throughput=(?P<throughput>[-+]?\d*\.?\d+) "
    r"(?P<throughput_unit>.+?) work_units=(?P<work_units>[-+]?\d*\.?\d+) error=(?P<error>.*)$"
)


def safe_literal_eval(raw: str) -> Any:
    """Parse logged Python repr payloads without failing the UI."""
    try:
        return ast.literal_eval(raw)
    except (SyntaxError, ValueError):
        return raw


def parse_query_event(message: str) -> dict[str, Any] | None:
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
        "query": safe_literal_eval(query_raw),
        "metadata": safe_literal_eval(metadata_raw),
    }


@st.cache_data(show_spinner=False)
def load_monitor_log(log_path: str, modified_time: float) -> tuple[pd.DataFrame, pd.DataFrame]:
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
            match = LOG_LINE_RE.match(raw_line.strip())
            if not match:
                continue

            timestamp = pd.to_datetime(match.group("timestamp"), format="%Y-%m-%d %H:%M:%S,%f", errors="coerce")
            message = match.group("message")
            query_event = parse_query_event(message)
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
            stage_rows.append({**stage, "query": trace["query"] or "(query missing in log)"})

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


def format_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def configured_model_names() -> list[str]:
    """Return configured Ollama generation model names without OpenAI fallbacks."""
    settings = get_settings()
    return list(dict.fromkeys([settings.ollama_small_model, settings.ollama_complex_model]))


def infer_generation_model(trace_stages: pd.DataFrame) -> str:
    """Infer the answer-generation model from monitored stage names."""
    settings = get_settings()
    if trace_stages.empty:
        return settings.ollama_complex_model

    stage_names = set(trace_stages["stage"].dropna().astype(str))
    if "stage_3_answer_generation_simple" in stage_names:
        return settings.ollama_small_model
    if "stage_3_answer_generation_complex" in stage_names:
        return settings.ollama_complex_model
    return settings.ollama_complex_model


def query_dashboard_rows(queries_df: pd.DataFrame, stages_df: pd.DataFrame) -> pd.DataFrame:
    """Build dashboard rows from parsed monitor traces."""
    columns = ["No.", "시간", "세션 ID", "질문", "모델", "상태", "응답 시간", "사용 문서 수", "사용 토큰", "작업"]
    if queries_df.empty:
        return pd.DataFrame(columns=columns)

    stage_by_trace = stages_df.groupby("trace_id") if not stages_df.empty else None
    rows: list[dict[str, Any]] = []
    for idx, row in queries_df.reset_index(drop=True).iterrows():
        trace_id = str(row.get("trace_id") or f"sess_{idx + 1:04d}")
        trace_stages = (
            stage_by_trace.get_group(trace_id)
            if stage_by_trace is not None and trace_id in stage_by_trace.groups
            else pd.DataFrame()
        )
        success = bool(trace_stages["success"].all()) if not trace_stages.empty else True
        elapsed = float(trace_stages["elapsed_sec"].sum()) if not trace_stages.empty else 0.0
        work_units = int(trace_stages["work_units"].sum()) if not trace_stages.empty else 0
        timestamp = row.get("query_timestamp")
        time_label = pd.to_datetime(timestamp).strftime("%Y-%m-%d %H:%M:%S") if pd.notna(timestamp) else "-"
        rows.append(
            {
                "No.": idx + 1,
                "시간": time_label,
                "세션 ID": trace_id,
                "질문": str(row.get("query") or "-"),
                "모델": infer_generation_model(trace_stages),
                "상태": "성공" if success else "오류",
                "응답 시간": f"{elapsed:.2f}초" if elapsed else "-",
                "사용 문서 수": max(1, len(trace_stages)) if not trace_stages.empty else "-",
                "사용 토큰": f"{work_units:,}" if work_units else "-",
                "작업": "상세 보기",
            }
        )
    return pd.DataFrame(rows, columns=columns)


def filter_queries_by_dates(queries_df: pd.DataFrame, start_date: date, end_date: date) -> pd.DataFrame:
    """Filter parsed query rows by an inclusive date range."""
    return queries_df[
        queries_df["query_date"].apply(lambda item: isinstance(item, date) and start_date <= item <= end_date)
    ].copy()
