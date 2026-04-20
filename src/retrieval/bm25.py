from __future__ import annotations

from langchain_community.retrievers import BM25Retriever

from src.common.schema import chunks_to_documents, load_chunks


def build_bm25_retriever(chunk_json_path: str, *, k: int = 5):
    chunks = load_chunks(chunk_json_path)
    docs = chunks_to_documents(chunks)
    retriever = BM25Retriever.from_documents(docs)
    retriever.k = k
    return retriever

