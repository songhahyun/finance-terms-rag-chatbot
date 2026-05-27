from __future__ import annotations

import chromadb
from langchain_chroma import Chroma

from src.embedding.chroma_builder import create_embedding_model


def build_dense_retriever(
    *,
    provider: str,
    model_name: str,
    collection_name: str,
    client_mode: str = "http",
    persist_directory: str | None = None,
    chroma_host: str = "chroma",
    chroma_port: int = 8000,
    chroma_ssl: bool = False,
    k: int = 5,
    fetch_k: int = 20,
    lambda_mult: float = 0.7,
):
    """Build a dense retriever backed by HTTP or local-persistent Chroma."""
    embedding_fn = create_embedding_model(provider, model_name)
    client_mode = client_mode.lower()
    if client_mode == "http":
        client = chromadb.HttpClient(host=chroma_host, port=chroma_port, ssl=chroma_ssl)
        store = Chroma(
            collection_name=collection_name,
            collection_metadata={"hnsw:space": "cosine"},
            embedding_function=embedding_fn,
            client=client,
        )
    elif client_mode == "persistent":
        if not persist_directory:
            raise ValueError("persist_directory is required when CHROMA_CLIENT_MODE=persistent")
        store = Chroma(
            collection_name=collection_name,
            collection_metadata={"hnsw:space": "cosine"},
            embedding_function=embedding_fn,
            persist_directory=persist_directory,
        )
    else:
        raise ValueError("CHROMA_CLIENT_MODE must be one of: http, persistent")
    return store.as_retriever(
        search_type="mmr",
        search_kwargs={"k": k, "fetch_k": fetch_k, "lambda_mult": lambda_mult},
    )
