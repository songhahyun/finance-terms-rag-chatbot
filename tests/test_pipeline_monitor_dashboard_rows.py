from __future__ import annotations

import json
from pathlib import Path

from src.monitor import PipelineMonitor


def test_monitor_summary_loads_json_line_rows(tmp_path: Path) -> None:
    log_path = tmp_path / "stage_monitor.log"
    rows = [
        [
            "2026-06-10T10:00:00Z",
            "trace-1",
            "intent_classification",
            "금리란?",
            "",
            "success",
            "",
            0.1,
            10.0,
        ],
        {
            "logged_at": "2026-06-10T10:00:01Z",
            "trace_id": "trace-2",
            "stage": "generation",
            "user_query": "환율 설명",
            "generated_answer": "",
            "status": "fail",
            "error_message": "timeout",
            "elapsed_sec": "1.5",
            "throughput": "0",
        },
    ]
    log_path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")

    summary = PipelineMonitor(log_path=log_path).summary()

    assert summary["total_rows"] == 2
    assert summary["error_rows"] == 1
    assert summary["warning_rows"] == 0
    assert "last_refresh" in summary


def test_monitor_summary_counts_in_process_stage_rows() -> None:
    monitor = PipelineMonitor(log_path=None)
    trace = monitor.start_trace("금리란?")

    trace.run_stage(
        "intent_classification",
        lambda: "needs_rag",
        throughput_unit="rps",
    )

    summary = monitor.summary()

    assert summary["trace_count"] == 1
    assert summary["total_rows"] == 1
    assert summary["error_rows"] == 0
