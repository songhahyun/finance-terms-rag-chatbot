from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.auth.rbac import require_roles
from backend.app.schemas.auth import AuthenticatedUser
from src.common.config import get_settings

router = APIRouter(prefix="/knowledge-documents", tags=["knowledge-documents"])


def _as_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _as_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _extract_rows(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("chunks", "documents", "items", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def _normalize_document(row: Any, index: int) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None

    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    term = _as_text(row.get("용어")) or _as_text(row.get("term"))
    explanation = _as_text(row.get("설명")) or _as_text(row.get("explanation")) or _as_text(row.get("text"))
    related_terms = (
        _as_string_list(row.get("연관검색어"))
        or _as_string_list(row.get("relatedTerms"))
        or _as_string_list(row.get("related_terms"))
        or _as_string_list(metadata.get("연관검색어"))
        or _as_string_list(metadata.get("related_terms"))
    )

    if not term or not explanation:
        return None

    return {
        "id": _as_text(row.get("id")) or _as_text(row.get("chunk_id")) or f"knowledge-{index}",
        "term": term,
        "explanation": explanation,
        "relatedTerms": related_terms,
    }


@router.get("")
def list_knowledge_documents(user: AuthenticatedUser = Depends(require_roles("user", "admin"))) -> dict[str, list[dict[str, Any]]]:
    path = get_settings().default_chunk_json_path
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge document file not found: {path}",
        )

    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Knowledge document file is not valid JSON.",
        ) from exc

    documents = [
        document
        for index, row in enumerate(_extract_rows(payload), start=1)
        if (document := _normalize_document(row, index)) is not None
    ]
    return {"items": documents}
