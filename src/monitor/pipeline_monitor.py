from __future__ import annotations

import logging
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
        self._lock = Lock()
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
        if self._logger is None:
            return
        self._logger.info(
            "trace_id=%s stage=%s success=%s elapsed_sec=%.4f throughput=%.4f %s work_units=%.2f error=%s",
            trace_id,
            metric.stage,
            metric.success,
            metric.elapsed_sec,
            metric.throughput,
            metric.throughput_unit,
            metric.work_units,
            metric.error or "-",
        )

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

    def summary(self) -> dict[str, Any]:
        """Aggregate stage metrics across stored traces.
        Compute counts, success rates, and average performance values."""
        grouped: dict[str, list[StageMetric]] = defaultdict(list)
        with self._lock:
            traces = list(self._history)

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
        }
