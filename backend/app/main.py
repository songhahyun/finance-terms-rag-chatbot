from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.middleware.request_logging import RequestLoggingMiddleware
from backend.app.routers import auth_router, chat_router, health_router, monitor_router


def create_app() -> FastAPI:
    """Create the FastAPI application for the backend service.
    Register middleware and API routers in one place."""
    app = FastAPI(title="Finance RAG Chatbot API", version="0.2.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(chat_router)
    app.include_router(monitor_router)
    return app


app = create_app()
