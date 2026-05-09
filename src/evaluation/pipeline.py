from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
from tqdm.auto import tqdm

from src.common.config import get_settings
from src.evaluation.metrics import hit_score, measure_retrieval_latency, mrr_score, parse_golden_ids, recall_score
from src.generation.context import build_context
from src.generation.llm import OllamaGenerator
from src.generation.rag_pipeline import RAGPipeline
from src.retrieval.factory import build_retriever


_LOCAL_HF_MODEL_NAME = "BAAI/bge-m3"


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


def _default_dense_variants() -> list[dict[str, str]]:
    """Return default embedding variants for dense/hybrid retrieval experiments."""
    settings = get_settings()
    return [
        {
            "provider": "openai",
            "model_name": "text-embedding-3-small",
            "collection_name": "docs_openai",
            "persist_directory": str(settings.chroma_openai_dir),
        },
        {
            "provider": "clova",
            "model_name": "bge-m3",
            "collection_name": "docs_clova",
            "persist_directory": str(settings.chroma_clova_dir),
        },
        {
            "provider": "local",
            "model_name": _LOCAL_HF_MODEL_NAME,
            "collection_name": "docs_local",
            "persist_directory": str(settings.chroma_local_dir),
        },
    ]


def run_retriever_comparison_evaluation(
    *,
    eval_csv_path: str | Path,
    chunk_json_path: str | Path,
    output_csv_path: str | Path,
    output_summary_csv_path: str | Path | None = None,
    k: int = 5,
    dense_variants: list[dict[str, str]] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run retrieval-only comparison across bm25, dense, and hybrid retrievers.
    Dense and hybrid are evaluated with openai/clova/local embedding variants."""
    eval_df = pd.read_csv(eval_csv_path, encoding="utf-8-sig")
    dense_variants = dense_variants or _default_dense_variants()

    experiments: list[dict[str, Any]] = [{"mode": "bm25"}]
    for variant in dense_variants:
        experiments.append({"mode": "dense", **variant})
        experiments.append({"mode": "hybrid", **variant})

    rows: list[dict[str, Any]] = []

    for exp in experiments:
        mode = exp["mode"]
        provider = exp.get("provider")
        model_name = _resolve_dense_model_name(provider, exp.get("model_name"))
        collection_name = exp.get("collection_name")
        persist_directory = exp.get("persist_directory")
        _require_hf_token_for_local(provider)

        if mode == "bm25":
            exp_label = "bm25"
        else:
            exp_label = f"{mode}:{provider}:{model_name}"

        retriever = build_retriever(
            mode=mode,
            dense_provider=provider or "clova",
            dense_model_name=model_name,
            dense_collection_name=collection_name or "docs_clova",
            dense_persist_directory=persist_directory,
            chunk_json_path=str(chunk_json_path),
            k=k,
        )

        for _, row in tqdm(eval_df.iterrows(), total=len(eval_df), desc=f"Retrieval eval [{exp_label}]"):
            query = row["query"]
            golden_ids = parse_golden_ids(row["chunk_id"])
            docs, query_latency_sec = measure_retrieval_latency(retriever.invoke, query)
            retrieved_ids = [doc.metadata.get("chunk_id") for doc in docs]

            rows.append(
                {
                    "experiment": exp_label,
                    "mode": mode,
                    "dense_provider": provider,
                    "dense_model_name": model_name,
                    "dense_collection_name": collection_name,
                    "query": query,
                    "golden_ids": golden_ids,
                    "retrieved_ids": retrieved_ids,
                    "hit": hit_score(retrieved_ids, golden_ids),
                    "recall": recall_score(retrieved_ids, golden_ids),
                    "mrr": mrr_score(retrieved_ids, golden_ids),
                    "query_latency_sec": query_latency_sec,
                }
            )

    detail_df = pd.DataFrame(rows)
    summary_df = (
        detail_df.groupby(
            ["experiment", "mode", "dense_provider", "dense_model_name", "dense_collection_name"],
            dropna=False,
            as_index=False,
        )[["hit", "recall", "mrr", "query_latency_sec"]]
        .mean()
        .rename(columns={"query_latency_sec": "avg_query_latency_sec"})
    )

    output_path = Path(output_csv_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    detail_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    if output_summary_csv_path:
        summary_path = Path(output_summary_csv_path)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")

    print("\nRetriever comparison summary")
    for _, s_row in summary_df.iterrows():
        print(
            f"[{s_row['experiment']}] "
            f"hit={s_row['hit']:.4f}, recall={s_row['recall']:.4f}, mrr={s_row['mrr']:.4f}, "
            f"avg_latency={s_row['avg_query_latency_sec']:.4f}s"
        )

    return detail_df, summary_df


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
    weave_log_contexts: bool = True,
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
    )
    rag = RAGPipeline(
        retriever=retriever,
        generator=generator,
    )
    df = pd.read_csv(eval_csv_path, encoding="utf-8-sig")
    rows: list[dict[str, Any]] = []

    log_generation_case = None
    log_generation_summary = None
    if use_weave:
        weave = _load_weave()
        weave.init(weave_project or os.getenv("WEAVE_PROJECT", "finance-terms-rag-generation"))

        @weave.op()
        def _log_generation_case(record: dict[str, Any]) -> dict[str, Any]:
            return record

        @weave.op()
        def _log_generation_summary(summary: dict[str, Any]) -> dict[str, Any]:
            return summary

        log_generation_case = _log_generation_case
        log_generation_summary = _log_generation_summary

    experiment_config = {
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
        "k": k,
        "language": language,
    }

    for row_index, (_, row) in enumerate(tqdm(df.iterrows(), total=len(df), desc=f"Generation [{experiment_name}]")):
        query = str(row["query"])
        golden_ids = parse_golden_ids(row["chunk_id"])

        docs, stage_1_retrieval_latency_sec = measure_retrieval_latency(rag.retriever.invoke, query)
        retrieved_ids = [doc.metadata.get("chunk_id") for doc in docs]

        context = build_context(docs)
        answer_prompt = rag._build_answer_prompt(query, context, language=language)
        stage_2_generation_answer, stage_2_generation_latency_sec = measure_retrieval_latency(
            rag._generate_text,
            rag.generator,
            answer_prompt,
        )

        total_latency_sec = stage_1_retrieval_latency_sec + stage_2_generation_latency_sec

        result = {
            "experiment": experiment_name,
            "retrieval_mode": retrieval_mode,
            "dense_provider": dense_provider,
            "dense_model_name": resolved_dense_model_name,
            "dense_collection_name": dense_collection_name,
            "row_index": int(row_index),
            "query": query,
            "golden_ids": golden_ids,
            "retrieved_ids": retrieved_ids,
            "hit": hit_score(retrieved_ids, golden_ids),
            "recall": recall_score(retrieved_ids, golden_ids),
            "mrr": mrr_score(retrieved_ids, golden_ids),
            "stage_1_retrieval_latency_sec": stage_1_retrieval_latency_sec,
            "stage_2_generation_answer": stage_2_generation_answer,
            "stage_2_generation_latency_sec": stage_2_generation_latency_sec,
            "total_latency_sec": total_latency_sec,
        }
        rows.append(result)

        if log_generation_case is not None:
            weave_record = {**experiment_config, **result}
            if weave_log_contexts:
                weave_record["contexts"] = _serialize_docs(docs)
            log_generation_case(weave_record)

    result_df = pd.DataFrame(rows)

    if output_csv_path is not None:
        output_path = Path(output_csv_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    avg_recall = float(result_df["recall"].mean()) if not result_df.empty else 0.0
    avg_mrr = float(result_df["mrr"].mean()) if not result_df.empty else 0.0
    avg_total_latency = float(result_df["total_latency_sec"].mean()) if not result_df.empty else 0.0
    if log_generation_summary is not None:
        summary = {
            **experiment_config,
            "rows": len(result_df),
            "avg_hit": float(result_df["hit"].mean()) if not result_df.empty else 0.0,
            "avg_recall": avg_recall,
            "avg_mrr": avg_mrr,
            "avg_stage_1_retrieval_latency_sec": (
                float(result_df["stage_1_retrieval_latency_sec"].mean()) if not result_df.empty else 0.0
            ),
            "avg_stage_2_generation_latency_sec": (
                float(result_df["stage_2_generation_latency_sec"].mean()) if not result_df.empty else 0.0
            ),
            "avg_total_latency_sec": avg_total_latency,
        }
        log_generation_summary(summary)
    print(
        f"[{experiment_name}] recall={avg_recall:.4f}, mrr={avg_mrr:.4f}, avg_total_latency_sec={avg_total_latency:.4f}"
    )
    return result_df
