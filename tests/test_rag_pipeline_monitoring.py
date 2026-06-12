from __future__ import annotations

from src.generation.rag_pipeline import RAGPipeline
from src.monitor import PipelineMonitor


class _Doc:
    page_content = "기준금리 설명"
    metadata = {"chunk_id": "chunk-1", "source": "source.pdf"}


class _Generator:
    def generate(self, prompt: str, **kwargs) -> str:
        return "기준금리 답변입니다."


class _SplitRetriever:
    def __init__(self, *, bm25_docs: list | None = None, dense_docs: list | None = None, fused_docs: list | None = None) -> None:
        self.bm25_docs = bm25_docs if bm25_docs is not None else []
        self.dense_docs = dense_docs if dense_docs is not None else []
        self.fused_docs = fused_docs if fused_docs is not None else []

    def retrieve_bm25(self, query: str) -> list:
        return self.bm25_docs

    def retrieve_dense(self, query: str) -> list:
        return self.dense_docs

    def fuse(self, *, dense_docs: list, bm25_docs: list) -> list:
        return self.fused_docs


def _stage_by_name(result: dict, stage: str) -> dict:
    return next(item for item in result["monitoring"]["stages"] if item["stage"] == stage)


def test_retrieval_empty_results_mark_monitor_failures_without_raising() -> None:
    monitor = PipelineMonitor(log_path=None)
    pipeline = RAGPipeline(_SplitRetriever(), generator=_Generator(), monitor=monitor)

    result = pipeline.answer("기준금리란?", language="ko")

    assert result["answer"] == "기준금리 답변입니다."
    assert result["retrieved_ids"] == []

    bm25 = _stage_by_name(result, "stage_1_retrieval_bm25")
    dense = _stage_by_name(result, "stage_1_retrieval_dense")
    fusion = _stage_by_name(result, "stage_1_retrieval_fusion")

    assert bm25["success"] is False
    assert dense["success"] is False
    assert fusion["success"] is False
    assert bm25["throughput_unit"] == "calls/sec"
    assert dense["throughput_unit"] == "calls/sec"
    assert fusion["throughput_unit"] == "calls/sec"
    assert bm25["work_units"] == 1.0
    assert dense["work_units"] == 1.0
    assert fusion["work_units"] == 1.0


def test_fusion_success_depends_on_parent_retrieval_results() -> None:
    monitor = PipelineMonitor(log_path=None)
    pipeline = RAGPipeline(
        _SplitRetriever(bm25_docs=[_Doc()], dense_docs=[], fused_docs=[]),
        generator=_Generator(),
        monitor=monitor,
    )

    result = pipeline.answer("기준금리란?", language="ko")

    assert _stage_by_name(result, "stage_1_retrieval_bm25")["success"] is True
    assert _stage_by_name(result, "stage_1_retrieval_dense")["success"] is False
    assert _stage_by_name(result, "stage_1_retrieval_fusion")["success"] is True
