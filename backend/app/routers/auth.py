from __future__ import annotations

import hmac

from fastapi import APIRouter, HTTPException, status

from backend.app.auth.jwt import create_access_token
from backend.app.db.session import get_db_session
from backend.app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest) -> TokenResponse:
    user = get_db_session().get_user(request.username)
    if user is None or not hmac.compare_digest(user.password, request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )
    return TokenResponse(
        access_token=create_access_token(user.username, list(user.roles)),
    )
