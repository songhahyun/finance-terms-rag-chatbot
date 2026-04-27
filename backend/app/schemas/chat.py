from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    mode: str = Field(default="hybrid")
    k: int = Field(default=5, ge=1, le=20)
    language: str = Field(default="ko", pattern="^(ko|en)$")


class SourceItem(BaseModel):
    chunk_id: str | None = None
    source: str | None = None
    text: str


class ChatResponse(BaseModel):
    question: str
    answer: str
    retrieved_ids: list[str | None]
    sources: list[SourceItem]
    keywords: list[str] = []
    query_type: str | None = None
    route_reason: str | None = None
    router_target: str | None = None
