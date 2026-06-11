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


def test_monitor_summary_aggregates_stage_metrics_and_throughput(tmp_path: Path) -> None:
    log_path = tmp_path / "stage_monitor.log"
    rows = [
        ["2026-06-10T10:00:00Z", "trace-1", "stage_0_intent_classification", "", "", "success", "", 0.5, 2.0],
        ["2026-06-10T10:00:01Z", "trace-2", "intent_classification", "", "", "fail", "bad", 1.0, 1.0],
        ["2026-06-10T10:00:02Z", "trace-3", "retrieval", "", "", "success", "", 0.25, 8.0],
        ["2026-06-10T10:00:03Z", "trace-4", "generation", "", "", "success", "", 2.0, 12.0],
    ]
    log_path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    stage_summary = PipelineMonitor(log_path=log_path).summary()["dashboard_stage_summary"]

    intent = stage_summary["intent_classification"]
    assert intent["total_rows"] == 2
    assert intent["success_count"] == 1
    assert intent["fail_count"] == 1
    assert intent["avg_elapsed_sec"] == 0.75
    assert intent["success_rate"] == 0.5
    assert intent["throughput"] == {"rps": 1.5}

    assert stage_summary["retrieval"]["throughput"] == {"qps": 8.0}
    assert stage_summary["generation"]["throughput"] == {
        "output_tps": 12.0,
        "rpm": 30.0,
        "tpm": 720.0,
    }
