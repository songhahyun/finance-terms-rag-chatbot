from __future__ import annotations

from collections import defaultdict


class HybridRetriever:
    def __init__(self, dense_retriever, bm25_retriever, *, k: int = 5, rrf_k: int = 60):
        """Initialize a hybrid retriever with dense and sparse backends.
        Store reciprocal-rank-fusion parameters for later merging."""
        self.dense_retriever = dense_retriever
        self.bm25_retriever = bm25_retriever
        self.k = k
        self.rrf_k = rrf_k

    def invoke(self, query: str):
        """Retrieve documents from both backends and merge the rankings.
        Return the top results after reciprocal rank fusion."""
        dense_docs = self.dense_retriever.invoke(query)
        bm25_docs = self.bm25_retriever.invoke(query)
        ranked = self._rrf_merge([dense_docs, bm25_docs])
        return ranked[: self.k]

    def _rrf_merge(self, ranked_lists: list[list]):
        """Fuse multiple ranked result lists with reciprocal rank scoring.
        Deduplicate documents by chunk id while keeping the strongest order."""
        scores = defaultdict(float)
        id_to_doc = {}
        for docs in ranked_lists:
            for rank, doc in enumerate(docs, start=1):
                chunk_id = doc.metadata.get("chunk_id")
                if chunk_id is None:
                    continue
                id_to_doc[chunk_id] = doc
                scores[chunk_id] += 1.0 / (self.rrf_k + rank)
        sorted_ids = sorted(scores, key=scores.get, reverse=True)
        return [id_to_doc[cid] for cid in sorted_ids]
