from __future__ import annotations

import json
from typing import Any, Iterator

import requests


def auth_headers(token: str | None) -> dict[str, str]:
    """Build request headers for authenticated API calls."""
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def extract_error_message(exc: requests.RequestException) -> str:
    """Extract a readable backend error message from a request exception."""
    response = getattr(exc, "response", None)
    if response is None:
        return str(exc)
    try:
        payload = response.json()
    except ValueError:
        return str(exc)
    detail = payload.get("detail")
    return str(detail) if detail else str(exc)


def login(api_base_url: str, username: str, password: str, timeout_sec: int) -> str:
    """Authenticate against the backend login endpoint."""
    resp = requests.post(
        f"{api_base_url}/auth/login",
        json={"username": username, "password": password},
        timeout=timeout_sec,
    )
    resp.raise_for_status()
    token = str(resp.json().get("access_token", "")).strip()
    if not token:
        raise requests.RequestException("Login response did not include an access token.")
    return token


def signup(api_base_url: str, username: str, password: str, role: str, timeout_sec: int) -> str:
    """Register a new account through the backend signup endpoint."""
    resp = requests.post(
        f"{api_base_url}/auth/signup",
        json={"username": username, "password": password, "role": role},
        timeout=timeout_sec,
    )
    resp.raise_for_status()
    token = str(resp.json().get("access_token", "")).strip()
    if not token:
        raise requests.RequestException("Signup response did not include an access token.")
    return token


def post_chat(
    api_url: str,
    question: str,
    mode: str,
    k: int,
    language: str,
    timeout_sec: int,
    token: str | None,
) -> dict[str, Any]:
    """Send a standard chat request to the backend API."""
    resp = requests.post(
        api_url,
        json={"question": question, "mode": mode, "k": k, "language": language},
        headers=auth_headers(token),
        timeout=timeout_sec,
    )
    resp.raise_for_status()
    return resp.json()


def stream_chat(
    api_url: str,
    question: str,
    mode: str,
    k: int,
    language: str,
    timeout_sec: int,
    token: str | None,
) -> Iterator[dict[str, Any]]:
    """Stream chat events from the backend endpoint."""
    with requests.post(
        api_url,
        json={"question": question, "mode": mode, "k": k, "language": language},
        headers=auth_headers(token),
        timeout=timeout_sec,
        stream=True,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines(decode_unicode=True):
            if line:
                yield json.loads(line)
