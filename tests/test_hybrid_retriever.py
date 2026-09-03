from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
from threading import Barrier
import unittest
from unittest.mock import MagicMock

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
    def test_invoke_runs_concurrently_and_preserves_rrf_results(self) -> None:
        started = Barrier(2, timeout=1)
        dense_docs = [_doc("shared"), _doc("dense-only")]
        bm25_docs = [_doc("bm25-only"), _doc("shared")]

        def retrieve(docs: list[FakeDocument]) -> list[FakeDocument]:
            started.wait()
            return docs

        dense = MagicMock()
        dense.invoke.side_effect = lambda query: retrieve(dense_docs)
        bm25 = MagicMock()
        bm25.invoke.side_effect = lambda query: retrieve(bm25_docs)

        result = HybridRetriever(dense, bm25, k=3).invoke("기준금리")

        self.assertEqual(
            [doc.metadata["chunk_id"] for doc in result],
            ["shared", "bm25-only", "dense-only"],
        )
        dense.invoke.assert_called_once_with("기준금리")
        bm25.invoke.assert_called_once_with("기준금리")

    def test_invoke_propagates_backend_failures(self) -> None:
        for failing_backend in ("dense", "bm25"):
            with self.subTest(failing_backend=failing_backend):
                dense = MagicMock()
                dense.invoke.return_value = [_doc("dense")]
                bm25 = MagicMock()
                bm25.invoke.return_value = [_doc("bm25")]
                backend = dense if failing_backend == "dense" else bm25
                backend.invoke.side_effect = RuntimeError(f"{failing_backend} failed")

                with self.assertRaisesRegex(RuntimeError, f"{failing_backend} failed"):
                    HybridRetriever(dense, bm25).invoke("기준금리")


if __name__ == "__main__":
    unittest.main()
