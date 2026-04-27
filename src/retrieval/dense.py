from __future__ import annotations

from langchain_chroma import Chroma

from src.embedding.chroma_builder import create_embedding_model


def build_dense_retriever(
    *,
    provider: str,
    model_name: str,
    collection_name: str,
    persist_directory: str,
    k: int = 5,
    fetch_k: int = 20,
    lambda_mult: float = 0.7,
):
    """Build a dense retriever backed by a persisted Chroma collection.
    Configure MMR search so retrieval balances relevance and diversity."""
    embedding_fn = create_embedding_model(provider, model_name)
    store = Chroma(
        collection_name=collection_name,
        collection_metadata={"hnsw:space": "cosine"},
        embedding_function=embedding_fn,
        persist_directory=persist_directory,
    )
    return store.as_retriever(
        search_type="mmr",
        search_kwargs={"k": k, "fetch_k": fetch_k, "lambda_mult": lambda_mult},
    )
