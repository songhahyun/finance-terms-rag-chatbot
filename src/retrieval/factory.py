from __future__ import annotations

from src.common.config import get_settings
from src.retrieval.bm25 import build_bm25_retriever
from src.retrieval.dense import build_dense_retriever
from src.retrieval.hybrid import HybridRetriever


def build_retriever(
    mode: str = "hybrid",
    *,
    dense_provider: str = "clova",
    dense_model_name: str = "bge-m3",
    dense_collection_name: str = "docs_clova",
    dense_persist_directory: str | None = None,
    chunk_json_path: str | None = None,
    k: int = 5,
):
    settings = get_settings()
    dense_persist_directory = dense_persist_directory or str(settings.chroma_clova_dir)
    chunk_json_path = chunk_json_path or str(settings.default_chunk_json_path)

    mode = mode.lower()
    if mode == "dense":
        return build_dense_retriever(
            provider=dense_provider,
            model_name=dense_model_name,
            collection_name=dense_collection_name,
            persist_directory=dense_persist_directory,
            k=k,
        )
    if mode == "bm25":
        return build_bm25_retriever(chunk_json_path=chunk_json_path, k=k)
    if mode == "hybrid":
        dense = build_dense_retriever(
            provider=dense_provider,
            model_name=dense_model_name,
            collection_name=dense_collection_name,
            persist_directory=dense_persist_directory,
            k=k,
        )
        bm25 = build_bm25_retriever(chunk_json_path=chunk_json_path, k=k)
        return HybridRetriever(dense, bm25, k=k)
    raise ValueError(f"지원하지 않는 mode: {mode}")

