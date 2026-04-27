from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.auth.deps import get_current_user
from backend.app.schemas.auth import AuthenticatedUser
from src.serving.rag_service import get_rag_service

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.get("/summary")
def monitor_summary(user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    return get_rag_service().monitor_summary()


@router.get("/recent")
def monitor_recent(limit: int = 20, user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    return get_rag_service().monitor_recent(limit=limit)
