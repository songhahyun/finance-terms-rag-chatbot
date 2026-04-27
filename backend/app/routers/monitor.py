from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.auth.rbac import require_roles
from backend.app.schemas.auth import AuthenticatedUser
from src.serving.rag_service import get_rag_service

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.get("/summary")
def monitor_summary(user: AuthenticatedUser = Depends(require_roles("admin"))) -> dict:
    """Return aggregated monitoring metrics for recent traces.
    Read the summary directly from the shared RAG service."""
    return get_rag_service().monitor_summary()


@router.get("/recent")
def monitor_recent(limit: int = 20, user: AuthenticatedUser = Depends(require_roles("admin"))) -> dict:
    """Return recent monitoring trace records.
    Limit the response size to the requested item count."""
    return get_rag_service().monitor_recent(limit=limit)
