from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
from tqdm.auto import tqdm

from src.common.config import get_settings
from src.common.schema import load_chunks
from src.evaluation.metrics import (
    bertscore_f1,
    hit_score,
    measure_retrieval_latency,
    mrr_score,
    parse_golden_ids,
    recall_score,
)
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


def _build_reference_lookup(chunk_json_path: str | Path) -> dict[str, str]:
    """Build a lookup from chunk id to reference text.
    Combine each term and description into one evaluation target."""
    chunks = load_chunks(chunk_json_path)
    return {chunk.chunk_id: f"{chunk.term}\n{chunk.description}" for chunk in chunks}


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


def run_evaluation(
    *,
    eval_csv_path: str | Path,
    chunk_json_path: str | Path,
    output_csv_path: str | Path,
    retrieval_mode: str = "hybrid",
    ollama_model: str | None = None,
    ollama_base_url: str | None = None,
    ollama_timeout: int | None = None,
    dense_provider: str = "clova",
    dense_model_name: str = "bge-m3",
    dense_collection_name: str = "docs_clova",
    dense_persist_directory: str | None = None,
    k: int = 5,
) -> pd.DataFrame:
    """Run retrieval-and-generation evaluation over a CSV dataset.
    Save per-row metrics and return the aggregated result table."""
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
        k=k,
    )
    generator = OllamaGenerator(
        model=ollama_model or settings.ollama_model,
        base_url=ollama_base_url or settings.ollama_base_url,
        timeout=ollama_timeout or settings.ollama_timeout,
    )
    rag = RAGPipeline(retriever=retriever, generator=generator)

    df = pd.read_csv(eval_csv_path, encoding="utf-8-sig")
    ref_lookup = _build_reference_lookup(chunk_json_path)
    rows: list[dict] = []
    predictions: list[str] = []
    references: list[str] = []

    for _, row in tqdm(df.iterrows(), total=len(df), desc="평가 실행"):
        query = row["query"]
        golden_ids = parse_golden_ids(row["chunk_id"])
        result, query_latency_sec = measure_retrieval_latency(rag.answer, query)
        retrieved_ids = result["retrieved_ids"]
        prediction = result["answer"]
        reference = "\n\n".join(ref_lookup.get(cid, "") for cid in golden_ids).strip()

        rows.append(
            {
                "query": query,
                "golden_ids": golden_ids,
                "retrieved_ids": retrieved_ids,
                "hit": hit_score(retrieved_ids, golden_ids),
                "recall": recall_score(retrieved_ids, golden_ids),
                "mrr": mrr_score(retrieved_ids, golden_ids),
                "query_latency_sec": query_latency_sec,
                "answer": prediction,
                "reference": reference,
            }
        )
        predictions.append(prediction)
        references.append(reference)

    bert_f1 = bertscore_f1(predictions, references, lang="ko")
    for row, f1 in zip(rows, bert_f1):
        row["bert_score_f1"] = f1

    result_df = pd.DataFrame(rows)
    avg_latency = float(result_df["query_latency_sec"].mean()) if not result_df.empty else 0.0
    print(f"Average query latency (sec): {avg_latency:.4f}")
    output_path = Path(output_csv_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return result_df
