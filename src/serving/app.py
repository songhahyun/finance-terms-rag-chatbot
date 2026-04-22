from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.common.config import get_settings
from src.generation.llm import OllamaGenerator
from src.generation.rag_pipeline import RAGPipeline
from src.monitor import PipelineMonitor
from src.retrieval.factory import build_retriever


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    mode: str = Field(default="hybrid")
    k: int = Field(default=5, ge=1, le=20)
    language: str = Field(default="ko", pattern="^(ko|en)$")


class SourceItem(BaseModel):
    chunk_id: str | None
    source: str | None
    text: str


class ChatResponse(BaseModel):
    question: str
    answer: str
    retrieved_ids: list[str | None]
    sources: list[SourceItem]


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Finance RAG Chatbot API", version="0.1.0")
    state: dict = {
        "pipelines": {},
        "monitor": PipelineMonitor(
            max_history=1000,
            log_path=settings.monitor_stage_log_path,
        ),
    }

    def get_pipeline(mode: str, k: int) -> RAGPipeline:
        key = (mode, k)
        if key in state["pipelines"]:
            return state["pipelines"][key]
        retriever = build_retriever(
            mode=mode,
            dense_provider="clova",
            dense_model_name="bge-m3",
            dense_collection_name="docs_clova",
            dense_persist_directory=str(settings.chroma_clova_dir),
            chunk_json_path=str(settings.default_chunk_json_path),
            k=k,
        )
        keyword_extractor = OllamaGenerator(
            model=settings.ollama_small_model,
            base_url=settings.ollama_base_url,
            timeout=settings.ollama_timeout,
        )
        complexity_classifier = OllamaGenerator(
            model=settings.ollama_small_model,
            base_url=settings.ollama_base_url,
            timeout=settings.ollama_timeout,
        )
        simple_generator = OllamaGenerator(
            model=settings.ollama_small_model,
            base_url=settings.ollama_base_url,
            timeout=settings.ollama_timeout,
        )
        complex_generator = OllamaGenerator(
            model=settings.ollama_complex_model,
            base_url=settings.ollama_base_url,
            timeout=settings.ollama_timeout,
        )
        pipeline = RAGPipeline(
            retriever,
            keyword_extractor=keyword_extractor,
            complexity_classifier=complexity_classifier,
            simple_generator=simple_generator,
            complex_generator=complex_generator,
            monitor=state["monitor"],
        )
        state["pipelines"][key] = pipeline
        return pipeline

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/monitor/summary")
    def monitor_summary() -> dict:
        return state["monitor"].summary()

    @app.get("/monitor/recent")
    def monitor_recent(limit: int = 20) -> dict:
        return {"items": state["monitor"].recent(limit=limit)}

    @app.post("/chat", response_model=ChatResponse)
    def chat(req: ChatRequest) -> ChatResponse:
        pipeline = get_pipeline(req.mode, req.k)
        result = pipeline.answer(req.question, language=req.language)
        sources = [
            SourceItem(
                chunk_id=doc.metadata.get("chunk_id"),
                source=doc.metadata.get("source"),
                text=doc.page_content,
            )
            for doc in result["contexts"]
        ]
        return ChatResponse(
            question=req.question,
            answer=result["answer"],
            retrieved_ids=result["retrieved_ids"],
            sources=sources,
        )

    return app


app = create_app()
