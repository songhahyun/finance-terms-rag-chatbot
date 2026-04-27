from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class UserRecord:
    username: str
    password: str
    roles: tuple[str, ...] = field(default_factory=tuple)
    is_active: bool = True
