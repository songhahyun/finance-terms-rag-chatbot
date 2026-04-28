from __future__ import annotations

import base64
import html
from pathlib import Path
from typing import Any

import requests
import streamlit as st

from frontend.api_client import extract_error_message, post_chat, stream_chat

ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"


def render_sources(sources: list[dict[str, Any]]) -> None:
    """Render retrieved source snippets in a compact panel."""
    if not sources:
        return
    rows = []
    for idx, item in enumerate(sources[:5], start=1):
        chunk_id = html.escape(str(item.get("chunk_id") or "-"))
        source = html.escape(str(item.get("source") or "출처 미상"))
        rows.append(f"<div>{idx}. {source} <span style='color:#94a3b8'>({chunk_id})</span></div>")
    st.markdown(
        f"""
        <div class="source-list">
            <strong>참고 문서 ({len(sources)})</strong>
            {''.join(rows)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_history() -> None:
    """Replay prior chat messages from session state."""
    for message in st.session_state.messages:
        role = message["role"]
        content = html.escape(str(message["content"])).replace("\n", "<br>")
        if role == "user":
            st.markdown(_user_bubble(content), unsafe_allow_html=True)
        else:
            st.markdown(_assistant_bubble(content, escaped=True), unsafe_allow_html=True)
            render_sources(message.get("sources") or [])
            render_disclaimer()


def render_chat_workspace() -> None:
    """Render the authenticated chat workspace."""
    inject_chatbot_avatar_style()
    st.markdown('<div class="content-pad">', unsafe_allow_html=True)
    st.markdown('<div class="chat-workspace-marker"></div>', unsafe_allow_html=True)
    st.markdown(f'<p class="page-title">{_conversation_title()}</p>', unsafe_allow_html=True)
    if st.session_state.messages:
        st.markdown('<div class="page-subtitle">현재 세션 대화</div>', unsafe_allow_html=True)

    st.markdown('<div class="chat-header-controls-marker"></div>', unsafe_allow_html=True)
    header_cols = st.columns([1.15, 1.05, 1.05])
    with header_cols[0]:
        st.markdown('<div class="chat-control-marker mode"></div>', unsafe_allow_html=True)
        mode = st.selectbox("검색 방식", options=["hybrid", "dense", "bm25"], index=0)
    with header_cols[1]:
        st.markdown('<div class="chat-control-marker language"></div>', unsafe_allow_html=True)
        language_label = st.selectbox("언어", options=["Korean", "English"], index=0)
    with header_cols[2]:
        st.markdown('<div class="chat-control-marker topk"></div>', unsafe_allow_html=True)
        k = st.number_input("검색 문서 개수", min_value=1, max_value=20, value=5, step=1)
    with st.expander("연결 설정", expanded=False):
        backend_base_url = st.text_input(
            "Backend base URL",
            value=st.session_state.backend_base_url,
            help="FastAPI server URL",
        ).strip().rstrip("/")
        st.session_state.backend_base_url = backend_base_url
        timeout_sec = st.number_input("API timeout (sec)", min_value=5, max_value=300, value=120, step=5)

    language = "ko" if language_label == "Korean" else "en"
    api_url = f"{st.session_state.backend_base_url}/chat"
    stream_api_url = f"{st.session_state.backend_base_url}/chat/stream"

    transcript_container = st.container()
    input_container = st.container()

    with input_container:
        st.markdown('<div class="chat-input-anchor"></div>', unsafe_allow_html=True)
        prompt = st.chat_input("메시지를 입력하세요...")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})

    with transcript_container:
        st.markdown('<div class="chat-transcript-marker"></div>', unsafe_allow_html=True)
        render_history()

        if not prompt:
            st.markdown("</div>", unsafe_allow_html=True)
            return

        try:
            answer_placeholder = st.empty()
            answer_placeholder.markdown(_assistant_loading_bubble(), unsafe_allow_html=True)
            answer = ""
            sources: list[dict[str, Any]] = []
            for event in stream_chat(
                stream_api_url,
                prompt,
                mode,
                int(k),
                language,
                int(timeout_sec),
                st.session_state.access_token,
            ):
                event_type = str(event.get("type", ""))
                if event_type == "token":
                    answer += str(event.get("content", ""))
                    answer_placeholder.markdown(_assistant_bubble(answer), unsafe_allow_html=True)
                elif event_type == "final":
                    if not answer:
                        answer = str(event.get("answer", ""))
                        answer_placeholder.markdown(_assistant_bubble(answer), unsafe_allow_html=True)
                    sources = event.get("sources", []) or []
                elif event_type == "error":
                    raise requests.RequestException(str(event.get("message", "unknown stream error")))
            if not answer:
                result = post_chat(api_url, prompt, mode, int(k), language, int(timeout_sec), st.session_state.access_token)
                answer = result.get("answer", "")
                sources = result.get("sources", [])
                answer_placeholder.markdown(_assistant_bubble(answer), unsafe_allow_html=True)
        except requests.RequestException as exc:
            answer = f"API request failed: {extract_error_message(exc)}"
            sources = []
            st.error(answer)
        render_sources(sources)

        st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})
        render_disclaimer()
    st.markdown("</div>", unsafe_allow_html=True)


def _user_bubble(content: str) -> str:
    avatar = html.escape(_user_avatar_letter())
    return (
        '<div class="bubble-row user">'
        f'<div class="chat-bubble user">{content}</div>'
        f'<div class="chat-avatar user">{avatar}</div>'
        '</div>'
    )


def _assistant_bubble(answer: str, escaped: bool = False) -> str:
    content = answer if escaped else html.escape(answer).replace("\n", "<br>")
    return (
        '<div class="bubble-row">'
        '<div class="chat-avatar bot"></div>'
        f'<div class="chat-bubble">{content}</div>'
        '</div>'
    )


def _assistant_loading_bubble() -> str:
    return (
        '<div class="bubble-row">'
        '<div class="chat-avatar bot"></div>'
        '<div class="chat-bubble loading-dots"><span></span><span></span><span></span></div>'
        '</div>'
    )


def _user_avatar_letter() -> str:
    username = str(st.session_state.current_user or "U").strip()
    return (username[:1] or "U").upper()


def inject_chatbot_avatar_style() -> None:
    image_src = _chatbot_icon_data_uri()
    st.markdown(
        f"""
        <style>
        .chat-avatar.bot {{
            background-image: url("{image_src}");
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def _chatbot_icon_data_uri() -> str:
    image_bytes = (ASSET_DIR / "chatbot_icon.png").read_bytes()
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_disclaimer() -> None:
    st.markdown(
        '<div class="disclaimer">본 답변은 참고용이며, 투자 권유가 아닙니다. 최종 투자 결정은 투자자 본인의 책임입니다.</div>',
        unsafe_allow_html=True,
    )


def _conversation_title() -> str:
    for message in st.session_state.messages:
        if message.get("role") == "user":
            title = str(message.get("content", "")).strip()
            if title:
                return html.escape(title[:40])
    return "새 대화"
