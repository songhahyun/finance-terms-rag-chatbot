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
            "status": "error",
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
        ["2026-06-10T10:00:01Z", "trace-2", "stage_0_intent_classification", "", "", "error", "bad", 1.0, 1.0],
        {
            "timestamp": "2026-06-10T10:00:02Z",
            "trace_id": "trace-3",
            "stage": "stage_1_retrieval_dense",
            "stage_type": "call_based",
            "status": "success",
            "elapsed_sec": 0.25,
            "attempted_calls_per_sec": 4.0,
            "successful_calls_per_sec": 4.0,
            "success_count": 1,
            "result_count": 5,
        },
        {
            "timestamp": "2026-06-10T10:00:03Z",
            "trace_id": "trace-4",
            "stage": "stage_2_generation",
            "stage_type": "generation",
            "status": "success",
            "elapsed_sec": 2.0,
            "generation_elapsed_sec": 2.0,
            "output_tokens": 12,
            "total_tokens": 20,
            "output_tokens_per_sec": 6.0,
            "chars": 24,
            "chars_per_sec": 12.0,
            "token_count_source": "provider_usage",
        },
    ]
    log_path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    stage_summary = PipelineMonitor(log_path=log_path).summary()["dashboard_stage_summary"]

    intent = stage_summary["stage_0_intent_classification"]
    assert intent["total_rows"] == 2
    assert intent["success_count"] == 1
    assert intent["fail_count"] == 1
    assert intent["avg_elapsed_sec"] == 0.75
    assert intent["success_rate"] == 0.5
    assert intent["throughput"] == {"rps": 1 / 0.75}
    assert intent["attempted_rps"] == 1 / 0.75

    assert stage_summary["stage_1_retrieval_dense"]["throughput"] == {"rps": 4.0}
    assert stage_summary["stage_2_generation"]["throughput"] == {
        "output_tps": 6.0,
        "rpm": 30.0,
        "output_tpm": 360.0,
        "total_tpm": 600.0,
    }


def test_recent_rows_returns_newest_first_with_error_filter_and_paging(tmp_path: Path) -> None:
    log_path = tmp_path / "stage_monitor.log"
    rows = []
    for index in range(25):
        rows.append(
            [
                f"2026-06-10T10:{index:02d}:00Z",
                f"trace-{index}",
                "generation",
                f"query {index}",
                "",
                "error" if index % 2 == 0 else "success",
                "error" if index % 2 == 0 else "",
                1.0,
                2.0,
            ]
        )
    log_path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    recent = PipelineMonitor(log_path=log_path).recent_rows(limit=20, page=1, errors_only=True)

    assert [row["trace_id"] for row in recent["rows"][:3]] == ["trace-24", "trace-22", "trace-20"]
    assert recent["paging"]["total_rows"] == 13
    assert recent["paging"]["start_row"] == 1
    assert recent["paging"]["end_row"] == 13
    assert recent["paging"]["pages"] == [{"page": 1, "label": "1-13", "start_row": 1, "end_row": 13}]


def test_recent_rows_supports_nested_page_ranges(tmp_path: Path) -> None:
    log_path = tmp_path / "stage_monitor.log"
    rows = [
        [f"2026-06-10T10:{index:02d}:00Z", f"trace-{index}", "retrieval", "", "", "success", "", 1, 1]
        for index in range(45)
    ]
    log_path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    recent = PipelineMonitor(log_path=log_path).recent_rows(limit=20, page=2)

    assert recent["rows"][0]["trace_id"] == "trace-24"
    assert recent["paging"]["page"] == 2
    assert recent["paging"]["start_row"] == 21
    assert recent["paging"]["end_row"] == 40
    assert [page["label"] for page in recent["paging"]["pages"]] == ["1-20", "21-40", "41-45"]


def test_dashboard_acceptance_intent_rps_uses_calls_not_legacy_throughput(tmp_path: Path) -> None:
    log_path = tmp_path / "stage_monitor.log"
    rows = [
        ["2026-06-10T10:00:00Z", "trace-1", "stage_0_intent_classification", "", "", "success", "", 1.008, 259.84],
        ["2026-06-10T10:00:01Z", "trace-2", "stage_0_intent_classification", "", "", "success", "", 1.008, 259.84],
    ]
    log_path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    intent = PipelineMonitor(log_path=log_path).summary()["dashboard_stage_summary"]["stage_0_intent_classification"]

    assert round(intent["successful_rps"], 2) == 0.99
    assert intent["throughput"]["rps"] != 259.84


def test_dashboard_acceptance_dense_error_and_zero_result(tmp_path: Path) -> None:
    log_path = tmp_path / "stage_monitor.log"
    rows = [
        {
            "timestamp": "2026-06-10T10:00:00Z",
            "trace_id": "trace-error",
            "stage": "stage_1_retrieval_dense",
            "stage_type": "call_based",
            "status": "error",
            "elapsed_sec": 0.2197,
            "attempted_calls_per_sec": 1 / 0.2197,
            "successful_calls_per_sec": 0.0,
            "success_count": 0,
            "result_count": 0,
        },
        {
            "timestamp": "2026-06-10T10:00:01Z",
            "trace_id": "trace-zero",
            "stage": "stage_1_retrieval_bm25",
            "stage_type": "call_based",
            "status": "zero_result",
            "elapsed_sec": 0.2197,
            "attempted_calls_per_sec": 1 / 0.2197,
            "successful_calls_per_sec": 1 / 0.2197,
            "success_count": 1,
            "result_count": 0,
        },
    ]
    log_path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    summary = PipelineMonitor(log_path=log_path).summary()["dashboard_stage_summary"]

    assert round(summary["stage_1_retrieval_dense"]["attempted_rps"], 4) == 4.5517
    assert summary["stage_1_retrieval_dense"]["successful_rps"] == 0.0
    assert summary["stage_1_retrieval_dense"]["status"] == "error"
    assert round(summary["stage_1_retrieval_bm25"]["successful_rps"], 4) == 4.5517
    assert summary["stage_1_retrieval_bm25"]["status"] == "zero_result"


def test_dashboard_acceptance_generation_and_fusion_schemas(tmp_path: Path) -> None:
    log_path = tmp_path / "stage_monitor.log"
    rows = [
        {
            "timestamp": "2026-06-10T10:00:00Z",
            "trace_id": "trace-gen",
            "stage": "stage_2_generation",
            "stage_type": "generation",
            "status": "success",
            "elapsed_sec": 3.0411,
            "generation_elapsed_sec": 3.0411,
            "input_tokens": 850,
            "output_tokens": 92,
            "total_tokens": 942,
            "output_tokens_per_sec": 92 / 3.0411,
            "chars": 183,
            "chars_per_sec": 183 / 3.0411,
            "token_count_source": "provider_usage",
        },
        {
            "timestamp": "2026-06-10T10:00:01Z",
            "trace_id": "trace-fusion",
            "stage": "stage_1_retrieval_fusion",
            "stage_type": "call_based",
            "status": "success",
            "elapsed_sec": 0.0001,
            "attempted_calls_per_sec": 10000.0,
            "successful_calls_per_sec": 10000.0,
        },
    ]
    log_path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    summary = PipelineMonitor(log_path=log_path).summary()["dashboard_stage_summary"]

    generation = summary["stage_2_generation"]
    assert round(generation["output_tps"], 4) == 30.2522
    assert round(generation["chars_per_sec"], 4) == 60.1756
    assert round(generation["output_tpm"], 4) == round((92 / 3.0411) * 60, 4)
    assert round(generation["total_tpm"], 4) == round((942 / 3.0411) * 60, 4)
    assert generation["token_count_source"] == "provider_usage"
    fusion = summary["stage_1_retrieval_fusion"]
    assert fusion["attempted_rps"] is None
    assert fusion["successful_rps"] is None
    assert fusion["status"] is None
