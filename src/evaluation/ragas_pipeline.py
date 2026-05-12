from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Any

import pandas as pd
from tqdm.auto import tqdm

from src.common.io import load_json

_DEFAULT_WEAVE_PROJECT = "finance-terms-rag-evaluation"
_RAGAS_WEAVE_STAGE = "ragas"
_RAGAS_WEAVE_SCHEMA_VERSION = "ragas_v1"


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


def _create_judge_embeddings(model_name: str):
    """Create embeddings for RAGAS metrics.
    Use OpenAI for OpenAI model names and HuggingFace for local sentence-transformer names."""
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
    judge_embedding_model: str = "text-embedding-3-small",
    use_weave: bool = False,
    weave_project: str | None = None,
    weave_experiment_group: str | None = None,
    weave_experiment_name: str | None = None,
    weave_log_contexts: bool = True,
    weave_print_call_link: bool = False,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Run RAGAS evaluation from a generated-answer CSV.
    Save detailed scores and return both row-level data and summary means."""
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
    }

    for _, row in tqdm(
        generated_df.iterrows(),
        total=len(generated_df),
        desc=f"RAGAS evaluation [{experiment_name}]",
    ):
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

    ragas_dataset = Dataset.from_list(
        [
            {
                "question": rec["question"],
                "answer": rec["answer"],
                "contexts": rec["contexts"],
                "ground_truth": rec["ground_truth"],
            }
            for rec in records
        ]
    )

    judge_llm = ChatOpenAI(model=judge_model, temperature=0)
    judge_embeddings = _create_judge_embeddings(judge_embedding_model)
    result = evaluate(
        dataset=ragas_dataset,
        metrics=[answer_relevancy, faithfulness, context_precision, context_recall],
        llm=LangchainLLMWrapper(judge_llm),
        embeddings=LangchainEmbeddingsWrapper(judge_embeddings),
    )

    score_df = result.to_pandas()
    metric_columns = ["answer_relevancy", "faithfulness", "context_precision", "context_recall"]
    output_df = generated_df.reset_index(drop=True).copy()
    record_df = pd.DataFrame(records)
    if "contexts" not in output_df.columns:
        output_df["contexts"] = record_df["contexts"]
    if "ground_truth" not in output_df.columns:
        output_df["ground_truth"] = record_df["ground_truth"]
    for column in metric_columns:
        output_df[column] = score_df[column].reset_index(drop=True)
    summary = {
        "answer_relevancy": float(output_df["answer_relevancy"].mean()),
        "faithfulness": float(output_df["faithfulness"].mean()),
        "context_precision": float(output_df["context_precision"].mean()),
        "context_recall": float(output_df["context_recall"].mean()),
    }

    if log_ragas_case is not None:
        for index, (record, score_row) in enumerate(zip(records, score_df.to_dict("records"), strict=True)):
            case_record = {
                **experiment_config,
                "row_index": index,
                "question": record["question"],
                "answer": record["answer"],
                "ground_truth": record["ground_truth"],
                "retrieved_ids": record["retrieved_ids"],
                "golden_ids": record["golden_ids"],
                **{column: float(score_row[column]) for column in metric_columns},
            }
            if "question_id" in generated_df.columns:
                case_record["question_id"] = str(generated_df.iloc[index]["question_id"])
            if weave_log_contexts:
                case_record["contexts"] = record["contexts"]
            log_ragas_case(case_record)

    if log_ragas_summary is not None:
        log_ragas_summary(
            {
                **experiment_config,
                "rows": len(output_df),
                **{f"avg_{key}": value for key, value in summary.items()},
            }
        )

    output_path = Path(output_csv_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    if output_summary_path:
        summary_path = Path(output_summary_path)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([summary]).to_csv(summary_path, index=False, encoding="utf-8-sig")

    return output_df, summary
