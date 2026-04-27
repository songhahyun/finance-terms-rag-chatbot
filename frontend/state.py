from __future__ import annotations

import base64
import json
import os

import streamlit as st


def init_state() -> None:
    """Initialize Streamlit session state for auth, routing, and chat data."""
    defaults = {
        "messages": [],
        "access_token": "",
        "auth_status": "Not signed in",
        "current_page": "login",
        "active_view": "chat",
        "current_user": "",
        "current_role": "",
        "backend_base_url": os.getenv("CHAT_API_BASE_URL", "http://localhost:8000").rstrip("/"),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def decode_token_claims(token: str) -> tuple[str, str]:
    """Extract username and primary role from a JWT payload."""
    try:
        _, payload_part, _ = token.split(".")
        padding = "=" * (-len(payload_part) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_part + padding).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return "", ""
    username = str(payload.get("sub", "")).strip()
    roles = payload.get("roles", [])
    role = str(roles[0]).strip() if isinstance(roles, list) and roles else ""
    return username, role


def set_authenticated_session(token: str, username: str, role: str, status_message: str) -> None:
    """Store authenticated user details in Streamlit session state."""
    token_username, token_role = decode_token_claims(token)
    st.session_state.access_token = token
    st.session_state.current_user = token_username or username
    st.session_state.current_role = token_role or role
    st.session_state.auth_status = status_message
    st.session_state.current_page = "app"


def sign_out() -> None:
    """Clear the authenticated session and return to the login screen."""
    st.session_state.access_token = ""
    st.session_state.current_user = ""
    st.session_state.current_role = ""
    st.session_state.auth_status = "Signed out"
    st.session_state.current_page = "login"
    st.session_state.active_view = "chat"
    st.session_state.messages = []
