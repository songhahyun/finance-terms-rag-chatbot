from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.auth.jwt import decode_access_token
from backend.app.config import get_backend_settings
from backend.app.db.session import get_db_session
from backend.app.schemas.auth import AuthenticatedUser

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser:
    settings = get_backend_settings()
    if credentials is None:
        if settings.auth_required:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token.",
            )
        return AuthenticatedUser(username="anonymous", roles=["guest"])

    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    username = str(payload.get("sub", "")).strip()
    user = get_db_session().get_user(username)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not active.",
        )
    return AuthenticatedUser(username=user.username, roles=list(user.roles))
