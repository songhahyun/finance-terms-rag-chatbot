from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from backend.app.auth.deps import get_current_user
from backend.app.schemas.auth import AuthenticatedUser


def require_roles(*required_roles: str) -> Callable[[AuthenticatedUser], AuthenticatedUser]:
    def _dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if not required_roles:
            return user
        if any(role in user.roles for role in required_roles):
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role.",
        )

    return _dependency
