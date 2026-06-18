from __future__ import annotations

from pathlib import Path

from src.generation.query_intent import ClassifierMethod, QueryIntent, QueryIntentResult
from src.monitor import PipelineMonitor
from src.serving import rag_service
from src.serving.rag_service import RAGRequest, RAGService


class _FakeClassifier:
    def __init__(self, result: QueryIntentResult) -> None:
        self.result = result
        self.calls = 0

    def classify(self, query: str) -> QueryIntentResult:
        self.calls += 1
        return self.result


class _FakeDoc:
    page_content = "가산금리\n\n문서 내용"
    metadata = {"chunk_id": "chunk-1", "source": "source.pdf", "term": "가산금리", "related_terms": "금리, 대출금리"}


class _FakePipeline:
    def __init__(self) -> None:
        self.calls = 0
        self.trace = None

    def answer(self, question: str, *, language: str, on_chunk=None, trace=None):
        self.calls += 1
        self.trace = trace
        if on_chunk is not None:
            on_chunk("rag-token")
        return {
            "answer": "RAG 답변",
            "retrieved_ids": ["chunk-1"],
            "contexts": [_FakeDoc()],
            "monitoring": trace.to_dict() if trace is not None else {"trace_id": "trace"},
        }


class _ServiceWithFakePipeline(RAGService):
    def __init__(self, *, intent_classifier, monitor: PipelineMonitor | None = None) -> None:
        super().__init__(intent_classifier=intent_classifier, monitor=monitor or PipelineMonitor(log_path=None))
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
    assert result["monitoring"]["metadata"]["intent"] == "simple"
    assert result["monitoring"]["stages"][0]["stage"] == "stage_0_intent_classification"
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
    assert result["sources"][0]["term"] == "가산금리"
    assert result["sources"][0]["explanation"] == "문서 내용"
    assert result["sources"][0]["related_terms"] == ["금리", "대출금리"]
    assert result["intent"] == "needs_rag"
    assert result["matched_terms"] == ["가산금리"]
    assert result["monitoring"]["metadata"]["intent"] == "needs_rag"
    assert result["monitoring"]["stages"][0]["stage"] == "stage_0_intent_classification"
    assert service.pipeline_builds == 1
    assert service.pipeline.calls == 1
    assert service.pipeline.trace is not None


def test_service_monitor_recent_exposes_classifier_stage() -> None:
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

    service.answer(RAGRequest(question="안녕?"))
    recent = service.monitor_recent(limit=1)

    item = recent["items"][0]
    assert item["metadata"]["intent"] == "simple"
    assert item["metadata"]["routing_reason"] == "matched_greeting"
    assert item["metadata"]["classifier_method"] == "rule"
    assert item["metadata"]["confidence"] == 1.0
    assert item["stages"][0]["stage"] == "stage_0_intent_classification"


def test_service_monitor_log_includes_classifier_metadata(tmp_path: Path) -> None:
    classifier = _FakeClassifier(
        QueryIntentResult(
            intent=QueryIntent.SIMPLE,
            confidence=1.0,
            reason="matched_greeting",
            classifier_method=ClassifierMethod.RULE,
            fixed_answer="안녕하세요.",
        )
    )
    log_path = tmp_path / "stage_monitor.log"
    service = _ServiceWithFakePipeline(
        intent_classifier=classifier,
        monitor=PipelineMonitor(log_path=log_path),
    )

    service.answer(RAGRequest(question="안녕?"))

    log_text = log_path.read_text(encoding="utf-8")
    assert "stage_0_intent_classification" in log_text
    assert "'intent': 'simple'" in log_text
    assert "'routing_reason': 'matched_greeting'" in log_text


def test_stream_answer_final_payload_includes_routing_metadata(monkeypatch) -> None:
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
    monkeypatch.setattr(rag_service, "_SERVICE", service)

    queue, result_holder, error_holder = rag_service.stream_answer("안녕?")

    chunks = []
    while True:
        item = queue.get(timeout=5)
        if item is None:
            break
        chunks.append(item)

    assert chunks == ["안녕하세요."]
    assert error_holder == {}
    final = result_holder["result"]
    assert final["intent"] == "simple"
    assert final["routing_reason"] == "matched_greeting"
    assert final["matched_terms"] == []
    assert final["classifier"] == {"method": "rule", "confidence": 1.0}
