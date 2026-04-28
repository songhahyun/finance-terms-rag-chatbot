from __future__ import annotations

import streamlit as st


def inject_app_styles() -> None:
    """Install the shared UI theme used by the Streamlit frontend."""
    st.markdown(
        """
        <style>
        :root {
            --app-blue: #2563eb;
            --app-blue-soft: #eaf1ff;
            --app-ink: #111827;
            --app-muted: #64748b;
            --app-border: #dbe3ef;
        }
        .stApp {
            background:
                radial-gradient(circle at 76% 12%, rgba(37, 99, 235, 0.08), transparent 28%),
                linear-gradient(180deg, #f8fbff 0%, #ffffff 58%, #f7faff 100%);
            color: var(--app-ink);
        }
        [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] {
            display: none;
        }
        .block-container {
            max-width: 1500px;
            padding: 1rem 1.5rem 1.4rem;
        }
        .stButton > button, .stDownloadButton > button {
            border-radius: 6px;
            border: 1px solid var(--app-border);
            box-shadow: none;
            font-weight: 600;
            min-height: 2.5rem;
        }
        .stButton > button:hover, .stDownloadButton > button:hover {
            border-color: var(--app-blue) !important;
            color: var(--app-blue) !important;
        }
        .stButton button[data-testid="stBaseButton-primary"],
        .stButton > button[kind="primary"],
        .stFormSubmitButton button[data-testid="stBaseButton-primary"] {
            background: var(--app-blue) !important;
            border-color: var(--app-blue) !important;
            color: #ffffff !important;
        }
        .stButton button[data-testid="stBaseButton-primary"]:hover,
        .stButton > button[kind="primary"]:hover,
        .stFormSubmitButton button[data-testid="stBaseButton-primary"]:hover {
            background: #1d4ed8 !important;
            border-color: #1d4ed8 !important;
            color: #ffffff !important;
        }
        .stButton button[data-testid="stBaseButton-secondary"]:focus,
        .stButton button[data-testid="stBaseButton-primary"]:focus,
        .stDownloadButton button:focus {
            border-color: var(--app-blue) !important;
            box-shadow: 0 0 0 0.12rem rgba(37, 99, 235, 0.18) !important;
        }
        div[data-testid="stTextInput"] input,
        div[data-testid="stPasswordInput"] input,
        div[data-testid="stSelectbox"] > div,
        div[data-testid="stDateInput"] input,
        div[data-testid="stNumberInput"] input {
            border-radius: 6px;
            border-color: var(--app-border);
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.fin-shell-marker),
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-wrap-marker) {
            border: 1px solid var(--app-border);
            border-radius: 8px !important;
            background: rgba(255, 255, 255, 0.94) !important;
            box-shadow: 0 18px 42px rgba(30, 64, 175, 0.08);
            padding: 0 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.fin-shell-marker) {
            min-height: calc(100vh - 2rem);
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-wrap-marker) {
            min-height: calc(100vh - 2rem);
            overflow: hidden;
        }
        .fin-shell-marker, .auth-wrap-marker, .side-card-marker {
            display: none;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.fin-shell-marker) div[data-testid="stVerticalBlock"]:has(> div .fin-topbar) {
            gap: 0;
        }
        .fin-topbar {
            height: 52px;
            border-bottom: 1px solid var(--app-border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 18px;
            background: rgba(255, 255, 255, 0.92);
        }
        .fin-brand {
            display: flex;
            align-items: center;
            gap: 9px;
            font-weight: 800;
            color: var(--app-blue);
        }
        .fin-mark {
            width: 20px;
            height: 20px;
            border: 2px solid var(--app-blue);
            border-radius: 6px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            line-height: 1;
        }
        .fin-user {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #334155;
            font-size: 0.9rem;
            font-weight: 600;
        }
        .fin-avatar {
            width: 28px;
            height: 28px;
            border-radius: 50%;
            background: #dbe7f6;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: #64748b;
            font-weight: 800;
        }
        .auth-panel {
            padding: 26px 42px 20px;
        }
        .auth-title {
            margin: 90px 0 8px;
            font-size: 1.75rem;
            font-weight: 800;
            color: var(--app-ink);
        }
        .auth-copy {
            color: var(--app-muted);
            font-size: 0.92rem;
            margin-bottom: 24px;
        }
        .auth-art {
            min-height: calc(100vh - 2rem);
            border-left: 1px solid #edf2fb;
            background:
                linear-gradient(145deg, rgba(255,255,255,0.88), rgba(235,243,255,0.88)),
                radial-gradient(circle at 50% 42%, rgba(37,99,235,0.18), transparent 34%);
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .auth-bank-svg {
            width: min(560px, 90%);
            height: auto;
            display: block;
        }
        .auth-art-image {
            width: min(560px, 86%);
            display: flex;
            align-items: center;
            justify-content: center;
            filter: drop-shadow(0 22px 28px rgba(37, 99, 235, 0.16));
            margin-top: 200px;
        }
        .bank-illu {
            width: min(470px, 82%);
            aspect-ratio: 1.2;
            position: relative;
            filter: drop-shadow(0 22px 28px rgba(37, 99, 235, 0.18));
        }
        .bank-plate {
            position: absolute;
            inset: 28% 12% 12%;
            transform: skewY(-8deg);
            background: linear-gradient(145deg, #f8fbff, #dbe9ff);
            border-radius: 18px;
            border: 1px solid #c9dcff;
        }
        .bank-house {
            position: absolute;
            left: 30%;
            top: 28%;
            width: 38%;
            height: 38%;
            background: linear-gradient(160deg, #ffffff, #d9e8ff);
            border-radius: 12px;
            border: 1px solid #bfd5ff;
        }
        .bank-roof {
            position: absolute;
            left: 25%;
            top: 19%;
            width: 48%;
            height: 16%;
            background: #7da2f7;
            transform: skewY(-19deg);
            border-radius: 8px;
        }
        .bank-pillars {
            position: absolute;
            left: 34%;
            top: 45%;
            width: 30%;
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 9px;
        }
        .bank-pillars span {
            height: 70px;
            border-radius: 8px;
            background: linear-gradient(180deg, #8fb0ff, #3d6fee);
        }
        .bank-card, .bank-chart, .bank-coin, .bank-lens {
            position: absolute;
            background: linear-gradient(145deg, #ffffff, #dce9ff);
            border: 1px solid #c9dcff;
            border-radius: 12px;
        }
        .bank-card { right: 11%; top: 27%; width: 76px; height: 118px; }
        .bank-chart { left: 10%; top: 36%; width: 82px; height: 120px; }
        .bank-coin { left: 17%; bottom: 20%; width: 56px; height: 56px; border-radius: 50%; }
        .bank-lens { left: 28%; bottom: 11%; width: 86px; height: 86px; border-radius: 50%; background: transparent; border: 14px solid #5f8df5; }
        div[data-testid="column"]:has(.side-card-marker) {
            min-height: calc(100vh - 89px);
            border-right: 1px solid var(--app-border);
            background: rgba(249, 251, 255, 0.86);
            padding: 12px 12px 16px 12px;
        }
        div[data-testid="column"]:has(.side-card-marker) .stButton {
            margin-bottom: 0.35rem;
        }
        .recent-title {
            font-size: 0.78rem;
            color: #475569;
            font-weight: 700;
            margin: 10px 16px;
        }
        .recent-item {
            color: #334155;
            font-size: 0.82rem;
            padding: 8px 14px;
            margin: 0 8px 2px;
            border-radius: 5px;
        }
        .recent-item.active {
            background: var(--app-blue-soft);
            color: #1e3a8a;
            font-weight: 700;
        }
        .content-pad {
            padding: 16px 18px 10px;
        }
        .page-title {
            font-size: 1.25rem;
            font-weight: 800;
            margin: 0;
            color: var(--app-ink);
        }
        .page-subtitle {
            color: var(--app-muted);
            font-size: 0.86rem;
            margin-top: 4px;
        }
        .chat-transcript {
            min-height: 520px;
            padding: 8px 0 4px;
        }
        .bubble-row {
            display: flex;
            margin: 12px 0;
            gap: 10px;
        }
        .bubble-row.user {
            justify-content: flex-end;
        }
        .bot-dot {
            width: 30px;
            height: 30px;
            border-radius: 50%;
            background: #17426a;
            color: #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            flex: 0 0 auto;
        }
        .chat-bubble {
            max-width: 76%;
            border-radius: 8px;
            padding: 12px 14px;
            border: 1px solid var(--app-border);
            background: #fff;
            color: #1f2937;
            line-height: 1.58;
            font-size: 0.92rem;
        }
        .chat-bubble.user {
            background: var(--app-blue);
            color: #fff;
            border-color: var(--app-blue);
        }
        .source-list {
            margin-top: 12px;
            padding-top: 10px;
            border-top: 1px solid #e8eef7;
            color: #475569;
            font-size: 0.82rem;
        }
        .disclaimer {
            color: #64748b;
            font-size: 0.78rem;
            padding: 0 2px 10px;
        }
        .metric-strip {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            margin: 14px 0 18px;
        }
        .metric-card {
            border: 1px solid var(--app-border);
            border-radius: 8px;
            padding: 14px;
            background: #fff;
        }
        .metric-label {
            color: #64748b;
            font-size: 0.78rem;
            font-weight: 700;
        }
        .metric-value {
            margin-top: 8px;
            font-size: 1.35rem;
            font-weight: 800;
            color: #0f172a;
        }
        div[data-testid="stTabs"] button[aria-selected="true"] {
            color: var(--app-blue) !important;
        }
        div[data-testid="stTabs"] button[aria-selected="true"] p {
            color: var(--app-blue) !important;
            font-weight: 700 !important;
        }
        div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
            background-color: var(--app-blue) !important;
        }
        div[data-testid="stTabs"] button:hover p {
            color: var(--app-blue) !important;
        }
        @media (max-width: 900px) {
            .auth-title { margin-top: 34px; }
            .auth-art { min-height: 360px; border-left: 0; border-top: 1px solid #edf2fb; }
            .metric-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .chat-bubble { max-width: 92%; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def brand_html() -> str:
    return '<div class="fin-brand"><span class="fin-mark">F</span><span>FinRAG Chatbot</span></div>'
