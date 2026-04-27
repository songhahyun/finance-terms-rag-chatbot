from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from backend.app.auth.deps import get_current_user
from backend.app.schemas.auth import AuthenticatedUser


def require_roles(*required_roles: str) -> Callable[[AuthenticatedUser], AuthenticatedUser]:
    """Create a dependency that enforces one of the required roles.
    Return the authenticated user when authorization succeeds."""
    def _dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        """Check the current user's roles against the required set.
        Raise HTTP 403 when no required role is present."""
        if not required_roles:
            return user
        if any(role in user.roles for role in required_roles):
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role.",
        )

    return _dependency
