from __future__ import annotations

import asyncio
from dataclasses import dataclass
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, MagicMock

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "retrieval" / "hybrid.py"
SPEC = importlib.util.spec_from_file_location("hybrid_retriever_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
HybridRetriever = MODULE.HybridRetriever


@dataclass
class FakeDocument:
    page_content: str
    metadata: dict[str, str]


def _doc(chunk_id: str) -> FakeDocument:
    return FakeDocument(page_content=chunk_id, metadata={"chunk_id": chunk_id})


class HybridRetrieverTests(unittest.TestCase):
    def test_ainvoke_runs_concurrently_and_preserves_rrf_results(self) -> None:
        started = asyncio.Event()
        arrival_count = 0
        dense_docs = [_doc("shared"), _doc("dense-only")]
        bm25_docs = [_doc("bm25-only"), _doc("shared")]

        async def retrieve(docs: list[FakeDocument]) -> list[FakeDocument]:
            nonlocal arrival_count
            arrival_count += 1
            if arrival_count == 2:
                started.set()
            await asyncio.wait_for(started.wait(), timeout=1)
            return docs

        dense = MagicMock()
        dense.ainvoke.side_effect = lambda query: retrieve(dense_docs)
        bm25 = MagicMock()
        bm25.ainvoke.side_effect = lambda query: retrieve(bm25_docs)

        result = asyncio.run(HybridRetriever(dense, bm25, k=3).ainvoke("기준금리"))

        self.assertEqual(
            [doc.metadata["chunk_id"] for doc in result],
            ["shared", "bm25-only", "dense-only"],
        )
        dense.ainvoke.assert_called_once_with("기준금리")
        bm25.ainvoke.assert_called_once_with("기준금리")

    def test_ainvoke_propagates_backend_failures(self) -> None:
        for failing_backend in ("dense", "bm25"):
            with self.subTest(failing_backend=failing_backend):
                dense = MagicMock()
                dense.ainvoke = AsyncMock(return_value=[_doc("dense")])
                bm25 = MagicMock()
                bm25.ainvoke = AsyncMock(return_value=[_doc("bm25")])
                backend = dense if failing_backend == "dense" else bm25
                async def fail(query: str) -> list[FakeDocument]:
                    raise RuntimeError(f"{failing_backend} failed")
                backend.ainvoke.side_effect = fail

                with self.assertRaisesRegex(RuntimeError, f"{failing_backend} failed"):
                    asyncio.run(HybridRetriever(dense, bm25).ainvoke("기준금리"))


if __name__ == "__main__":
    unittest.main()
