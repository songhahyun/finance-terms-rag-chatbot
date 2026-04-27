from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

from backend.app.config import get_backend_settings


def _b64encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")


def _b64decode(payload: str) -> bytes:
    padding = "=" * (-len(payload) % 4)
    return base64.urlsafe_b64decode(payload + padding)


def create_access_token(subject: str, roles: list[str]) -> str:
    settings = get_backend_settings()
    header = {"alg": settings.jwt_algorithm, "typ": "JWT"}
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.jwt_exp_minutes)
    body = {
        "sub": subject,
        "roles": roles,
        "exp": int(expires_at.timestamp()),
    }
    header_part = _b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    body_part = _b64encode(json.dumps(body, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_part}.{body_part}".encode("ascii")
    signature = hmac.new(
        settings.jwt_secret.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    return f"{header_part}.{body_part}.{_b64encode(signature)}"


def decode_access_token(token: str) -> dict:
    settings = get_backend_settings()
    try:
        header_part, body_part, signature_part = token.split(".")
    except ValueError as exc:
        raise ValueError("Malformed token.") from exc

    signing_input = f"{header_part}.{body_part}".encode("ascii")
    expected_signature = hmac.new(
        settings.jwt_secret.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    actual_signature = _b64decode(signature_part)
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise ValueError("Invalid token signature.")

    payload = json.loads(_b64decode(body_part).decode("utf-8"))
    if int(payload.get("exp", 0)) < int(datetime.now(UTC).timestamp()):
        raise ValueError("Token has expired.")
    return payload
