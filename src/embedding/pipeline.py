from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from tqdm.auto import tqdm

from src.common.schema import chunks_to_documents, load_chunks
from src.embedding.chroma_builder import create_chroma_store, create_embedding_model


@dataclass
class EmbeddingTarget:
    provider: str
    model_name: str
    collection_name: str
    persist_directory: Path
    sleep_sec: float = 0.5


def add_documents_in_batches(vectorstore, documents: list, *, batch_size: int = 100, sleep_sec: float = 0.5) -> None:
    """Upload documents to the vector store in controlled batches.
    Retry rate-limited requests and update progress as batches succeed."""
    all_ids = [doc.metadata["chunk_id"] for doc in documents]
    pbar = tqdm(total=len(documents), desc="임베딩 적재")
    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i : i + batch_size]
        batch_ids = all_ids[i : i + batch_size]

        retry_count = 0
        while retry_count < 3:
            try:
                vectorstore.add_documents(documents=batch_docs, ids=batch_ids)
                pbar.update(len(batch_docs))
                time.sleep(sleep_sec)
                break
            except Exception as e:  # noqa: BLE001
                if "429" in str(e):
                    retry_count += 1
                    time.sleep(5)
                else:
                    raise
    pbar.close()


def run_embedding(
    chunk_json_path: str | Path,
    targets: list[EmbeddingTarget],
    *,
    batch_size: int = 100,
) -> None:
    """Build embeddings for all chunks across one or more targets.
    Load chunk documents once, then populate each configured vector store."""
    chunks = load_chunks(chunk_json_path)
    docs = chunks_to_documents(chunks)

    for target in targets:
        embedding_fn = create_embedding_model(target.provider, target.model_name)
        vectorstore = create_chroma_store(
            collection_name=target.collection_name,
            persist_directory=target.persist_directory,
            embedding_function=embedding_fn,
        )
        add_documents_in_batches(vectorstore, docs, batch_size=batch_size, sleep_sec=target.sleep_sec)
