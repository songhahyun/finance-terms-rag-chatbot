from __future__ import annotations

from src.generation.query_intent import ClassifierMethod, QueryIntent, QueryIntentResult
from src.monitor import PipelineMonitor
from src.serving.rag_service import RAGRequest, RAGService


class _FakeClassifier:
    def __init__(self, result: QueryIntentResult) -> None:
        self.result = result
        self.calls = 0

    def classify(self, query: str) -> QueryIntentResult:
        self.calls += 1
        return self.result


class _FakeDoc:
    page_content = "문서 내용"
    metadata = {"chunk_id": "chunk-1", "source": "source.pdf"}


class _FakePipeline:
    def __init__(self) -> None:
        self.calls = 0

    def answer(self, question: str, *, language: str, on_chunk=None):
        self.calls += 1
        if on_chunk is not None:
            on_chunk("rag-token")
        return {
            "answer": "RAG 답변",
            "retrieved_ids": ["chunk-1"],
            "contexts": [_FakeDoc()],
            "monitoring": {"trace_id": "trace"},
        }


class _ServiceWithFakePipeline(RAGService):
    def __init__(self, *, intent_classifier) -> None:
        super().__init__(intent_classifier=intent_classifier, monitor=PipelineMonitor(log_path=None))
        self.pipeline = _FakePipeline()
        self.pipeline_builds = 0

    def _build_pipeline(self, mode: str, k: int):
        self.pipeline_builds += 1
        return self.pipeline


def test_service_non_rag_route_does_not_build_pipeline() -> None:
    classifier = _FakeClassifier(
        QueryIntentResult(
            intent=QueryIntent.SIMPLE,
            confidence=1.0,
            reason="matched_greeting",
            classifier_method=ClassifierMethod.RULE,
            fixed_answer="안녕하세요.",
        )
    )
    service = _ServiceWithFakePipeline(intent_classifier=classifier)

    result = service.answer(RAGRequest(question="안녕?"))

    assert result["answer"] == "안녕하세요."
    assert result["retrieved_ids"] == []
    assert result["sources"] == []
    assert result["intent"] == "simple"
    assert service.pipeline_builds == 0
    assert service.pipeline.calls == 0


def test_service_rag_route_uses_existing_pipeline() -> None:
    classifier = _FakeClassifier(
        QueryIntentResult(
            intent=QueryIntent.NEEDS_RAG,
            confidence=1.0,
            reason="matched_finance_terms",
            matched_terms=["가산금리"],
            classifier_method=ClassifierMethod.RULE,
        )
    )
    service = _ServiceWithFakePipeline(intent_classifier=classifier)

    result = service.answer(RAGRequest(question="가산금리란?", k=3))

    assert result["answer"] == "RAG 답변"
    assert result["retrieved_ids"] == ["chunk-1"]
    assert result["sources"][0]["chunk_id"] == "chunk-1"
    assert result["intent"] == "needs_rag"
    assert result["matched_terms"] == ["가산금리"]
    assert service.pipeline_builds == 1
    assert service.pipeline.calls == 1
