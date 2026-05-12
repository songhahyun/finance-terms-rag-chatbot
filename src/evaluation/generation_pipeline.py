from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
from tqdm.auto import tqdm

from src.common.config import get_settings
from src.evaluation.metrics import (
    bertscore_f1,
    hit_score,
    measure_retrieval_latency,
    mrr_score,
    parse_golden_ids,
    recall_score,
)
from src.generation.context import build_context
from src.generation.llm import OllamaGenerator
from src.generation.rag_pipeline import RAGPipeline
from src.retrieval.factory import build_retriever


_LOCAL_HF_MODEL_NAME = "BAAI/bge-m3"
_DEFAULT_WEAVE_PROJECT = "finance-terms-rag-evaluation"
_GENERATION_WEAVE_STAGE = "generation"
_GENERATION_WEAVE_SCHEMA_VERSION = "generation_v1"


def _resolve_dense_model_name(provider: str | None, model_name: str | None) -> str:
    """Resolve dense embedding model name with local-provider override."""
    if (provider or "").lower() == "local":
        return _LOCAL_HF_MODEL_NAME
    return model_name or "bge-m3"


def _require_hf_token_for_local(provider: str | None) -> None:
    """Validate Hugging Face token availability for local embedding provider."""
    if (provider or "").lower() != "local":
        return
    if os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN"):
        return
    raise ValueError("`dense_provider='local'` requires HF_TOKEN or HUGGING_FACE_HUB_TOKEN in environment.")


def _load_weave():
    """Import Weave only when experiment logging has been explicitly enabled."""
    try:
        import weave
    except ImportError as exc:
        raise ImportError("Weave is not installed. Run `pip install weave` or `pip install -r requirements.txt`.") from exc
    return weave


def _serialize_docs(docs: list) -> list[dict[str, Any]]:
    """Convert retrieved documents into JSON-friendly records for experiment logs."""
    return [
        {
            "chunk_id": doc.metadata.get("chunk_id"),
            "source": doc.metadata.get("source"),
            "text": doc.page_content,
        }
        for doc in docs
    ]


def _measure_generation_retrieval_stages(
    retriever,
    query: str,
    retrieval_mode: str,
) -> tuple[list, dict[str, float]]:
    """Measure retrieval latency using split hybrid stages when available."""
    latencies = {
        "stage_1_retrieval_bm25_latency_sec": 0.0,
        "stage1_1_retrieval_dense_latency_sec": 0.0,
        "stage_1_retrieval_fusion_latency_sec": 0.0,
    }

    retrieval_mode = retrieval_mode.lower()

    if retrieval_mode == "hybrid" and all(hasattr(retriever, name) for name in ("retrieve_bm25", "retrieve_dense", "fuse")):
        bm25_docs, latencies["stage_1_retrieval_bm25_latency_sec"] = measure_retrieval_latency(
            retriever.retrieve_bm25,
            query,
        )
        dense_docs, latencies["stage1_1_retrieval_dense_latency_sec"] = measure_retrieval_latency(
            retriever.retrieve_dense,
            query,
        )
        docs, latencies["stage_1_retrieval_fusion_latency_sec"] = measure_retrieval_latency(
            retriever.fuse,
            dense_docs=dense_docs,
            bm25_docs=bm25_docs,
        )
        return docs, latencies

    if retrieval_mode == "dense":
        docs, latencies["stage1_1_retrieval_dense_latency_sec"] = measure_retrieval_latency(retriever.invoke, query)
        return docs, latencies

    if retrieval_mode == "bm25":
        docs, latencies["stage_1_retrieval_bm25_latency_sec"] = measure_retrieval_latency(retriever.invoke, query)
        return docs, latencies

    docs, latencies["stage_1_retrieval_fusion_latency_sec"] = measure_retrieval_latency(retriever.invoke, query)
    return docs, latencies


def run_generation_experiment(
    *,
    experiment_name: str,
    eval_csv_path: str | Path,
    chunk_json_path: str | Path,
    retrieval_mode: str = "hybrid",
    dense_provider: str = "clova",
    dense_model_name: str = "bge-m3",
    dense_collection_name: str = "docs_clova",
    dense_persist_directory: str | None = None,
    bm25_index_path: str | Path | None = None,
    output_csv_path: str | Path | None = None,
    ollama_model: str | None = None,
    ollama_base_url: str | None = None,
    ollama_timeout: int | None = None,
    k: int = 5,
    language: str | None = None,
    use_weave: bool = False,
    weave_project: str | None = None,
    weave_experiment_group: str | None = None,
    weave_log_contexts: bool = True,
    weave_log_prompt: bool = True,
    weave_print_call_link: bool = False,
) -> pd.DataFrame:
    """Run one stage-wise generation experiment and return per-row result DataFrame.
    Use one fixed answer generator for every query.
    When `use_weave` is true, log each case and aggregate metrics to W&B Weave."""
    settings = get_settings()
    resolved_dense_model_name = _resolve_dense_model_name(dense_provider, dense_model_name)
    _require_hf_token_for_local(dense_provider)

    retriever = build_retriever(
        mode=retrieval_mode,
        dense_provider=dense_provider,
        dense_model_name=resolved_dense_model_name,
        dense_collection_name=dense_collection_name,
        dense_persist_directory=dense_persist_directory,
        chunk_json_path=str(chunk_json_path),
        bm25_index_path=str(bm25_index_path) if bm25_index_path is not None else None,
        k=k,
    )
    generator = OllamaGenerator(
        model=ollama_model or settings.ollama_model,
        base_url=ollama_base_url or settings.ollama_base_url,
        timeout=ollama_timeout or settings.ollama_timeout,
        temperature=settings.ollama_temperature,
        top_p=settings.ollama_top_p,
        repeat_penalty=settings.ollama_repeat_penalty,
        keep_alive=settings.ollama_keep_alive,
    )
    rag = RAGPipeline(
        retriever=retriever,
        generator=generator,
    )
    df = pd.read_csv(eval_csv_path, encoding="utf-8-sig")
    rows: list[dict[str, Any]] = []
    weave_extras: list[dict[str, Any]] = []

    log_generation_case = None
    log_generation_summary = None
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
                "stage": _GENERATION_WEAVE_STAGE,
                "schema_version": _GENERATION_WEAVE_SCHEMA_VERSION,
            },
        )

        @weave.op()
        def _log_generation_case(record: dict[str, Any]) -> dict[str, Any]:
            return record

        @weave.op()
        def _log_generation_summary(summary: dict[str, Any]) -> dict[str, Any]:
            return summary

        log_generation_case = _log_generation_case
        log_generation_summary = _log_generation_summary

    experiment_config = {
        "stage": _GENERATION_WEAVE_STAGE,
        "schema_version": _GENERATION_WEAVE_SCHEMA_VERSION,
        "experiment_group": weave_experiment_group,
        "experiment": experiment_name,
        "retrieval_mode": retrieval_mode,
        "dense_provider": dense_provider,
        "dense_model_name": resolved_dense_model_name,
        "dense_collection_name": dense_collection_name,
        "dense_persist_directory": dense_persist_directory,
        "chunk_json_path": str(chunk_json_path),
        "bm25_index_path": str(bm25_index_path) if bm25_index_path is not None else None,
        "ollama_model": ollama_model or settings.ollama_model,
        "ollama_base_url": ollama_base_url or settings.ollama_base_url,
        "ollama_temperature": settings.ollama_temperature,
        "ollama_top_p": settings.ollama_top_p,
        "ollama_repeat_penalty": settings.ollama_repeat_penalty,
        "ollama_keep_alive": settings.ollama_keep_alive,
        "k": k,
        "language": language,
    }

    for _, row in tqdm(df.iterrows(), total=len(df), desc=f"Generation [{experiment_name}]"):
        question_id = str(row["question_id"])
        query = str(row["query"])
        golden_ids = parse_golden_ids(row["chunk_id"])
        ground_truth = "" if pd.isna(row.get("ground_truth", "")) else str(row.get("ground_truth", ""))

        docs, retrieval_latencies = _measure_generation_retrieval_stages(rag.retriever, query, retrieval_mode)
        retrieved_ids = [doc.metadata.get("chunk_id") for doc in docs]

        context = build_context(docs)
        answer_prompt = rag._build_answer_prompt(query, context, language=language)
        stage_2_generation_answer, stage_2_generation_latency_sec = measure_retrieval_latency(
            rag._generate_text,
            rag.generator,
            answer_prompt,
        )

        total_retrieval_latency_sec = sum(retrieval_latencies.values())
        total_latency_sec = total_retrieval_latency_sec + stage_2_generation_latency_sec

        result = {
            "experiment": experiment_name,
            "retrieval_mode": retrieval_mode,
            "dense_provider": dense_provider,
            "dense_model_name": resolved_dense_model_name,
            "dense_collection_name": dense_collection_name,
            "question_id": question_id,
            "query": query,
            "ground_truth": ground_truth,
            "golden_ids": golden_ids,
            "retrieved_ids": retrieved_ids,
            "hit": hit_score(retrieved_ids, golden_ids),
            "recall": recall_score(retrieved_ids, golden_ids),
            "mrr": mrr_score(retrieved_ids, golden_ids),
            **retrieval_latencies,
            "stage_1_retrieval_total_latency_sec": total_retrieval_latency_sec,
            "stage_2_generation_answer": stage_2_generation_answer,
            "stage_2_generation_latency_sec": stage_2_generation_latency_sec,
            "total_latency_sec": total_latency_sec,
        }
        rows.append(result)

        if log_generation_case is not None:
            weave_extra = {}
            if weave_log_prompt:
                weave_extra["stage_2_generation_prompt"] = answer_prompt
            if weave_log_contexts:
                weave_extra["contexts"] = _serialize_docs(docs)
            weave_extras.append(weave_extra)

    bert_scores = bertscore_f1(
        [str(row["stage_2_generation_answer"]) for row in rows],
        [str(row["ground_truth"]) for row in rows],
        lang="ko",
    )
    for row, bert_score in zip(rows, bert_scores, strict=True):
        row["bertscore_f1"] = bert_score

    if log_generation_case is not None:
        for result, weave_extra in zip(rows, weave_extras, strict=True):
            log_generation_case({**experiment_config, **result, **weave_extra})

    result_df = pd.DataFrame(rows)

    if output_csv_path is not None:
        output_path = Path(output_csv_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    avg_recall = float(result_df["recall"].mean()) if not result_df.empty else 0.0
    avg_mrr = float(result_df["mrr"].mean()) if not result_df.empty else 0.0
    avg_bertscore_f1 = float(result_df["bertscore_f1"].mean()) if not result_df.empty else 0.0
    avg_total_latency = float(result_df["total_latency_sec"].mean()) if not result_df.empty else 0.0
    if log_generation_summary is not None:
        summary = {
            **experiment_config,
            "rows": len(result_df),
            "avg_hit": float(result_df["hit"].mean()) if not result_df.empty else 0.0,
            "avg_recall": avg_recall,
            "avg_mrr": avg_mrr,
            "avg_bertscore_f1": avg_bertscore_f1,
            "avg_stage_1_retrieval_total_latency_sec": (
                float(result_df["stage_1_retrieval_total_latency_sec"].mean()) if not result_df.empty else 0.0
            ),
            "avg_stage_1_retrieval_bm25_latency_sec": (
                float(result_df["stage_1_retrieval_bm25_latency_sec"].mean()) if not result_df.empty else 0.0
            ),
            "avg_stage1_1_retrieval_dense_latency_sec": (
                float(result_df["stage1_1_retrieval_dense_latency_sec"].mean()) if not result_df.empty else 0.0
            ),
            "avg_stage_1_retrieval_fusion_latency_sec": (
                float(result_df["stage_1_retrieval_fusion_latency_sec"].mean()) if not result_df.empty else 0.0
            ),
            "avg_stage_2_generation_latency_sec": (
                float(result_df["stage_2_generation_latency_sec"].mean()) if not result_df.empty else 0.0
            ),
            "avg_total_latency_sec": avg_total_latency,
        }
        log_generation_summary(summary)
    print(
        f"[{experiment_name}] recall={avg_recall:.4f}, mrr={avg_mrr:.4f}, "
        f"bertscore_f1={avg_bertscore_f1:.4f}, avg_total_latency_sec={avg_total_latency:.4f}"
    )
    return result_df
