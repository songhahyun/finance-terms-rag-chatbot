from __future__ import annotations

from dataclasses import dataclass
from queue import Queue
from threading import Lock, Thread
from typing import Any, Callable

from src.common.config import get_settings
from src.generation.factory import build_generator
from src.generation.openai_provider import OpenAIGenerator
from src.generation.query_intent import (
    DEFAULT_CLARIFICATION_ANSWER,
    QueryIntent,
    QueryIntentClassifier,
    QueryIntentResult,
    RuleBasedQueryClassifier,
    OpenAILLMIntentClassifier,
)
from src.generation.rag_pipeline import RAGPipeline
from src.monitor import PipelineMonitor
from src.retrieval.factory import build_retriever


@dataclass(frozen=True)
class RAGRequest:
    question: str
    mode: str = "hybrid"
    k: int = 5
    language: str = "ko"


class RAGService:
    """Adapter between web entrypoints and the legacy RAG pipeline."""

    def __init__(self, *, intent_classifier: Any | None = None, monitor: PipelineMonitor | None = None) -> None:
        settings = get_settings()
        self._settings = settings
        self._monitor = monitor or PipelineMonitor(
            max_history=1000,
            log_path=settings.monitor_stage_log_path,
        )
        self._pipelines: dict[tuple[str, int], RAGPipeline] = {}
        self._simple_generator: OpenAIGenerator | None = None
        self._intent_classifier = intent_classifier or self._build_intent_classifier()
        self._lock = Lock()

    def _build_intent_classifier(self) -> QueryIntentClassifier:
        dictionary_path = self._settings.processed_data_dir / "kiwi_user_dict.tsv"
        rule_classifier = RuleBasedQueryClassifier(dictionary_path)
        llm_classifier = None
        provider = getattr(self._settings, "intent_classifier_provider", "openai")
        if provider == "openai" and self._settings.openai_api_key:
            llm_classifier = OpenAILLMIntentClassifier(
                api_key=self._settings.openai_api_key,
                model=getattr(self._settings, "intent_classifier_model", "gpt-4.1-mini"),
                timeout=getattr(self._settings, "intent_classifier_timeout", 10),
                confidence_threshold=getattr(self._settings, "intent_classifier_confidence_threshold", 0.7),
            )
        return QueryIntentClassifier(rule_classifier=rule_classifier, llm_classifier=llm_classifier)

    def _build_pipeline(self, mode: str, k: int) -> RAGPipeline:
        retriever = build_retriever(
            mode=mode,
            dense_provider="clova",
            dense_model_name="bge-m3",
            chunk_json_path=str(self._settings.default_chunk_json_path),
            k=k,
        )
        generator = build_generator(self._settings)
        return RAGPipeline(
            retriever,
            generator=generator,
            monitor=self._monitor,
            monitor_stage3_timeout_sec=self._settings.monitor_stage3_timeout_sec,
        )

    def get_pipeline(self, mode: str, k: int) -> RAGPipeline:
        key = (mode.lower(), k)
        with self._lock:
            pipeline = self._pipelines.get(key)
            if pipeline is None:
                pipeline = self._build_pipeline(mode=key[0], k=key[1])
                self._pipelines[key] = pipeline
        return pipeline

    @staticmethod
    def _serialize_result(question: str, result: dict[str, Any]) -> dict[str, Any]:
        sources = [
            {
                "chunk_id": doc.metadata.get("chunk_id"),
                "source": doc.metadata.get("source"),
                "text": doc.page_content,
            }
            for doc in result.get("contexts", [])
        ]
        return {
            "question": question,
            "answer": result.get("answer", ""),
            "regeneration_count": result.get("regeneration_count", 0),
            "language_validation": result.get("language_validation"),
            "retrieved_ids": result.get("retrieved_ids", []),
            "sources": sources,
            "monitoring": result.get("monitoring"),
        }

    def answer(self, request: RAGRequest, *, on_chunk: Callable[[str], None] | None = None) -> dict[str, Any]:
        classification = self._intent_classifier.classify(request.question)
        if classification.intent != QueryIntent.NEEDS_RAG:
            return self._answer_without_rag(request.question, classification, on_chunk=on_chunk)

        pipeline = self.get_pipeline(request.mode, request.k)
        result = pipeline.answer(
            request.question,
            language=request.language,
            on_chunk=on_chunk,
        )
        response = self._serialize_result(request.question, result)
        response.update(classification.routing_metadata())
        return response

    def _answer_without_rag(
        self,
        question: str,
        classification: QueryIntentResult,
        *,
        on_chunk: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        answer = classification.fixed_answer
        if answer is None and classification.intent == QueryIntent.SIMPLE:
            answer = self._answer_simple_with_llm(question)
        if answer is None:
            answer = DEFAULT_CLARIFICATION_ANSWER
        if on_chunk is not None:
            on_chunk(answer)

        response = {
            "question": question,
            "answer": answer,
            "regeneration_count": 0,
            "language_validation": None,
            "retrieved_ids": [],
            "sources": [],
            "monitoring": None,
        }
        response.update(classification.routing_metadata())
        return response

    def _answer_simple_with_llm(self, question: str) -> str:
        if self._simple_generator is None:
            self._simple_generator = OpenAIGenerator(
                api_key=self._settings.openai_api_key,
                model="gpt-4.1-mini",
                temperature=0.1,
                max_tokens=500,
            )
        prompt = (
            "경제·금융 개념을 일반 사용자가 이해하기 쉽게 한국어로 짧게 답하세요.\n"
            f"질문: {question}"
        )
        return self._simple_generator.generate(prompt)

    def monitor_summary(self) -> dict[str, Any]:
        return self._monitor.summary()

    def monitor_recent(self, limit: int = 20) -> dict[str, Any]:
        return {"items": self._monitor.recent(limit=limit)}


_SERVICE: RAGService | None = None


def get_rag_service() -> RAGService:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = RAGService()
    return _SERVICE


def answer_query(
    question: str,
    *,
    mode: str = "hybrid",
    k: int = 5,
    language: str = "ko",
    on_chunk: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    request = RAGRequest(question=question, mode=mode, k=k, language=language)
    return get_rag_service().answer(request, on_chunk=on_chunk)


def stream_answer(
    question: str,
    *,
    mode: str = "hybrid",
    k: int = 5,
    language: str = "ko",
):
    queue: Queue[str | None] = Queue()
    result_holder: dict[str, Any] = {}
    error_holder: dict[str, str] = {}

    def _on_chunk(chunk: str) -> None:
        queue.put(chunk)

    def _worker() -> None:
        try:
            result_holder["result"] = answer_query(
                question,
                mode=mode,
                k=k,
                language=language,
                on_chunk=_on_chunk,
            )
        except Exception as exc:  # noqa: BLE001
            error_holder["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            queue.put(None)

    worker = Thread(target=_worker, daemon=True)
    worker.start()
    return queue, result_holder, error_holder
