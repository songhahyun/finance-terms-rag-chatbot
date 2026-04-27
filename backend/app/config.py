from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BackendSettings:
    auth_required: bool
    jwt_secret: str
    jwt_algorithm: str
    jwt_exp_minutes: int
    default_admin_username: str
    default_admin_password: str
    default_admin_role: str


def get_backend_settings() -> BackendSettings:
    return BackendSettings(
        auth_required=os.getenv("API_AUTH_REQUIRED", "false").lower() == "true",
        jwt_secret=os.getenv("API_JWT_SECRET", "change-me-in-production"),
        jwt_algorithm=os.getenv("API_JWT_ALGORITHM", "HS256"),
        jwt_exp_minutes=int(os.getenv("API_JWT_EXP_MINUTES", "60")),
        default_admin_username=os.getenv("API_ADMIN_USERNAME", "admin"),
        default_admin_password=os.getenv("API_ADMIN_PASSWORD", "admin123"),
        default_admin_role=os.getenv("API_ADMIN_ROLE", "admin"),
    )
