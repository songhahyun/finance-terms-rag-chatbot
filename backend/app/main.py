from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import get_backend_settings
from backend.app.middleware.request_logging import RequestLoggingMiddleware
from backend.app.routers import auth_router, chat_router, health_router, knowledge_documents_router, monitor_router


def create_app() -> FastAPI:
    """Create the FastAPI application for the backend service.
    Register middleware and API routers in one place."""
    settings = get_backend_settings()
    app = FastAPI(title="Finance RAG Chatbot API", version="0.2.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(chat_router)
    app.include_router(knowledge_documents_router)
    app.include_router(monitor_router)
    return app


app = create_app()
