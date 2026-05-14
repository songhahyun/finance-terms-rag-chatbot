from __future__ import annotations

import ast
import logging
import os
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from src.common.io import load_json

_DEFAULT_WEAVE_PROJECT = "finance-terms-rag-evaluation"
_RAGAS_WEAVE_STAGE = "ragas"
_RAGAS_WEAVE_SCHEMA_VERSION = "ragas_v1"
_RAGAS_GENERATION_WARNING = "LLM returned 1 generations instead of requested 3"


class _RagasGenerationWarningFilter(logging.Filter):
    """Suppress a noisy RAGAS warning that does not stop evaluation."""

    def filter(self, record: logging.LogRecord) -> bool:
        return _RAGAS_GENERATION_WARNING not in record.getMessage()


def _suppress_ragas_generation_warning() -> None:
    """Hide RAGAS self-consistency generation-count warnings once per process."""
    logger = logging.getLogger("ragas.prompt.pydantic_prompt")
    if any(isinstance(log_filter, _RagasGenerationWarningFilter) for log_filter in logger.filters):
        return
    logger.addFilter(_RagasGenerationWarningFilter())


def _iter_exception_tree(exc: BaseException):
    """Yield nested exceptions from chained errors and Python 3.11 exception groups."""
    yield exc
    for nested in getattr(exc, "exceptions", []) or []:
        yield from _iter_exception_tree(nested)
    if exc.__cause__ is not None:
        yield from _iter_exception_tree(exc.__cause__)
    if exc.__context__ is not None:
        yield from _iter_exception_tree(exc.__context__)


def _is_rate_limit_error(exc: BaseException) -> bool:
    """Detect OpenAI/LangChain/RAGAS rate-limit failures without binding to one SDK class."""
    for nested in _iter_exception_tree(exc):
        text = str(nested).lower()
        if nested.__class__.__name__ == "RateLimitError":
            return True
        if getattr(nested, "status_code", None) == 429:
            return True
        if "rate limit" in text or "rate_limit_exceeded" in text:
            return True
    return False


def _retry_after_seconds(exc: BaseException) -> float | None:
    """Read an API retry hint when it is present in headers or the error message."""
    for nested in _iter_exception_tree(exc):
        response = getattr(nested, "response", None)
        headers = getattr(response, "headers", None)
        if headers:
            retry_after = headers.get("retry-after") or headers.get("Retry-After")
            if retry_after:
                try:
                    return float(retry_after)
                except ValueError:
                    pass

        match = re.search(r"try again in ([0-9.]+)s", str(nested), flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def _has_complete_metrics(output_df: pd.DataFrame, row_index: int, metric_columns: list[str]) -> bool:
    """Return True when a row already has all RAGAS metrics from a previous run."""
    return all(column in output_df.columns and not pd.isna(output_df.at[row_index, column]) for column in metric_columns)


def _parse_id_list(raw_value: Any) -> list[str]:
    """Normalize evaluation ids into a consistent string list.
    Accept list objects, serialized lists, or scalar values."""
    if isinstance(raw_value, list):
        return [str(v) for v in raw_value]
    if isinstance(raw_value, str):
        if raw_value.startswith("["):
            try:
                parsed = ast.literal_eval(raw_value)
                if isinstance(parsed, list):
                    return [str(v) for v in parsed]
            except (SyntaxError, ValueError):
                pass
        return [raw_value]
    return [str(raw_value)]


def _parse_contexts(raw_value: Any) -> list[str]:
    """Normalize serialized context records from generated CSV outputs."""
    if isinstance(raw_value, list):
        values = raw_value
    elif isinstance(raw_value, str) and raw_value.startswith("["):
        try:
            parsed = ast.literal_eval(raw_value)
            values = parsed if isinstance(parsed, list) else [raw_value]
        except (SyntaxError, ValueError):
            values = [raw_value]
    elif pd.isna(raw_value):
        values = []
    else:
        values = [str(raw_value)]

    contexts: list[str] = []
    for value in values:
        if isinstance(value, dict):
            contexts.append(str(value.get("text") or value.get("page_content") or ""))
        else:
            contexts.append(str(value))
    return [context for context in contexts if context]


def _read_chunk_fields(item: dict[str, Any]) -> tuple[str, str]:
    """Read term and description fields from a chunk record.
    Support both Korean source keys and normalized English keys."""
    term = str(item.get("\uc6a9\uc5b4") or item.get("term") or "")
    description = str(item.get("\uc124\uba85") or item.get("description") or "")
    return term, description


def _build_chunk_text_lookup(chunk_json_path: str | Path) -> dict[str, str]:
    """Build a chunk-id lookup for RAGAS context and ground-truth text.
    Skip rows that do not provide a usable chunk identifier."""
    rows = load_json(chunk_json_path)
    lookup: dict[str, str] = {}
    for row in rows:
        chunk_id = str(row.get("chunk_id", "")).strip()
        if not chunk_id:
            continue
        term, description = _read_chunk_fields(row)
        lookup[chunk_id] = f"{term}\n{description}".strip()
    return lookup


def _get_required_text(row: pd.Series, candidates: tuple[str, ...], label: str) -> str:
    """Read a required text field from one of several compatible column names."""
    for column in candidates:
        if column in row and not pd.isna(row[column]):
            return str(row[column])
    raise KeyError(f"Generated CSV is missing required {label} column. Tried: {', '.join(candidates)}")


@lru_cache(maxsize=4)
def _create_judge_embeddings(model_name: str):
    """Create embeddings for RAGAS metrics.
    Use OpenAI for OpenAI model names and HuggingFace for local sentence-transformer names.
    Cache the client so repeated experiment loops do not reload the same model weights."""
    if model_name.startswith("text-embedding-"):
        from langchain_openai import OpenAIEmbeddings  # noqa: PLC0415

        return OpenAIEmbeddings(model=model_name)

    from langchain_huggingface import HuggingFaceEmbeddings  # noqa: PLC0415

    hf_model_name = {
        "multilingual-e5-large": "intfloat/multilingual-e5-large",
    }.get(model_name, model_name)
    return HuggingFaceEmbeddings(model_name=hf_model_name)


def _load_weave():
    """Import Weave only when experiment logging has been explicitly enabled."""
    try:
        import weave
    except ImportError as exc:
        raise ImportError("Weave is not installed. Run `pip install weave` or `pip install -r requirements.txt`.") from exc
    return weave


def run_ragas_evaluation(
    *,
    generated_csv_path: str | Path,
    chunk_json_path: str | Path,
    output_csv_path: str | Path,
    output_summary_path: str | Path | None = None,
    judge_model: str = "gpt-4o-mini",
    judge_embedding_model: str = "multilingual-e5-large",
    max_rows: int | None = None,
    use_weave: bool = False,
    weave_project: str | None = None,
    weave_experiment_group: str | None = None,
    weave_experiment_name: str | None = None,
    weave_log_contexts: bool = True,
    weave_print_call_link: bool = False,
    rate_limit_max_retries: int = 20,
    rate_limit_sleep_seconds: float = 10.0,
    rate_limit_max_sleep_seconds: float = 120.0,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Run RAGAS evaluation from a generated-answer CSV.
    Save detailed scores and return both row-level data and summary means."""
    _suppress_ragas_generation_warning()
    try:
        from datasets import Dataset  # noqa: PLC0415
        from langchain_openai import ChatOpenAI  # noqa: PLC0415
        from ragas import evaluate  # noqa: PLC0415
        from ragas.embeddings import LangchainEmbeddingsWrapper  # noqa: PLC0415
        from ragas.llms import LangchainLLMWrapper  # noqa: PLC0415
        from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError("RAGAS evaluation dependencies are missing. Run `pip install -r requirements.txt`.") from exc

    generated_df = pd.read_csv(generated_csv_path, encoding="utf-8-sig")
    if max_rows is not None:
        if max_rows <= 0:
            raise ValueError("`max_rows` must be a positive integer when provided.")
        generated_df = generated_df.head(max_rows).copy()
    chunk_lookup = _build_chunk_text_lookup(chunk_json_path)
    records: list[dict[str, Any]] = []
    experiment_name = weave_experiment_name or Path(generated_csv_path).stem

    log_ragas_case = None
    log_ragas_summary = None
    if use_weave:
        weave = _load_weave()
        weave.init(
            weave_project or os.getenv("WEAVE_PROJECT", _DEFAULT_WEAVE_PROJECT),
            settings={
                "print_call_link": weave_print_call_link,
                "implicitly_patch_integrations": False,
            },
            attributes={
                "experiment_group": weave_experiment_group,
                "experiment": experiment_name,
                "stage": _RAGAS_WEAVE_STAGE,
                "schema_version": _RAGAS_WEAVE_SCHEMA_VERSION,
            },
        )

        @weave.op()
        def _log_ragas_case(record: dict[str, Any]) -> dict[str, Any]:
            return record

        @weave.op()
        def _log_ragas_summary(summary_record: dict[str, Any]) -> dict[str, Any]:
            return summary_record

        log_ragas_case = _log_ragas_case
        log_ragas_summary = _log_ragas_summary

    experiment_config = {
        "stage": _RAGAS_WEAVE_STAGE,
        "schema_version": _RAGAS_WEAVE_SCHEMA_VERSION,
        "experiment_group": weave_experiment_group,
        "experiment": experiment_name,
        "generated_csv_path": str(generated_csv_path),
        "chunk_json_path": str(chunk_json_path),
        "judge_model": judge_model,
        "judge_embedding_model": judge_embedding_model,
        "max_rows": max_rows,
        "rate_limit_max_retries": rate_limit_max_retries,
        "rate_limit_sleep_seconds": rate_limit_sleep_seconds,
        "rate_limit_max_sleep_seconds": rate_limit_max_sleep_seconds,
    }

    for _, row in generated_df.iterrows():
        question = _get_required_text(row, ("query", "question"), "question")
        answer = _get_required_text(row, ("stage_2_generation_answer", "answer"), "answer")
        golden_ids = _parse_id_list(row["golden_ids"] if "golden_ids" in row else row["chunk_id"])
        retrieved_ids = _parse_id_list(row["retrieved_ids"]) if "retrieved_ids" in row else []
        contexts = _parse_contexts(row["contexts"]) if "contexts" in row else []
        if not contexts:
            contexts = [chunk_lookup.get(chunk_id, "") for chunk_id in retrieved_ids]
            contexts = [context for context in contexts if context]
        ground_truth = (
            "" if "ground_truth" not in row or pd.isna(row["ground_truth"]) else str(row["ground_truth"])
        )
        if not ground_truth:
            ground_truth = "\n\n".join(chunk_lookup.get(cid, "") for cid in golden_ids).strip()

        records.append(
            {
                "question": question,
                "answer": answer,
                "contexts": contexts,
                "ground_truth": ground_truth,
                "retrieved_ids": retrieved_ids,
                "golden_ids": golden_ids,
            }
        )

    print(f"[INFO] {Path(generated_csv_path).name} {len(records)} rows loading complete")

    judge_llm = ChatOpenAI(model=judge_model, temperature=0)
    judge_embeddings = _create_judge_embeddings(judge_embedding_model)
    metric_columns = ["answer_relevancy", "faithfulness", "context_precision", "context_recall"]
    output_df = generated_df.reset_index(drop=True).copy()
    record_df = pd.DataFrame(records)
    if "contexts" not in output_df.columns:
        output_df["contexts"] = record_df["contexts"]
    if "ground_truth" not in output_df.columns:
        output_df["ground_truth"] = record_df["ground_truth"]

    output_path = Path(output_csv_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        existing_df = pd.read_csv(output_path, encoding="utf-8-sig")
        if len(existing_df) == len(output_df):
            for column in [*metric_columns, "contexts", "ground_truth"]:
                if column in existing_df.columns:
                    output_df[column] = existing_df[column]
            completed_rows = sum(_has_complete_metrics(output_df, idx, metric_columns) for idx in range(len(output_df)))
            if completed_rows:
                print(f"[INFO] Resuming from {output_path}: {completed_rows}/{len(output_df)} rows already scored")
        else:
            print(
                f"[WARN] Ignoring existing output with different row count: "
                f"{output_path} ({len(existing_df)} != {len(output_df)})"
            )

    ragas_llm = LangchainLLMWrapper(judge_llm)
    ragas_embeddings = LangchainEmbeddingsWrapper(judge_embeddings)
    metrics = [answer_relevancy, faithfulness, context_precision, context_recall]

    for row_index, record in enumerate(records):
        if _has_complete_metrics(output_df, row_index, metric_columns):
            continue

        row_attempt = 0
        while True:
            try:
                row_dataset = Dataset.from_list(
                    [
                        {
                            "question": record["question"],
                            "answer": record["answer"],
                            "contexts": record["contexts"],
                            "ground_truth": record["ground_truth"],
                        }
                    ]
                )
                result = evaluate(
                    dataset=row_dataset,
                    metrics=metrics,
                    llm=ragas_llm,
                    embeddings=ragas_embeddings,
                    raise_exceptions=True,
                    batch_size=1,
                    show_progress=False,
                )
                score_row = result.to_pandas().iloc[0]
                for column in metric_columns:
                    output_df.at[row_index, column] = score_row[column]

                if log_ragas_case is not None:
                    case_record = {
                        **experiment_config,
                        "row_index": row_index,
                        "question": record["question"],
                        "answer": record["answer"],
                        "ground_truth": record["ground_truth"],
                        "retrieved_ids": record["retrieved_ids"],
                        "golden_ids": record["golden_ids"],
                        **{column: float(score_row[column]) for column in metric_columns},
                    }
                    if "question_id" in generated_df.columns:
                        case_record["question_id"] = str(generated_df.iloc[row_index]["question_id"])
                    if weave_log_contexts:
                        case_record["contexts"] = record["contexts"]
                    log_ragas_case(case_record)

                output_df.to_csv(output_path, index=False, encoding="utf-8-sig")
                print(f"[INFO] RAGAS row {row_index + 1}/{len(records)} saved")
                break
            except Exception as exc:
                if not _is_rate_limit_error(exc):
                    raise
                row_attempt += 1
                if row_attempt > rate_limit_max_retries:
                    raise RuntimeError(
                        f"Rate limit persisted at row {row_index + 1} after {rate_limit_max_retries} retries"
                    ) from exc
                retry_hint = _retry_after_seconds(exc)
                exponential_sleep = rate_limit_sleep_seconds * (2 ** (row_attempt - 1))
                sleep_seconds = min(rate_limit_max_sleep_seconds, max(exponential_sleep, (retry_hint or 0.0) + 1.0))
                print(
                    f"[WARN] Rate limit at row {row_index + 1}/{len(records)} "
                    f"({row_attempt}/{rate_limit_max_retries}). Sleeping {sleep_seconds:.1f}s then retrying."
                )
                time.sleep(sleep_seconds)

    summary = {
        "answer_relevancy": float(output_df["answer_relevancy"].mean()),
        "faithfulness": float(output_df["faithfulness"].mean()),
        "context_precision": float(output_df["context_precision"].mean()),
        "context_recall": float(output_df["context_recall"].mean()),
    }

    if log_ragas_summary is not None:
        log_ragas_summary(
            {
                **experiment_config,
                "rows": len(output_df),
                **{f"avg_{key}": value for key, value in summary.items()},
            }
        )
    output_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    if output_summary_path:
        summary_path = Path(output_summary_path)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([summary]).to_csv(summary_path, index=False, encoding="utf-8-sig")

    return output_df, summary


def run_ragas_evaluations(
    *,
    generated_csv_paths: list[str | Path],
    chunk_json_path: str | Path,
    output_dir: str | Path,
    output_summary_path: str | Path,
    judge_model: str = "gpt-4o-mini",
    judge_embedding_model: str = "multilingual-e5-large",
    max_rows: int | None = None,
    use_weave: bool = False,
    weave_project: str | None = None,
    weave_experiment_group: str | None = None,
    weave_log_contexts: bool = True,
    weave_print_call_link: bool = False,
    rate_limit_max_retries: int = 20,
    rate_limit_sleep_seconds: float = 10.0,
    rate_limit_max_sleep_seconds: float = 120.0,
) -> tuple[dict[str, Path], pd.DataFrame]:
    """Run RAGAS over one or more generated CSV files.
    Write one detail CSV per experiment and a single combined summary CSV."""
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    detail_outputs: dict[str, Path] = {}
    summary_rows: list[dict[str, Any]] = []

    for generated_csv_path in generated_csv_paths:
        generated_path = Path(generated_csv_path)
        experiment_name = generated_path.stem
        detail_output_path = output_root / f"{experiment_name}_ragas.csv"

        output_df, summary = run_ragas_evaluation(
            generated_csv_path=generated_path,
            chunk_json_path=chunk_json_path,
            output_csv_path=detail_output_path,
            output_summary_path=None,
            judge_model=judge_model,
            judge_embedding_model=judge_embedding_model,
            max_rows=max_rows,
            use_weave=use_weave,
            weave_project=weave_project,
            weave_experiment_group=weave_experiment_group,
            weave_experiment_name=experiment_name,
            weave_log_contexts=weave_log_contexts,
            weave_print_call_link=weave_print_call_link,
            rate_limit_max_retries=rate_limit_max_retries,
            rate_limit_sleep_seconds=rate_limit_sleep_seconds,
            rate_limit_max_sleep_seconds=rate_limit_max_sleep_seconds,
        )

        detail_outputs[experiment_name] = detail_output_path
        summary_rows.append(
            {
                "experiment": experiment_name,
                "rows": len(output_df),
                **summary,
                "detail_output_path": str(detail_output_path),
            }
        )

    summary_df = pd.DataFrame(summary_rows)
    summary_path = Path(output_summary_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")

    return detail_outputs, summary_df
