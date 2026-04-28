from __future__ import annotations

import html

import streamlit as st

from frontend.components.chat import render_chat_workspace
from frontend.components.dashboard import render_dashboard_page
from frontend.state import sign_out
from frontend.styles import brand_html


def render_topbar() -> None:
    """Render the app top bar."""
    username = st.session_state.current_user or "사용자"
    user_label = html.escape(f"{username} 님")
    avatar = html.escape(username[:1].upper())
    st.markdown(
        f"""
        <div class="fin-topbar">
            {brand_html()}
            <div class="fin-topbar-actions">
                <div class="fin-user"><span class="fin-avatar">{avatar}</span><span>{user_label}</span></div>
                <a class="fin-logout" href="?logout=1" target="_self">로그아웃</a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_side_nav(active: str) -> None:
    """Render left navigation for the authenticated app."""
    st.markdown('<div class="side-nav-start"></div>', unsafe_allow_html=True)
    if st.button("+ 새 대화", key="side_new_chat", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.session_state.active_view = "chat"
        st.rerun()

    chat_type = "primary" if active == "chat" else "secondary"
    if st.button("대화", key="side_chat", use_container_width=True, type=chat_type):
        st.session_state.active_view = "chat"
        st.rerun()
    if st.session_state.current_role == "admin":
        dash_type = "primary" if active == "dashboard" else "secondary"
        if st.button("대시보드", key="side_dashboard", use_container_width=True, type=dash_type):
            st.session_state.active_view = "dashboard"
            st.rerun()
    st.button("지식 문서", key="side_docs", use_container_width=True, disabled=True)
    st.button("설정", key="side_settings", use_container_width=True, disabled=True)

    st.markdown('<div class="recent-title">최근 대화</div>', unsafe_allow_html=True)
    recent_items = _recent_chat_titles()
    for idx, item in enumerate(recent_items):
        cls = "recent-item active" if idx == 0 and active == "chat" else "recent-item"
        st.markdown(f'<div class="{cls}">{html.escape(item)}</div>', unsafe_allow_html=True)
    st.markdown('<div class="side-nav-end"></div>', unsafe_allow_html=True)


def render_authenticated_app() -> None:
    """Render the authenticated shell with left navigation."""
    if st.query_params.get("logout") == "1":
        st.query_params.clear()
        sign_out()
        st.rerun()

    active = st.session_state.active_view
    if active == "dashboard" and st.session_state.current_role != "admin":
        active = "chat"
        st.session_state.active_view = "chat"

    with st.container(border=True):
        st.markdown('<div class="fin-shell-marker"></div>', unsafe_allow_html=True)
        render_topbar()
        nav_col, body_col = st.columns([0.15, 0.85], gap="small", vertical_alignment="top")
        with nav_col:
            render_side_nav(active)
        with body_col:
            if active == "dashboard":
                render_dashboard_page()
            else:
                render_chat_workspace()


def _recent_chat_titles() -> list[str]:
    """Return current-session user prompts as recent chat titles."""
    titles: list[str] = []
    seen: set[str] = set()
    for message in reversed(st.session_state.messages):
        if message.get("role") != "user":
            continue
        title = str(message.get("content", "")).strip()
        if not title or title in seen:
            continue
        titles.append(title[:40])
        seen.add(title)
        if len(titles) == 5:
            break
    return titles
