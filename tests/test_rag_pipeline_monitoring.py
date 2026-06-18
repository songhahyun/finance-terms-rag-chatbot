from __future__ import annotations

from src.generation.rag_pipeline import RAGPipeline
from src.monitor import PipelineMonitor


class _Doc:
    page_content = "기준금리 설명"
    metadata = {"chunk_id": "chunk-1", "source": "source.pdf"}


class _Generator:
    provider = "openai"
    model = "test-model"
    last_usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}

    def generate(self, prompt: str, **kwargs) -> str:
        return "기준금리 답변입니다."


class _OllamaGenerator:
    provider = "ollama"
    model = "llama3.2:3b"
    last_usage = {
        "prompt_eval_count": 850,
        "eval_count": 92,
        "prompt_eval_duration": 7053941000,
        "eval_duration": 3041100000,
        "total_duration": 10195041000,
    }

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


def test_retrieval_empty_results_mark_zero_result_without_raising() -> None:
    monitor = PipelineMonitor(log_path=None)
    pipeline = RAGPipeline(_SplitRetriever(), generator=_Generator(), monitor=monitor)

    result = pipeline.answer("기준금리란?", language="ko")

    assert result["answer"] == "기준금리 답변입니다."
    assert result["retrieved_ids"] == []

    bm25 = _stage_by_name(result, "stage_1_retrieval_bm25")
    dense = _stage_by_name(result, "stage_1_retrieval_dense")
    fusion = _stage_by_name(result, "stage_1_retrieval_fusion")

    assert bm25["success"] is True
    assert dense["success"] is True
    assert fusion["success"] is True
    assert bm25["status"] == "zero_result"
    assert dense["status"] == "zero_result"
    assert fusion["status"] == "zero_result"
    assert bm25["throughput_unit"] == "calls/sec"
    assert dense["throughput_unit"] == "calls/sec"
    assert fusion["throughput_unit"] == "calls/sec"
    assert bm25["attempted_count"] == 1
    assert bm25["success_count"] == 1
    assert bm25["fail_count"] == 0
    assert bm25["result_count"] == 0


def test_fusion_success_depends_on_parent_retrieval_results() -> None:
    monitor = PipelineMonitor(log_path=None)
    pipeline = RAGPipeline(
        _SplitRetriever(bm25_docs=[_Doc()], dense_docs=[], fused_docs=[]),
        generator=_Generator(),
        monitor=monitor,
    )

    result = pipeline.answer("기준금리란?", language="ko")

    assert _stage_by_name(result, "stage_1_retrieval_bm25")["success"] is True
    assert _stage_by_name(result, "stage_1_retrieval_dense")["success"] is True
    assert _stage_by_name(result, "stage_1_retrieval_fusion")["success"] is True


def test_generation_metric_maps_openai_usage() -> None:
    monitor = PipelineMonitor(log_path=None)
    pipeline = RAGPipeline(_SplitRetriever(bm25_docs=[_Doc()], fused_docs=[_Doc()]), generator=_Generator(), monitor=monitor)

    result = pipeline.answer("기준금리란?", language="ko")

    generation = _stage_by_name(result, "stage_2_generation")
    assert generation["stage_type"] == "generation"
    assert generation["provider"] == "openai"
    assert generation["input_tokens"] == 10
    assert generation["output_tokens"] == 5
    assert generation["total_tokens"] == 15
    assert generation["token_count_source"] == "provider_usage"


def test_generation_metric_maps_ollama_usage_and_durations() -> None:
    monitor = PipelineMonitor(log_path=None)
    pipeline = RAGPipeline(_SplitRetriever(bm25_docs=[_Doc()], fused_docs=[_Doc()]), generator=_OllamaGenerator(), monitor=monitor)

    result = pipeline.answer("기준금리란?", language="ko")

    generation = _stage_by_name(result, "stage_2_generation")
    assert generation["provider"] == "ollama"
    assert generation["input_tokens"] == 850
    assert generation["output_tokens"] == 92
    assert generation["total_tokens"] == 942
    assert round(generation["input_tokens_per_sec"], 4) == round(850 / 7.053941, 4)
    assert round(generation["output_tokens_per_sec"], 4) == round(92 / 3.0411, 4)
    assert generation["token_count_source"] == "provider_usage"
