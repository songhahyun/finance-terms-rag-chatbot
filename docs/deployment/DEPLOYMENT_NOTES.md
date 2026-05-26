## Current Generation Flow

- Backend entrypoint: `backend/app/main.py` creates the FastAPI app, registers CORS and request logging middleware, and includes the health, auth, chat, knowledge document, and monitor routers.
- RAG service: `src/serving/rag_service.py` owns the shared `RAGService`, builds retrievers with `src.retrieval.factory.build_retriever`, and wraps them in `src.generation.rag_pipeline.RAGPipeline`.
- Current generator: `src.generation.llm.OllamaGenerator` is instantiated directly in `RAGService._build_pipeline()` with Ollama settings.
- Current settings source: `src.common.config.get_settings()` loads project settings from environment variables and the root `.env`; `backend.app.config.get_backend_settings()` separately loads auth/JWT settings for the FastAPI layer.
- Chat endpoint: `backend/app/routers/chat.py` exposes `POST /chat` and `POST /chat/stream`, both protected by `get_current_user`, and calls `answer_query()` or `stream_answer()` from `src.serving.rag_service`.
