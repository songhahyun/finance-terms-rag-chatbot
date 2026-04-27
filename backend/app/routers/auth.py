from __future__ import annotations

import hmac

from fastapi import APIRouter, HTTPException, status

from backend.app.auth.jwt import create_access_token
from backend.app.db.session import get_db_session
from backend.app.schemas.auth import LoginRequest, SignUpRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest) -> TokenResponse:
    """Authenticate a user with username and password.
    Return a signed bearer token for successful login."""
    user = get_db_session().get_user(request.username)
    if user is None or not hmac.compare_digest(user.password, request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )
    return TokenResponse(
        access_token=create_access_token(user.username, list(user.roles)),
    )


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(request: SignUpRequest) -> TokenResponse:
    """Register a new user account and issue a bearer token.
    Allow either admin or general user roles for the new account."""
    try:
        user = get_db_session().create_user(
            username=request.username,
            password=request.password,
            role=request.role,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return TokenResponse(
        access_token=create_access_token(user.username, list(user.roles)),
    )
