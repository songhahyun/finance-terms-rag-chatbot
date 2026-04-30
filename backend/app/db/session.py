from __future__ import annotations

from threading import Lock

from backend.app.config import get_backend_settings
from backend.app.db.models import UserRecord


class InMemorySession:
    """Minimal session store for auth scaffolding."""

    def __init__(self) -> None:
        """Initialize the in-memory user store and lock.
        Seed the default admin user from backend settings."""
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
        """Look up a user record by username.
        Return None when the user does not exist."""
        with self._lock:
            return self._users.get(username)

    def create_user(self, username: str, password: str, role: str) -> UserRecord:
        """Create a new in-memory user record.
        Raise ValueError when the username already exists."""
        with self._lock:
            if username in self._users:
                raise ValueError("Username already exists.")
            user = UserRecord(
                username=username,
                password=password,
                roles=(role,),
            )
            self._users[username] = user
            return user


_SESSION = InMemorySession()


def get_db_session() -> InMemorySession:
    """Return the shared in-memory session instance.
    Keep auth data access consistent across requests."""
    return _SESSION
