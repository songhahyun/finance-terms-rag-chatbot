from __future__ import annotations

import streamlit as st

from frontend.components.chat import render_chat_workspace
from frontend.components.dashboard import render_dashboard_page
from frontend.styles import brand_html


def render_topbar() -> None:
    """Render the app top bar."""
    username = st.session_state.current_user or "사용자"
    st.markdown(
        f"""
        <div class="fin-topbar">
            {brand_html()}
            <div class="fin-user"><span class="fin-avatar">{username[:1].upper()}</span><span>{username} 님</span><span>⌄</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_side_nav(active: str) -> None:
    """Render left navigation for the authenticated app."""
    st.markdown('<div class="side-card-marker"></div>', unsafe_allow_html=True)
    if st.button("+  새 대화", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.session_state.active_view = "chat"
        st.rerun()

    chat_type = "primary" if active == "chat" else "secondary"
    if st.button("대화", use_container_width=True, type=chat_type):
        st.session_state.active_view = "chat"
        st.rerun()
    if st.session_state.current_role == "admin":
        dash_type = "primary" if active == "dashboard" else "secondary"
        if st.button("대시보드", use_container_width=True, type=dash_type):
            st.session_state.active_view = "dashboard"
            st.rerun()
    st.button("지식 문서", use_container_width=True, disabled=True)
    st.button("설정", use_container_width=True, disabled=True)

    st.markdown('<div class="recent-title">최근 대화</div>', unsafe_allow_html=True)
    recent_items = [
        "ELS 상품 설명해줘",
        "신용등급 하락 원인",
        "금리 인상 영향 분석",
        "회사채 투자 리스크",
        "환율 전망 알려줘",
    ]
    for idx, item in enumerate(recent_items):
        cls = "recent-item active" if idx == 0 and active == "chat" else "recent-item"
        st.markdown(f'<div class="{cls}">{item}</div>', unsafe_allow_html=True)


def render_authenticated_app() -> None:
    """Render the authenticated shell with left navigation."""
    active = st.session_state.active_view
    if active == "dashboard" and st.session_state.current_role != "admin":
        active = "chat"
        st.session_state.active_view = "chat"

    with st.container(border=True):
        st.markdown('<div class="fin-shell-marker"></div>', unsafe_allow_html=True)
        render_topbar()
        nav_col, body_col = st.columns([0.18, 0.82], gap="small")
        with nav_col:
            render_side_nav(active)
        with body_col:
            if active == "dashboard":
                render_dashboard_page()
            else:
                render_chat_workspace()
