from __future__ import annotations

import logging
import json
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Any, Callable
from uuid import uuid4


@dataclass
class StageMetric:
    stage: str
    success: bool
    elapsed_sec: float
    throughput: float
    throughput_unit: str
    work_units: float
    started_at: str
    ended_at: str
    error: str | None = None


@dataclass
class QueryTrace:
    trace_id: str
    query: str
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)
    stage_metrics: list[StageMetric] = field(default_factory=list)
    _on_stage_metric: Callable[[str, StageMetric], None] | None = field(default=None, repr=False)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def run_stage(
        self,
        stage: str,
        fn: Callable[[], Any],
        *,
        throughput_unit: str = "units/sec",
        throughput_fn: Callable[[Any], float] | None = None,
        timeout_sec: float | None = None,
    ) -> Any:
        """Execute one pipeline stage while collecting timing metadata.
        Record success, throughput, and timeout information for the trace."""
        started_ts = datetime.now(timezone.utc).isoformat()
        t0 = perf_counter()
        success = False
        error: str | None = None
        result: Any = None
        try:
            result = fn()
            success = True
            return result
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            elapsed = max(perf_counter() - t0, 1e-9)
            ended_ts = datetime.now(timezone.utc).isoformat()
            units = 1.0
            if success and throughput_fn is not None:
                try:
                    units = float(throughput_fn(result))
                except Exception:  # noqa: BLE001
                    units = 0.0
            throughput = units / elapsed
            if success and timeout_sec is not None and elapsed > timeout_sec:
                success = False
                error = f"TimeoutExceeded: elapsed_sec={elapsed:.3f} > timeout_sec={timeout_sec:.3f}"
            metric = StageMetric(
                stage=stage,
                success=success,
                elapsed_sec=elapsed,
                throughput=throughput,
                throughput_unit=throughput_unit,
                work_units=units,
                started_at=started_ts,
                ended_at=ended_ts,
                error=error,
            )
            with self._lock:
                self.stage_metrics.append(metric)
            if self._on_stage_metric is not None:
                try:
                    self._on_stage_metric(self.trace_id, metric)
                except Exception:  # noqa: BLE001
                    pass

    def to_dict(self) -> dict[str, Any]:
        """Serialize the trace into a JSON-friendly dictionary.
        Include metadata and all collected stage metrics."""
        with self._lock:
            return {
                "trace_id": self.trace_id,
                "query": self.query,
                "created_at": self.created_at,
                "metadata": dict(self.metadata),
                "stages": [asdict(item) for item in self.stage_metrics],
            }


class PipelineMonitor:
    def __init__(self, *, max_history: int = 500, log_path: str | Path | None = None) -> None:
        """Initialize in-memory monitoring state and optional logging.
        Keep a bounded history of recent query traces."""
        self._history: deque[QueryTrace] = deque(maxlen=max_history)
        self._rows: deque[dict[str, Any]] = deque(maxlen=max_history)
        self._lock = Lock()
        self._log_path = Path(log_path) if log_path is not None else None
        self._load_log_rows()
        self._logger = self._build_logger(log_path)

    @staticmethod
    def _build_logger(log_path: str | Path | None) -> logging.Logger | None:
        """Create or reuse a logger for pipeline monitoring output.
        Attach file and console handlers only when needed."""
        if log_path is None:
            return None

        path = Path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger("pipeline.monitor")
        logger.setLevel(logging.INFO)
        logger.propagate = False

        resolved = str(path.resolve())
        has_file_handler = any(
            isinstance(handler, logging.FileHandler)
            and str(Path(handler.baseFilename).resolve()) == resolved
            for handler in logger.handlers
        )
        if not has_file_handler:
            file_handler = logging.FileHandler(path, encoding="utf-8")
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
            )
            logger.addHandler(file_handler)

        has_stream_handler = any(
            isinstance(handler, logging.StreamHandler)
            and not isinstance(handler, logging.FileHandler)
            for handler in logger.handlers
        )
        if not has_stream_handler:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(
                logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
            )
            logger.addHandler(stream_handler)

        return logger

    def _log_stage_metric(self, trace_id: str, metric: StageMetric) -> None:
        """Write one stage metric to the configured logger.
        Skip logging entirely when no logger has been configured."""
        self._append_metric_row(trace_id, metric)
        if self._logger is None:
            return
        metadata: dict[str, Any] = {}
        with self._lock:
            for trace in self._history:
                if trace.trace_id == trace_id:
                    metadata = dict(trace.metadata)
                    break
        self._logger.info(
            "trace_id=%s stage=%s success=%s elapsed_sec=%.4f throughput=%.4f %s work_units=%.2f error=%s metadata=%s",
            trace_id,
            metric.stage,
            metric.success,
            metric.elapsed_sec,
            metric.throughput,
            metric.throughput_unit,
            metric.work_units,
            metric.error or "-",
            metadata,
        )

    def _append_metric_row(self, trace_id: str, metric: StageMetric) -> None:
        """Add one in-process stage metric to the bounded row queue."""
        query = ""
        with self._lock:
            for trace in self._history:
                if trace.trace_id == trace_id:
                    query = trace.query
                    break
            self._rows.append(
                {
                    "timestamp": metric.ended_at,
                    "trace_id": trace_id,
                    "stage": metric.stage,
                    "user_query": query,
                    "generated_answer": "",
                    "status": "success" if metric.success else "fail",
                    "error_message": metric.error or "",
                    "elapsed_sec": metric.elapsed_sec,
                    "throughput": metric.throughput,
                }
            )

    def _load_log_rows(self) -> None:
        """Load JSON-line monitor rows from the configured log file."""
        if self._log_path is None or not self._log_path.exists():
            return
        for line in self._log_path.read_text(encoding="utf-8").splitlines():
            row = self._parse_log_row(line)
            if row is None:
                continue
            self._rows.append(row)

    @staticmethod
    def _parse_log_row(line: str) -> dict[str, Any] | None:
        """Parse one JSON-line monitor row into the dashboard schema."""
        text = line.strip()
        if not text:
            return None
        try:
            raw = json.loads(text)
        except json.JSONDecodeError:
            return None

        if isinstance(raw, list):
            values = list(raw)
            keys = [
                "timestamp",
                "trace_id",
                "stage",
                "user_query",
                "generated_answer",
                "status",
                "error_message",
                "elapsed_sec",
                "throughput",
            ]
            data = {key: values[index] if index < len(values) else "" for index, key in enumerate(keys)}
        elif isinstance(raw, dict):
            values = list(raw.values())
            data = dict(raw)
            data["timestamp"] = values[0] if values else data.get("timestamp", "")
        else:
            return None

        return {
            "timestamp": str(data.get("timestamp", "")),
            "trace_id": str(data.get("trace_id", "")),
            "stage": str(data.get("stage", "")),
            "user_query": str(data.get("user_query", "")),
            "generated_answer": str(data.get("generated_answer", "")),
            "status": PipelineMonitor._normalize_status(data.get("status")),
            "error_message": str(data.get("error_message", "")),
            "elapsed_sec": PipelineMonitor._to_float(data.get("elapsed_sec")),
            "throughput": PipelineMonitor._to_float(data.get("throughput")),
        }

    @staticmethod
    def _normalize_status(value: Any) -> str:
        """Normalize status values to the dashboard success/fail vocabulary."""
        text = str(value).strip().lower()
        if text in {"success", "true", "ok"}:
            return "success"
        if text in {"fail", "failed", "false", "error"}:
            return "fail"
        return text

    @staticmethod
    def _to_float(value: Any) -> float:
        """Convert numeric log values to float, defaulting invalid data to zero."""
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _dashboard_stage_name(stage: Any) -> str:
        """Normalize known pipeline stage names for dashboard grouping."""
        text = str(stage).strip()
        for expected in ("intent_classification", "retrieval", "generation"):
            if text == expected or text.endswith(f"_{expected}"):
                return expected
        return text

    @classmethod
    def _stage_metrics_from_rows(cls, rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Aggregate dashboard stage metrics from normalized monitor rows."""
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            stage = cls._dashboard_stage_name(row.get("stage", ""))
            if stage:
                grouped[stage].append(row)

        stage_metrics: dict[str, dict[str, Any]] = {}
        for stage, stage_rows in grouped.items():
            total = len(stage_rows)
            success_count = sum(1 for row in stage_rows if row.get("status") == "success")
            fail_count = sum(1 for row in stage_rows if row.get("status") == "fail")
            elapsed_values = [cls._to_float(row.get("elapsed_sec")) for row in stage_rows]
            throughput_values = [cls._to_float(row.get("throughput")) for row in stage_rows]
            avg_elapsed_sec = sum(elapsed_values) / total if total else 0.0
            avg_throughput = sum(throughput_values) / total if total else 0.0
            throughput = cls._throughput_for_stage(stage, avg_elapsed_sec, avg_throughput)
            stage_metrics[stage] = {
                "total_rows": total,
                "success_count": success_count,
                "fail_count": fail_count,
                "avg_elapsed_sec": avg_elapsed_sec,
                "success_rate": success_count / total if total else 0.0,
                "throughput": throughput,
            }
        return stage_metrics

    @staticmethod
    def _throughput_for_stage(stage: str, avg_elapsed_sec: float, avg_throughput: float) -> dict[str, float]:
        """Return stage-specific throughput metrics for dashboard display."""
        if stage == "intent_classification":
            return {"rps": avg_throughput}
        if stage == "retrieval":
            return {"qps": avg_throughput}
        if stage == "generation":
            rpm = 60.0 / avg_elapsed_sec if avg_elapsed_sec > 0 else 0.0
            return {
                "output_tps": avg_throughput,
                "rpm": rpm,
                "tpm": avg_throughput * 60.0,
            }
        return {"throughput": avg_throughput}

    def _log_trace_started(self, trace: QueryTrace) -> None:
        """Log the start of a new traced query.
        Record the query text and any attached metadata."""
        if self._logger is None:
            return
        self._logger.info(
            "trace_id=%s event=query_received query=%r metadata=%s",
            trace.trace_id,
            trace.query,
            trace.metadata,
        )

    def start_trace(self, query: str, metadata: dict[str, Any] | None = None) -> QueryTrace:
        """Create and register a new query trace object.
        Add it to bounded history and emit an initial log entry."""
        trace = QueryTrace(
            trace_id=str(uuid4()),
            query=query,
            created_at=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
            _on_stage_metric=self._log_stage_metric,
        )
        with self._lock:
            self._history.append(trace)
        self._log_trace_started(trace)
        return trace

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return recent traces in reverse chronological order.
        Respect the requested limit while always returning a list."""
        with self._lock:
            traces = list(self._history)[-max(limit, 1) :]
        return [trace.to_dict() for trace in reversed(traces)]

    def recent_rows(self, *, limit: int = 20, page: int = 1, errors_only: bool = False) -> dict[str, Any]:
        """Return paginated recent dashboard rows ordered newest first."""
        page_size = limit if limit in {20, 50, 100} else 20
        page_index = max(page, 1)
        with self._lock:
            rows = list(reversed(self._rows))
        if errors_only:
            rows = [row for row in rows if row.get("status") == "fail"]

        total_rows = len(rows)
        total_pages = max((total_rows + page_size - 1) // page_size, 1)
        page_index = min(page_index, total_pages)
        start = (page_index - 1) * page_size
        end = min(start + page_size, total_rows)
        return {
            "rows": rows[start:end],
            "paging": {
                "limit": page_size,
                "page": page_index,
                "total_rows": total_rows,
                "total_pages": total_pages,
                "start_row": start + 1 if total_rows else 0,
                "end_row": end,
                "errors_only": errors_only,
                "pages": self._page_ranges(total_rows, page_size),
            },
        }

    @staticmethod
    def _page_ranges(total_rows: int, page_size: int) -> list[dict[str, int | str]]:
        """Build page labels as row ranges such as 1-20 and 21-40."""
        if total_rows <= 0:
            return []
        pages = []
        total_pages = (total_rows + page_size - 1) // page_size
        for index in range(total_pages):
            start = index * page_size + 1
            end = min((index + 1) * page_size, total_rows)
            pages.append({"page": index + 1, "label": f"{start}-{end}", "start_row": start, "end_row": end})
        return pages

    def summary(self) -> dict[str, Any]:
        """Aggregate stage metrics across stored traces.
        Compute counts, success rates, and average performance values."""
        grouped: dict[str, list[StageMetric]] = defaultdict(list)
        with self._lock:
            traces = list(self._history)
            rows = list(self._rows)

        for trace in traces:
            for metric in trace.stage_metrics:
                grouped[metric.stage].append(metric)

        summary_by_stage: dict[str, dict[str, float | int | str]] = {}
        for stage_name, metrics in grouped.items():
            if not metrics:
                continue
            total = len(metrics)
            success_count = sum(1 for m in metrics if m.success)
            elapsed_avg = sum(m.elapsed_sec for m in metrics) / total
            throughput_avg = sum(m.throughput for m in metrics) / total
            summary_by_stage[stage_name] = {
                "count": total,
                "success_count": success_count,
                "success_rate": success_count / total,
                "avg_elapsed_sec": elapsed_avg,
                "avg_throughput": throughput_avg,
                "throughput_unit": metrics[0].throughput_unit,
            }

        return {
            "trace_count": len(traces),
            "stage_summary": summary_by_stage,
            "dashboard_stage_summary": self._stage_metrics_from_rows(rows),
            "total_rows": len(rows),
            "error_rows": sum(1 for row in rows if row.get("status") == "fail"),
            "warning_rows": 0,
            "last_refresh": datetime.now(timezone.utc).isoformat(),
        }
