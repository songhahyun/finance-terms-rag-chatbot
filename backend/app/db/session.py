from __future__ import annotations

from threading import Lock

from backend.app.config import get_backend_settings
from backend.app.db.models import UserRecord


class InMemorySession:
    """Minimal session store for auth scaffolding."""

    def __init__(self) -> None:
        settings = get_backend_settings()
        self._lock = Lock()
        self._users = {
            settings.default_admin_username: UserRecord(
                username=settings.default_admin_username,
                password=settings.default_admin_password,
                roles=(settings.default_admin_role,),
            )
        }

    def get_user(self, username: str) -> UserRecord | None:
        with self._lock:
            return self._users.get(username)


_SESSION = InMemorySession()


def get_db_session() -> InMemorySession:
    return _SESSION
