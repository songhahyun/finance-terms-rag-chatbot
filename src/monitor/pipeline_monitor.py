from __future__ import annotations

import logging
import json
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Any, Awaitable, Callable
from uuid import uuid4

CALL_BASED_STAGES = {
    "stage_0_intent_classification",
    "stage_1_retrieval_bm25",
    "stage_1_retrieval_dense",
    "stage_1_retrieval_fusion",
}
GENERATION_STAGES = {"stage_2_generation"}
RETRIEVAL_STAGES = {
    "stage_1_retrieval_bm25",
    "stage_1_retrieval_dense",
    "stage_1_retrieval_fusion",
}
FUSION_STAGE = "stage_1_retrieval_fusion"


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
    stage_type: str = "unknown"
    status: str = "success"
    attempted_count: int | None = None
    success_count: int | None = None
    fail_count: int | None = None
    result_count: int | None = None
    attempted_calls_per_sec: float | None = None
    successful_calls_per_sec: float | None = None
    provider: str | None = None
    model: str | None = None
    generation_elapsed_sec: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    output_tokens_per_sec: float | None = None
    input_tokens_per_sec: float | None = None
    chars: int | None = None
    chars_per_sec: float | None = None
    token_count_source: str | None = None
    raw_usage: dict[str, Any] | None = None


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
        success_fn: Callable[[Any], bool] | None = None,
        result_count_fn: Callable[[Any], int] | None = None,
        metric_extra_fn: Callable[[Any, float], dict[str, Any]] | None = None,
        timeout_sec: float | None = None,
    ) -> Any:
        """Execute one pipeline stage while collecting timing metadata.
        Record success, throughput, and timeout information for the trace."""
        started_ts = datetime.now(timezone.utc).isoformat()
        t0 = perf_counter()
        success = False
        error: str | None = None
        result: Any = None
        status = "success"
        try:
            result = fn()
            success = True
            return result
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"
            status = "timeout" if isinstance(exc, TimeoutError) else "error"
            raise
        finally:
            elapsed = max(perf_counter() - t0, 1e-9)
            ended_ts = datetime.now(timezone.utc).isoformat()
            stage_type = PipelineMonitor._stage_type(stage)
            units = 1.0
            if success and throughput_fn is not None:
                try:
                    units = float(throughput_fn(result))
                except Exception:  # noqa: BLE001
                    units = 0.0
            throughput = units / elapsed
            if success and success_fn is not None:
                try:
                    success = bool(success_fn(result))
                except Exception as exc:  # noqa: BLE001
                    success = False
                    error = f"{type(exc).__name__}: {exc}"
                    status = "error"
                if not success and error is None:
                    error = "StageMarkedFailed: success_fn returned false"
                    status = "error"
            if success and timeout_sec is not None and elapsed > timeout_sec:
                success = False
                error = f"TimeoutExceeded: elapsed_sec={elapsed:.3f} > timeout_sec={timeout_sec:.3f}"
                status = "timeout"
            extra: dict[str, Any] = {}
            if metric_extra_fn is not None:
                try:
                    extra = dict(metric_extra_fn(result, elapsed))
                except Exception as exc:  # noqa: BLE001
                    extra = {"metric_error": f"{type(exc).__name__}: {exc}"}
            if stage_type == "call_based":
                result_count = PipelineMonitor._result_count(result, result_count_fn) if success else 0
                if success:
                    status = "zero_result" if stage in RETRIEVAL_STAGES and result_count == 0 else "success"
                attempted_count = 1
                success_count = 1 if success else 0
                fail_count = 0 if success else 1
                extra.update(
                    {
                        "attempted_count": attempted_count,
                        "success_count": success_count,
                        "fail_count": fail_count,
                        "result_count": result_count,
                        "attempted_calls_per_sec": attempted_count / elapsed,
                        "successful_calls_per_sec": success_count / elapsed,
                    }
                )
                throughput = extra["successful_calls_per_sec"]
                units = float(success_count)
                throughput_unit = "calls/sec"
            elif stage_type == "generation":
                status = status if not success else str(extra.get("status") or "success")
                extra.setdefault("generation_elapsed_sec", elapsed)
                if extra.get("chars_per_sec") is not None:
                    throughput = float(extra["chars_per_sec"])
                    units = float(extra.get("chars") or 0)
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
                stage_type=stage_type,
                status=status,
                attempted_count=extra.get("attempted_count"),
                success_count=extra.get("success_count"),
                fail_count=extra.get("fail_count"),
                result_count=extra.get("result_count"),
                attempted_calls_per_sec=extra.get("attempted_calls_per_sec"),
                successful_calls_per_sec=extra.get("successful_calls_per_sec"),
                provider=extra.get("provider"),
                model=extra.get("model"),
                generation_elapsed_sec=extra.get("generation_elapsed_sec"),
                input_tokens=extra.get("input_tokens"),
                output_tokens=extra.get("output_tokens"),
                total_tokens=extra.get("total_tokens"),
                output_tokens_per_sec=extra.get("output_tokens_per_sec"),
                input_tokens_per_sec=extra.get("input_tokens_per_sec"),
                chars=extra.get("chars"),
                chars_per_sec=extra.get("chars_per_sec"),
                token_count_source=extra.get("token_count_source"),
                raw_usage=extra.get("raw_usage"),
            )
            with self._lock:
                self.stage_metrics.append(metric)
            if self._on_stage_metric is not None:
                try:
                    self._on_stage_metric(self.trace_id, metric)
                except Exception:  # noqa: BLE001
                    pass

    async def run_retrieval_stage_async(
        self,
        stage: str,
        fn: Callable[[], Awaitable[Any]],
        *,
        result_count_fn: Callable[[Any], int] | None = None,
    ) -> Any:
        """Execute and record one asynchronous retrieval stage."""
        started_ts = datetime.now(timezone.utc).isoformat()
        t0 = perf_counter()
        success = False
        error: str | None = None
        result: Any = None
        try:
            result = await fn()
            success = True
            return result
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            elapsed = max(perf_counter() - t0, 1e-9)
            ended_ts = datetime.now(timezone.utc).isoformat()
            result_count = PipelineMonitor._result_count(result, result_count_fn) if success else 0
            status = "success" if success else "error"
            if success and result_count == 0:
                status = "zero_result"
            metric = StageMetric(
                stage=stage,
                success=success,
                elapsed_sec=elapsed,
                throughput=(1.0 / elapsed) if success else 0.0,
                throughput_unit="calls/sec",
                work_units=1.0 if success else 0.0,
                started_at=started_ts,
                ended_at=ended_ts,
                error=error,
                stage_type="call_based",
                status=status,
                attempted_count=1,
                success_count=1 if success else 0,
                fail_count=0 if success else 1,
                result_count=result_count,
                attempted_calls_per_sec=1.0 / elapsed,
                successful_calls_per_sec=(1.0 / elapsed) if success else 0.0,
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
                    "stage_type": metric.stage_type,
                    "user_query": query,
                    "generated_answer": "",
                    "status": metric.status,
                    "error_message": metric.error or "",
                    "elapsed_sec": metric.elapsed_sec,
                    "throughput": metric.throughput,
                    "attempted_count": metric.attempted_count,
                    "success_count": metric.success_count,
                    "fail_count": metric.fail_count,
                    "result_count": metric.result_count,
                    "attempted_calls_per_sec": metric.attempted_calls_per_sec,
                    "successful_calls_per_sec": metric.successful_calls_per_sec,
                    "provider": metric.provider,
                    "model": metric.model,
                    "generation_elapsed_sec": metric.generation_elapsed_sec,
                    "input_tokens": metric.input_tokens,
                    "output_tokens": metric.output_tokens,
                    "total_tokens": metric.total_tokens,
                    "output_tokens_per_sec": metric.output_tokens_per_sec,
                    "input_tokens_per_sec": metric.input_tokens_per_sec,
                    "chars": metric.chars,
                    "chars_per_sec": metric.chars_per_sec,
                    "token_count_source": metric.token_count_source,
                    "raw_usage": metric.raw_usage,
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
            "stage_type": str(data.get("stage_type") or PipelineMonitor._stage_type(str(data.get("stage", "")))),
            "user_query": str(data.get("user_query", "")),
            "generated_answer": str(data.get("generated_answer", "")),
            "status": PipelineMonitor._normalize_status(data.get("status")),
            "error_message": str(data.get("error_message", "")),
            "elapsed_sec": PipelineMonitor._to_float(data.get("elapsed_sec")),
            "throughput": PipelineMonitor._to_float(data.get("throughput")),
            "attempted_count": PipelineMonitor._to_optional_int(data.get("attempted_count")),
            "success_count": PipelineMonitor._to_optional_int(data.get("success_count")),
            "fail_count": PipelineMonitor._to_optional_int(data.get("fail_count")),
            "result_count": PipelineMonitor._to_optional_int(data.get("result_count")),
            "attempted_calls_per_sec": PipelineMonitor._to_optional_float(data.get("attempted_calls_per_sec")),
            "successful_calls_per_sec": PipelineMonitor._to_optional_float(data.get("successful_calls_per_sec")),
            "provider": data.get("provider"),
            "model": data.get("model"),
            "generation_elapsed_sec": PipelineMonitor._to_optional_float(data.get("generation_elapsed_sec")),
            "input_tokens": PipelineMonitor._to_optional_int(data.get("input_tokens")),
            "output_tokens": PipelineMonitor._to_optional_int(data.get("output_tokens")),
            "total_tokens": PipelineMonitor._to_optional_int(data.get("total_tokens")),
            "output_tokens_per_sec": PipelineMonitor._to_optional_float(data.get("output_tokens_per_sec")),
            "input_tokens_per_sec": PipelineMonitor._to_optional_float(data.get("input_tokens_per_sec")),
            "chars": PipelineMonitor._to_optional_int(data.get("chars")),
            "chars_per_sec": PipelineMonitor._to_optional_float(data.get("chars_per_sec")),
            "token_count_source": data.get("token_count_source"),
            "raw_usage": data.get("raw_usage"),
        }

    @staticmethod
    def _normalize_status(value: Any) -> str:
        """Normalize status values to the dashboard success/fail vocabulary."""
        text = str(value).strip().lower()
        if text in {"success", "true", "ok"}:
            return "success"
        if text in {"zero_result", "error", "timeout"}:
            return text
        if text in {"fail", "failed", "false"}:
            return "error"
        return text

    @staticmethod
    def _to_float(value: Any) -> float:
        """Convert numeric log values to float, defaulting invalid data to zero."""
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _to_optional_float(value: Any) -> float | None:
        """Convert numeric log values to float, preserving missing values."""
        if value in {None, ""}:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_optional_int(value: Any) -> int | None:
        """Convert numeric log values to int, preserving missing values."""
        if value in {None, ""}:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _stage_type(stage: str) -> str:
        """Return the metric schema type for a stage name."""
        if stage in CALL_BASED_STAGES or stage.endswith("_intent_classification"):
            return "call_based"
        if stage in GENERATION_STAGES or stage.endswith("_generation"):
            return "generation"
        return "unknown"

    @staticmethod
    def _result_count(result: Any, result_count_fn: Callable[[Any], int] | None) -> int:
        """Return a safe result count for call-based stage status classification."""
        if result_count_fn is not None:
            return max(int(result_count_fn(result)), 0)
        try:
            return max(len(result), 0)  # type: ignore[arg-type]
        except TypeError:
            return 0

    @staticmethod
    def _dashboard_stage_name(stage: Any) -> str:
        """Return the raw monitor stage name for dashboard grouping."""
        return str(stage).strip()

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
            success_count = sum(1 for row in stage_rows if row.get("status") in {"success", "zero_result"})
            fail_count = sum(1 for row in stage_rows if row.get("status") in {"error", "timeout", "fail"})
            elapsed_values = [cls._to_float(row.get("elapsed_sec")) for row in stage_rows]
            avg_elapsed_sec = sum(elapsed_values) / total if total else 0.0
            stage_type = str(stage_rows[-1].get("stage_type") or cls._stage_type(stage))
            throughput = cls._throughput_for_stage(stage, avg_elapsed_sec, stage_rows)
            stage_metrics[stage] = {
                "stage_type": stage_type,
                "total_rows": total,
                "success_count": success_count,
                "fail_count": fail_count,
                "avg_elapsed_sec": avg_elapsed_sec,
                "success_rate": success_count / total if total else 0.0,
                "throughput": throughput,
                **cls._dashboard_schema_fields(stage, stage_rows, avg_elapsed_sec),
            }
        return stage_metrics

    @classmethod
    def _throughput_for_stage(cls, stage: str, avg_elapsed_sec: float, rows: list[dict[str, Any]]) -> dict[str, float]:
        """Return stage-specific throughput metrics for dashboard display."""
        if stage == FUSION_STAGE:
            return {}
        if cls._stage_type(stage) == "call_based":
            return {"rps": cls._avg_optional(rows, "successful_calls_per_sec") or (1.0 / avg_elapsed_sec if avg_elapsed_sec > 0 else 0.0)}
        if cls._stage_type(stage) == "generation":
            rpm = 60.0 / avg_elapsed_sec if avg_elapsed_sec > 0 else 0.0
            output_tps = cls._avg_optional(rows, "output_tokens_per_sec") or 0.0
            total_tps = cls._avg_ratio(rows, "total_tokens", "generation_elapsed_sec")
            return {
                "output_tps": output_tps,
                "rpm": rpm,
                "output_tpm": output_tps * 60.0,
                "total_tpm": total_tps * 60.0,
            }
        return {"throughput": cls._avg_optional(rows, "throughput") or 0.0}

    @classmethod
    def _dashboard_schema_fields(cls, stage: str, rows: list[dict[str, Any]], avg_elapsed_sec: float) -> dict[str, Any]:
        """Build explicit dashboard table fields for the stage metric schema."""
        latest_status = str(rows[-1].get("status") or "")
        if stage == FUSION_STAGE:
            return {
                "elapsed_sec": avg_elapsed_sec,
                "attempted_rps": None,
                "successful_rps": None,
                "result_count": None,
                "status": None,
            }
        if cls._stage_type(stage) == "call_based":
            attempted_rps = cls._avg_optional(rows, "attempted_calls_per_sec")
            successful_rps = cls._avg_optional(rows, "successful_calls_per_sec")
            return {
                "elapsed_sec": avg_elapsed_sec,
                "attempted_rps": attempted_rps if attempted_rps is not None else (1.0 / avg_elapsed_sec if avg_elapsed_sec > 0 else 0.0),
                "successful_rps": successful_rps if successful_rps is not None else (1.0 / avg_elapsed_sec if avg_elapsed_sec > 0 else 0.0),
                "result_count": sum(cls._to_optional_int(row.get("result_count")) or 0 for row in rows),
                "status": latest_status,
            }
        if cls._stage_type(stage) == "generation":
            generation_elapsed = cls._avg_optional(rows, "generation_elapsed_sec") or avg_elapsed_sec
            output_tps = cls._avg_optional(rows, "output_tokens_per_sec")
            chars_per_sec = cls._avg_optional(rows, "chars_per_sec")
            total_tps = cls._avg_ratio(rows, "total_tokens", "generation_elapsed_sec")
            return {
                "elapsed_sec": generation_elapsed,
                "output_tps": output_tps,
                "chars_per_sec": chars_per_sec,
                "rpm": 60.0 / generation_elapsed if generation_elapsed > 0 else 0.0,
                "output_tpm": output_tps * 60.0 if output_tps is not None else None,
                "total_tpm": total_tps * 60.0,
                "input_tokens": sum(cls._to_optional_int(row.get("input_tokens")) or 0 for row in rows),
                "output_tokens": sum(cls._to_optional_int(row.get("output_tokens")) or 0 for row in rows),
                "total_tokens": sum(cls._to_optional_int(row.get("total_tokens")) or 0 for row in rows),
                "token_count_source": str(rows[-1].get("token_count_source") or "unavailable"),
                "status": latest_status,
            }
        return {"elapsed_sec": avg_elapsed_sec, "status": latest_status}

    @classmethod
    def _avg_optional(cls, rows: list[dict[str, Any]], key: str) -> float | None:
        """Average a numeric row field while ignoring missing values."""
        values = [value for row in rows if (value := cls._to_optional_float(row.get(key))) is not None]
        return sum(values) / len(values) if values else None

    @classmethod
    def _avg_ratio(cls, rows: list[dict[str, Any]], numerator_key: str, denominator_key: str) -> float:
        """Average per-row numerator/denominator rates while ignoring missing values."""
        rates = []
        for row in rows:
            numerator = cls._to_optional_float(row.get(numerator_key))
            denominator = cls._to_optional_float(row.get(denominator_key))
            if numerator is not None and denominator and denominator > 0:
                rates.append(numerator / denominator)
        return sum(rates) / len(rates) if rates else 0.0

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
            rows = [row for row in rows if row.get("status") in {"error", "timeout", "fail"}]

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
            "error_rows": sum(1 for row in rows if row.get("status") in {"error", "timeout", "fail"}),
            "warning_rows": 0,
            "last_refresh": datetime.now(timezone.utc).isoformat(),
        }
