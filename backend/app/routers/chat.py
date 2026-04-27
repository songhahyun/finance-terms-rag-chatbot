from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from backend.app.auth.deps import get_current_user
from backend.app.schemas.auth import AuthenticatedUser
from backend.app.schemas.chat import ChatRequest, ChatResponse
from src.serving.rag_service import answer_query, stream_answer

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> ChatResponse:
    result = answer_query(
        request.question,
        mode=request.mode,
        k=request.k,
        language=request.language,
    )
    return ChatResponse(**result)


@router.post("/stream")
def chat_stream(
    request: ChatRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> StreamingResponse:
    queue, result_holder, error_holder = stream_answer(
        request.question,
        mode=request.mode,
        k=request.k,
        language=request.language,
    )

    def _iter_chunks():
        while True:
            item = queue.get()
            if item is None:
                break
            yield json.dumps({"type": "token", "content": item}, ensure_ascii=False) + "\n"

        if "error" in error_holder:
            yield json.dumps({"type": "error", "message": error_holder["error"]}, ensure_ascii=False) + "\n"
            return

        yield json.dumps({"type": "final", **result_holder["result"]}, ensure_ascii=False) + "\n"

    return StreamingResponse(_iter_chunks(), media_type="application/x-ndjson")
