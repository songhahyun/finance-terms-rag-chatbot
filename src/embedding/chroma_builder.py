from __future__ import annotations

from pathlib import Path

from langchain_chroma import Chroma


def create_embedding_model(provider: str, model_name: str):
    provider = provider.lower()
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings  # noqa: PLC0415

        return OpenAIEmbeddings(model=model_name)
    if provider == "clova":
        from langchain_naver import ClovaXEmbeddings  # noqa: PLC0415

        return ClovaXEmbeddings(model=model_name)
    if provider == "local":
        from langchain_huggingface import HuggingFaceEmbeddings  # noqa: PLC0415

        return HuggingFaceEmbeddings(model_name=model_name)
    raise ValueError(f"지원하지 않는 provider: {provider}")


def create_chroma_store(
    *,
    collection_name: str,
    persist_directory: str | Path,
    embedding_function,
) -> Chroma:
    return Chroma(
        collection_name=collection_name,
        collection_metadata={"hnsw:space": "cosine"},
        embedding_function=embedding_function,
        persist_directory=str(persist_directory),
    )

