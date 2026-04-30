from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Expose a minimal health check endpoint.
    Return a static ok payload when the API is running."""
    return {"status": "ok"}
