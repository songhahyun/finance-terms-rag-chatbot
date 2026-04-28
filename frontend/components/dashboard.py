from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from frontend.monitoring import (
    configured_model_names,
    filter_queries_by_dates,
    format_percent,
    load_monitor_log,
    query_dashboard_rows,
)


def render_dashboard_page() -> None:
    """Render the admin monitoring dashboard."""
    st.markdown('<div class="content-pad">', unsafe_allow_html=True)
    st.markdown('<p class="page-title">대시보드</p>', unsafe_allow_html=True)

    default_log_path = str(Path("logs") / "stage_monitor.log")
    with st.expander("모니터링 로그 연결", expanded=False):
        log_path = st.text_input("Monitor log path", value=default_log_path).strip()

    log_file = Path(log_path)
    if not log_path or not log_file.exists():
        st.warning(f"Log file not found: `{log_path}`")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    queries_df, stages_df = load_monitor_log(str(log_file), log_file.stat().st_mtime)
    tabs = st.tabs(["채팅 로그", "사용 통계", "지식 문서 통계"])
    with tabs[0]:
        _render_chat_log_tab(queries_df, stages_df)
    with tabs[1]:
        render_monitor_summary(queries_df, stages_df)
    with tabs[2]:
        render_recent_stage_logs(stages_df)

    st.markdown("</div>", unsafe_allow_html=True)


def _render_chat_log_tab(queries_df: pd.DataFrame, stages_df: pd.DataFrame) -> None:
    if queries_df.empty:
        st.info("No query logs found yet.")
        return

    available_dates = sorted([item for item in queries_df["query_date"].dropna().unique()])
    default_range = (available_dates[0], available_dates[-1]) if available_dates else (date.today(), date.today())
    filter_cols = st.columns([1.45, 1, 1, 1.6, 0.8])
    selected_dates = filter_cols[0].date_input("기간", value=default_range, label_visibility="collapsed")
    selected_status = filter_cols[1].selectbox("상태", ["전체 상태", "성공", "오류"], label_visibility="collapsed")
    selected_model = filter_cols[2].selectbox("모델", ["전체 모델", *configured_model_names()], label_visibility="collapsed")
    search_text = filter_cols[3].text_input("검색", placeholder="질문 또는 세션ID 검색", label_visibility="collapsed")

    if isinstance(selected_dates, tuple):
        start_date, end_date = selected_dates
    else:
        start_date = end_date = selected_dates

    filtered_queries = filter_queries_by_dates(queries_df, start_date, end_date)
    filtered_stages = stages_df[stages_df["trace_id"].isin(filtered_queries["trace_id"])].copy()
    table_df = query_dashboard_rows(filtered_queries, filtered_stages)
    if selected_status != "전체 상태":
        table_df = table_df[table_df["상태"] == selected_status]
    if selected_model != "전체 모델":
        table_df = table_df[table_df["모델"] == selected_model]
    if search_text:
        needle = search_text.casefold()
        table_df = table_df[
            table_df["질문"].str.casefold().str.contains(needle, na=False)
            | table_df["세션 ID"].str.casefold().str.contains(needle, na=False)
        ]

    csv_data = table_df.to_csv(index=False).encode("utf-8-sig")
    filter_cols[4].download_button(
        "CSV 다운로드",
        data=csv_data,
        file_name="chat_logs.csv",
        mime="text/csv",
        use_container_width=True,
    )

    total = len(table_df)
    success_count = int((table_df["상태"] == "성공").sum()) if total else 0
    avg_elapsed = float(filtered_stages["elapsed_sec"].mean()) if not filtered_stages.empty else 0.0
    st.markdown(
        f"""
        <div class="metric-strip">
            <div class="metric-card"><div class="metric-label">전체 대화</div><div class="metric-value">{total}</div></div>
            <div class="metric-card"><div class="metric-label">성공률</div><div class="metric-value">{format_percent(success_count / total) if total else "0.0%"}</div></div>
            <div class="metric-card"><div class="metric-label">평균 응답 시간</div><div class="metric-value">{avg_elapsed:.2f}초</div></div>
            <div class="metric-card"><div class="metric-label">로그 파일</div><div class="metric-value">{len(queries_df)}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "질문": st.column_config.TextColumn(width="large"),
            "상태": st.column_config.TextColumn(width="small"),
            "작업": st.column_config.TextColumn(width="small"),
        },
    )


def render_monitor_summary(queries_df: pd.DataFrame, stages_df: pd.DataFrame) -> None:
    """Render high-level monitoring metrics and per-stage summary."""
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
    metric_cols[1].metric("Success Rate (All Stages)", format_percent(successful_queries / total_queries))
    metric_cols[2].metric("Avg Elapsed Sec (All Stages)", f"{overall_elapsed:.2f}")
    metric_cols[3].metric("Avg Throughput (All Stages)", f"{overall_throughput:.2f}")

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


def render_recent_stage_logs(stages_df: pd.DataFrame) -> None:
    """Render raw stage log rows for filtered inspection."""
    with st.expander("Filtered Stage Logs", expanded=True):
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
