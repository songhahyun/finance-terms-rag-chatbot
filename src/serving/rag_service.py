from __future__ import annotations

from dataclasses import dataclass
from queue import Queue
from threading import Lock, Thread
from typing import Any, Callable

from src.common.config import get_settings
from src.generation.llm import OllamaGenerator
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

    def __init__(self) -> None:
        settings = get_settings()
        self._settings = settings
        self._monitor = PipelineMonitor(
            max_history=1000,
            log_path=settings.monitor_stage_log_path,
        )
        self._pipelines: dict[tuple[str, int], RAGPipeline] = {}
        self._lock = Lock()

    def _build_pipeline(self, mode: str, k: int) -> RAGPipeline:
        retriever = build_retriever(
            mode=mode,
            dense_provider="clova",
            dense_model_name="bge-m3",
            dense_collection_name="docs_clova",
            dense_persist_directory=str(self._settings.chroma_clova_dir),
            chunk_json_path=str(self._settings.default_chunk_json_path),
            k=k,
        )
        keyword_extractor = OllamaGenerator(
            model=self._settings.ollama_small_model,
            base_url=self._settings.ollama_base_url,
            timeout=self._settings.ollama_timeout,
        )
        complexity_classifier = OllamaGenerator(
            model=self._settings.ollama_small_model,
            base_url=self._settings.ollama_base_url,
            timeout=self._settings.ollama_timeout,
        )
        simple_generator = OllamaGenerator(
            model=self._settings.ollama_small_model,
            base_url=self._settings.ollama_base_url,
            timeout=self._settings.ollama_timeout,
        )
        complex_generator = OllamaGenerator(
            model=self._settings.ollama_complex_model,
            base_url=self._settings.ollama_base_url,
            timeout=self._settings.ollama_timeout,
        )
        return RAGPipeline(
            retriever,
            keyword_extractor=keyword_extractor,
            complexity_classifier=complexity_classifier,
            simple_generator=simple_generator,
            complex_generator=complex_generator,
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
            "retrieved_ids": result.get("retrieved_ids", []),
            "sources": sources,
            "keywords": result.get("keywords", []),
            "query_type": result.get("query_type"),
            "route_reason": result.get("route_reason"),
            "router_target": result.get("router_target"),
            "monitoring": result.get("monitoring"),
        }

    def answer(self, request: RAGRequest, *, on_chunk: Callable[[str], None] | None = None) -> dict[str, Any]:
        pipeline = self.get_pipeline(request.mode, request.k)
        result = pipeline.answer(
            request.question,
            language=request.language,
            on_chunk=on_chunk,
        )
        return self._serialize_result(request.question, result)

    def monitor_summary(self) -> dict[str, Any]:
        return self._monitor.summary()

    def monitor_recent(self, limit: int = 20) -> dict[str, Any]:
        return {"items": self._monitor.recent(limit=limit)}


_SERVICE = RAGService()


def get_rag_service() -> RAGService:
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
    return _SERVICE.answer(request, on_chunk=on_chunk)


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

