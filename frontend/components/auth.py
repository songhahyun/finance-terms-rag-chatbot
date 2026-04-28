from __future__ import annotations

import os
from pathlib import Path

import requests
import streamlit as st

from frontend.api_client import extract_error_message, login, signup
from frontend.state import set_authenticated_session
from frontend.styles import brand_html

ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"


def render_auth_art() -> None:
    """Render the finance illustration used on auth screens."""
    st.markdown('<div class="auth-art-image">', unsafe_allow_html=True)
    st.image(str(ASSET_DIR / "bank_icon.png"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_login_page() -> None:
    """Render the login page for existing users."""
    st.markdown('<div class="auth-panel">', unsafe_allow_html=True)
    st.markdown(brand_html(), unsafe_allow_html=True)
    st.markdown(
        '<div style="margin:14px 0 0 28px;color:#64748b;font-size:0.86rem;">금융 지식을 가장 빠르고 정확하게</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="auth-title">로그인</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-copy">FinRAG Chatbot에 오신 것을 환영합니다.</div>', unsafe_allow_html=True)
    with st.expander("서버 연결", expanded=False):
        st.session_state.backend_base_url = st.text_input(
            "Backend base URL",
            value=st.session_state.backend_base_url,
            help="FastAPI server URL",
        ).strip().rstrip("/")

    username = st.text_input(
        "아이디",
        value=os.getenv("API_ADMIN_USERNAME", "admin"),
        key="login_username",
        placeholder="아이디를 입력하세요",
    ).strip()
    password = st.text_input("비밀번호", type="password", key="login_password", placeholder="비밀번호를 입력하세요")

    if st.button("로그인", use_container_width=True, type="primary"):
        try:
            token = login(st.session_state.backend_base_url, username, password, timeout_sec=30)
            set_authenticated_session(token, username, "", "Signed in")
            st.rerun()
        except requests.RequestException as exc:
            st.error(f"Login failed: {extract_error_message(exc)}")

    help_cols = st.columns([1, 1])
    with help_cols[0]:
        st.checkbox("아이디 기억하기", value=False)
    with help_cols[1]:
        st.markdown(
            '<div style="text-align:right;padding-top:8px;color:#2563eb;font-size:0.85rem;">비밀번호 찾기</div>',
            unsafe_allow_html=True,
        )
    if st.button("회원가입", use_container_width=True):
        st.session_state.current_page = "signup"
        st.rerun()
    st.markdown(
        '<div style="position:fixed;bottom:28px;color:#94a3b8;font-size:0.76rem;">© 2024 FinRAG Chatbot. All rights reserved.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def render_signup_page() -> None:
    """Render the sign-up page for new users."""
    st.markdown('<div class="auth-panel">', unsafe_allow_html=True)
    st.markdown(brand_html(), unsafe_allow_html=True)
    st.markdown(
        '<div style="margin:14px 0 0 28px;color:#64748b;font-size:0.86rem;">금융 지식을 가장 빠르고 정확하게</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="auth-title">회원가입</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-copy">계정을 만들고 FinRAG 워크스페이스를 시작하세요.</div>', unsafe_allow_html=True)
    with st.expander("서버 연결", expanded=False):
        st.session_state.backend_base_url = st.text_input(
            "Backend base URL",
            value=st.session_state.backend_base_url,
            help="FastAPI server URL",
            key="signup_backend_base_url",
        ).strip().rstrip("/")

    username = st.text_input("아이디", key="signup_username", placeholder="아이디를 입력하세요").strip()
    password = st.text_input("비밀번호", type="password", key="signup_password", placeholder="비밀번호를 입력하세요")
    role_label = st.selectbox("계정 유형", options=["General User", "Admin"], index=0)
    role = "admin" if role_label == "Admin" else "user"

    if st.button("계정 만들기", use_container_width=True, type="primary"):
        try:
            token = signup(st.session_state.backend_base_url, username, password, role, timeout_sec=30)
            set_authenticated_session(token, username, role, "Signed up and signed in")
            st.rerun()
        except requests.RequestException as exc:
            st.error(f"Sign-up failed: {extract_error_message(exc)}")
    if st.button("로그인으로 돌아가기", use_container_width=True):
        st.session_state.current_page = "login"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
