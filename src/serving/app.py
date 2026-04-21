from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.common.config import get_settings
from src.generation.llm import OllamaGenerator
from src.generation.rag_pipeline import RAGPipeline
from src.retrieval.factory import build_retriever


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    mode: str = Field(default="hybrid")
    k: int = Field(default=5, ge=1, le=20)


class ChatResponse(BaseModel):
    question: str
    answer: str
    retrieved_ids: list[str | None]


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Finance RAG Chatbot API", version="0.1.0")
    state: dict = {"pipelines": {}}

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
        generator = OllamaGenerator(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            timeout=settings.ollama_timeout,
        )
        pipeline = RAGPipeline(retriever, generator)
        state["pipelines"][key] = pipeline
        return pipeline

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/chat", response_model=ChatResponse)
    def chat(req: ChatRequest) -> ChatResponse:
        pipeline = get_pipeline(req.mode, req.k)
        result = pipeline.answer(req.question)
        return ChatResponse(
            question=req.question,
            answer=result["answer"],
            retrieved_ids=result["retrieved_ids"],
        )

    return app


app = create_app()
