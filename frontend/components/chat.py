from __future__ import annotations

import html
from typing import Any

import requests
import streamlit as st

from frontend.api_client import extract_error_message, post_chat, stream_chat
from frontend.state import sign_out


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
            st.markdown(
                f'<div class="bubble-row user"><div class="chat-bubble user">{content}</div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="bubble-row"><div class="bot-dot">F</div><div class="chat-bubble">{content}</div></div>',
                unsafe_allow_html=True,
            )
            render_sources(message.get("sources") or [])


def render_chat_workspace() -> None:
    """Render the authenticated chat workspace."""
    st.markdown('<div class="content-pad">', unsafe_allow_html=True)
    header_cols = st.columns([1.8, 1, 1, 0.8, 0.65])
    with header_cols[0]:
        st.markdown('<p class="page-title">ELS 상품 설명해줘</p>', unsafe_allow_html=True)
        st.markdown('<div class="page-subtitle">2024-05-27 14:30</div>', unsafe_allow_html=True)
    with header_cols[1]:
        mode = st.selectbox("검색 방식", options=["hybrid", "dense", "bm25"], index=0, label_visibility="collapsed")
    with header_cols[2]:
        language_label = st.selectbox("답변 언어", options=["Korean", "English"], index=0, label_visibility="collapsed")
    with header_cols[3]:
        k = st.number_input("Top-K", min_value=1, max_value=20, value=5, step=1, label_visibility="collapsed")
    with header_cols[4]:
        if st.button("로그아웃", use_container_width=True):
            sign_out()
            st.rerun()

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
    if not st.session_state.messages:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": "안녕하세요. 금융 용어와 상품 구조에 대해 질문해 주세요. 관련 문서를 검색해 근거와 함께 답변합니다.",
                "sources": [],
            }
        )

    st.markdown('<div class="chat-transcript">', unsafe_allow_html=True)
    render_history()
    st.markdown("</div>", unsafe_allow_html=True)

    prompt = st.chat_input("메시지를 입력하세요...")
    if not prompt:
        st.markdown(
            '<div class="disclaimer">본 답변은 참고용이며, 투자 권유가 아닙니다. 최종 투자 결정은 투자자 본인의 책임입니다.</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.markdown(
        f'<div class="bubble-row user"><div class="chat-bubble user">{html.escape(prompt)}</div></div>',
        unsafe_allow_html=True,
    )

    with st.spinner("답변을 생성하고 있습니다..."):
        try:
            answer_placeholder = st.empty()
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
    st.markdown(
        '<div class="disclaimer">본 답변은 참고용이며, 투자 권유가 아닙니다. 최종 투자 결정은 투자자 본인의 책임입니다.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def _assistant_bubble(answer: str) -> str:
    content = html.escape(answer).replace("\n", "<br>")
    return f'<div class="bubble-row"><div class="bot-dot">F</div><div class="chat-bubble">{content}</div></div>'
