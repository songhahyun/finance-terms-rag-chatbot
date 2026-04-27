from __future__ import annotations

from fastapi import FastAPI

from backend.app.middleware.request_logging import RequestLoggingMiddleware
from backend.app.routers import auth_router, chat_router, health_router, monitor_router


def create_app() -> FastAPI:
    app = FastAPI(title="Finance RAG Chatbot API", version="0.2.0")
    app.add_middleware(RequestLoggingMiddleware)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(chat_router)
    app.include_router(monitor_router)
    return app


app = create_app()
