from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pandas as pd
from tqdm.auto import tqdm

from src.common.config import get_settings
from src.common.io import load_json
from src.generation.llm import OllamaGenerator
from src.generation.rag_pipeline import RAGPipeline
from src.retrieval.factory import build_retriever


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


def _read_chunk_fields(item: dict[str, Any]) -> tuple[str, str]:
    """Read term and description fields from a chunk record.
    Support both Korean source keys and normalized English keys."""
    term = str(item.get("\uc6a9\uc5b4") or item.get("term") or "")
    description = str(item.get("\uc124\uba85") or item.get("description") or "")
    return term, description


def _build_reference_lookup(chunk_json_path: str | Path) -> dict[str, str]:
    """Build a chunk-id lookup for RAGAS ground-truth text.
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


def run_ragas_evaluation(
    *,
    eval_csv_path: str | Path,
    chunk_json_path: str | Path,
    output_csv_path: str | Path,
    output_summary_path: str | Path | None = None,
    retrieval_mode: str = "hybrid",
    ollama_model: str | None = None,
    ollama_base_url: str | None = None,
    ollama_timeout: int | None = None,
    dense_provider: str = "clova",
    dense_model_name: str = "bge-m3",
    dense_collection_name: str = "docs_clova",
    dense_persist_directory: str | None = None,
    k: int = 5,
    judge_model: str = "gpt-4o-mini",
    judge_embedding_model: str = "text-embedding-3-small",
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Run a RAGAS-based evaluation workflow on the test set.
    Save detailed scores and return both row-level data and summary means."""
    try:
        from datasets import Dataset  # noqa: PLC0415
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings  # noqa: PLC0415
        from ragas import evaluate  # noqa: PLC0415
        from ragas.embeddings import LangchainEmbeddingsWrapper  # noqa: PLC0415
        from ragas.llms import LangchainLLMWrapper  # noqa: PLC0415
        from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError("RAGAS evaluation dependencies are missing. Run `pip install -r requirements.txt`.") from exc

    settings = get_settings()
    retriever = build_retriever(
        mode=retrieval_mode,
        dense_provider=dense_provider,
        dense_model_name=dense_model_name,
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

    eval_df = pd.read_csv(eval_csv_path, encoding="utf-8-sig")
    ref_lookup = _build_reference_lookup(chunk_json_path)
    records: list[dict[str, Any]] = []

    for _, row in tqdm(eval_df.iterrows(), total=len(eval_df), desc="RAGAS evaluation"):
        question = str(row["query"])
        golden_ids = _parse_id_list(row["chunk_id"])
        result = rag.answer(question)

        contexts = [doc.page_content for doc in result["contexts"]]
        ground_truth = "\n\n".join(ref_lookup.get(cid, "") for cid in golden_ids).strip()

        records.append(
            {
                "question": question,
                "answer": result["answer"],
                "contexts": contexts,
                "ground_truth": ground_truth,
                "retrieved_ids": result["retrieved_ids"],
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
    judge_embeddings = OpenAIEmbeddings(model=judge_embedding_model)
    result = evaluate(
        dataset=ragas_dataset,
        metrics=[answer_relevancy, faithfulness, context_precision, context_recall],
        llm=LangchainLLMWrapper(judge_llm),
        embeddings=LangchainEmbeddingsWrapper(judge_embeddings),
    )

    score_df = result.to_pandas()
    output_df = pd.concat([pd.DataFrame(records), score_df], axis=1)
    summary = {
        "answer_relevancy": float(output_df["answer_relevancy"].mean()),
        "faithfulness": float(output_df["faithfulness"].mean()),
        "context_precision": float(output_df["context_precision"].mean()),
        "context_recall": float(output_df["context_recall"].mean()),
    }

    output_path = Path(output_csv_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    if output_summary_path:
        summary_path = Path(output_summary_path)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([summary]).to_csv(summary_path, index=False, encoding="utf-8-sig")

    return output_df, summary
