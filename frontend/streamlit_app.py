from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from frontend.components.auth import render_auth_art, render_login_page, render_signup_page
from frontend.components.layout import render_authenticated_app
from frontend.state import init_state
from frontend.styles import inject_app_styles


def main() -> None:
    """Run the Streamlit frontend entrypoint."""
    st.set_page_config(page_title="FinRAG Chatbot", page_icon="F", layout="wide")
    init_state()
    inject_app_styles()

    if not st.session_state.access_token:
        with st.container(border=True):
            st.markdown('<div class="auth-wrap-marker"></div>', unsafe_allow_html=True)
            form_col, art_col = st.columns([0.52, 0.48], gap="small")
            with form_col:
                if st.session_state.current_page == "signup":
                    render_signup_page()
                else:
                    render_login_page()
            with art_col:
                render_auth_art()
        return

    render_authenticated_app()


if __name__ == "__main__":
    main()
