from __future__ import annotations

import json
import os
from typing import Any

import requests
import streamlit as st


def _post_chat(api_url: str, question: str, mode: str, k: int, language: str, timeout_sec: int) -> dict[str, Any]:
    resp = requests.post(
        api_url,
        json={"question": question, "mode": mode, "k": k, "language": language},
        timeout=timeout_sec,
    )
    resp.raise_for_status()
    return resp.json()


def _stream_chat(
    api_url: str,
    question: str,
    mode: str,
    k: int,
    language: str,
    timeout_sec: int,
):
    with requests.post(
        api_url,
        json={"question": question, "mode": mode, "k": k, "language": language},
        timeout=timeout_sec,
        stream=True,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            yield json.loads(line)


def _init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []


def _render_sources(sources: list[dict[str, Any]]) -> None:
    if not sources:
        return
    with st.expander("Sources"):
        for idx, item in enumerate(sources, start=1):
            chunk_id = item.get("chunk_id")
            source = item.get("source")
            text = item.get("text", "")
            st.markdown(f"**{idx}. chunk_id:** `{chunk_id}`")
            st.markdown(f"**source:** `{source}`")
            st.markdown(f"**text:** {text}")
            st.divider()


def _render_history() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            _render_sources(message.get("sources") or [])


def main() -> None:
    st.set_page_config(page_title="Finance Terms RAG Chat", page_icon="F", layout="wide")
    st.title("Finance Terms RAG Chat")
    st.caption("Streamlit frontend connected to FastAPI `/chat` and `/chat/stream` endpoints")

    _init_state()

    with st.sidebar:
        st.subheader("Chat Settings")
        backend_base_url = st.text_input(
            "Backend base URL",
            value=os.getenv("CHAT_API_BASE_URL", "http://localhost:8000"),
            help="FastAPI server URL",
        ).strip().rstrip("/")
        mode = st.selectbox("Retrieval mode", options=["hybrid", "dense", "bm25"], index=0)
        language_label = st.selectbox("Answer language", options=["Korean", "English"], index=0)
        language = "ko" if language_label == "Korean" else "en"
        k = st.slider("Top-K", min_value=1, max_value=20, value=5)
        timeout_sec = st.number_input("API timeout (sec)", min_value=5, max_value=300, value=120, step=5)
        if st.button("Clear conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    api_url = f"{backend_base_url}/chat"
    stream_api_url = f"{backend_base_url}/chat/stream"
    _render_history()

    prompt = st.chat_input("Type your question")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Generating answer..."):
            try:
                answer_placeholder = st.empty()
                answer = ""
                sources: list[dict[str, Any]] = []
                for event in _stream_chat(stream_api_url, prompt, mode, int(k), language, int(timeout_sec)):
                    event_type = str(event.get("type", ""))
                    if event_type == "token":
                        answer += str(event.get("content", ""))
                        answer_placeholder.markdown(answer)
                    elif event_type == "final":
                        if not answer:
                            answer = str(event.get("answer", ""))
                            answer_placeholder.markdown(answer)
                        sources = event.get("sources", []) or []
                    elif event_type == "error":
                        raise requests.RequestException(str(event.get("message", "unknown stream error")))
                if not answer:
                    # Fallback: if streaming payload was empty, try normal non-stream endpoint.
                    result = _post_chat(api_url, prompt, mode, int(k), language, int(timeout_sec))
                    answer = result.get("answer", "")
                    sources = result.get("sources", [])
                    answer_placeholder.markdown(answer)
            except requests.RequestException as exc:
                answer = f"API request failed: {exc}"
                sources = []
                st.markdown(answer)
            _render_sources(sources)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
        }
    )


if __name__ == "__main__":
    main()
