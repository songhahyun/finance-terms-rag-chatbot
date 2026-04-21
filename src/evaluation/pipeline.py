from __future__ import annotations

from pathlib import Path

import pandas as pd
from tqdm.auto import tqdm

from src.common.config import get_settings
from src.common.schema import load_chunks
from src.evaluation.metrics import bertscore_f1, hit_score, parse_golden_ids, recall_score
from src.generation.llm import OllamaGenerator
from src.generation.rag_pipeline import RAGPipeline
from src.retrieval.factory import build_retriever


def _build_reference_lookup(chunk_json_path: str | Path) -> dict[str, str]:
    chunks = load_chunks(chunk_json_path)
    return {chunk.chunk_id: f"{chunk.term}\n{chunk.description}" for chunk in chunks}


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

    df = pd.read_csv(eval_csv_path, encoding="utf-8-sig")
    ref_lookup = _build_reference_lookup(chunk_json_path)
    rows: list[dict] = []
    predictions: list[str] = []
    references: list[str] = []

    for _, row in tqdm(df.iterrows(), total=len(df), desc="평가 실행"):
        query = row["query"]
        golden_ids = parse_golden_ids(row["chunk_id"])
        result = rag.answer(query)
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
    output_path = Path(output_csv_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return result_df
