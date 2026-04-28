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
            --app-shell-margin: 24px;
            --app-shell-vertical-space: 48px;
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
            max-width: none;
            padding: var(--app-shell-margin);
        }
        .stButton > button, .stDownloadButton > button {
            border-radius: 6px;
            border: 1px solid var(--app-border);
            box-shadow: none;
            font-weight: 600;
            min-height: 2.5rem;
        }
        div[data-testid="stButton"],
        .stButton {
            width: 100% !important;
            min-width: 0 !important;
        }
        div[data-testid="stButton"] > button,
        .stButton > button {
            width: 100% !important;
            white-space: nowrap !important;
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
            min-height: calc(100vh - var(--app-shell-vertical-space));
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-wrap-marker) {
            min-height: calc(100vh - var(--app-shell-vertical-space));
            overflow: hidden;
        }
        .fin-shell-marker, .auth-wrap-marker, .auth-panel-marker, .side-card-marker, .side-nav-marker, .side-nav-start, .side-nav-end, .chat-workspace-marker, .chat-header-controls-marker, .chat-transcript-marker, .chat-input-anchor, .chat-control-marker, .topbar-row-marker {
            display: none;
        }
        [data-testid="stElementContainer"]:has(.chat-control-marker),
        [data-testid="stElementContainer"]:has(.chat-header-controls-marker),
        [data-testid="stElementContainer"]:has(.topbar-row-marker) {
            display: none;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.fin-shell-marker) div[data-testid="stVerticalBlock"] {
            gap: 0;
        }
        div[data-testid="stHorizontalBlock"]:has(.topbar-row-marker) {
            height: 52px;
            border-bottom: 1px solid var(--app-border);
            display: grid !important;
            grid-template-columns: minmax(0, 1fr) 150px 98px;
            align-items: center;
            column-gap: 10px;
            padding: 0 18px;
            background: rgba(255, 255, 255, 0.92);
            margin: 30px 12px 0;
            width: calc(100% - 24px);
            box-sizing: border-box;
        }
        div[data-testid="stHorizontalBlock"]:has(.topbar-row-marker) > div[data-testid="column"] {
            width: 100% !important;
            min-width: 0 !important;
            flex: unset !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.topbar-row-marker) div[data-testid="stButton"] > button {
            width: 100%;
            min-height: 28px;
            height: 30px;
            padding: 0 10px;
            font-size: 0.78rem;
        }
        .fin-brand {
            display: flex;
            align-items: center;
            gap: 9px;
            font-weight: 800;
            font-size: 2rem;
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
            justify-content: flex-end;
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
        .auth-title {
            margin: 70px 0 8px;
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
            min-height: 700px;
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            min-width: 0;
            padding: 0 0 0 0;
            box-sizing: border-box;
            overflow: visible;
        }
        div[data-testid="stHorizontalBlock"]:has(.auth-art-image) {
            display: grid !important;
            grid-template-columns: minmax(930px, 0.84fr) minmax(345px, 0.16fr);
            column-gap: 0;
            width: 100%;
            max-width: 100%;
            min-height: 700px;
            align-items: stretch;
            overflow: visible;
            box-sizing: border-box;
        }
        div[data-testid="stHorizontalBlock"]:has(.auth-art-image) > div[data-testid="column"] {
            width: 100% !important;
            min-width: 0 !important;
            flex: unset !important;
        }
        div[data-testid="column"]:has(.auth-panel-marker) {
            padding: 48px clamp(24px, 3vw, 52px) 18px clamp(28px, 5vw, 72px);
            box-sizing: border-box;
        }
        div[data-testid="column"]:has(.auth-art-image) {
            min-height: 700px;
            min-width: 0;
            overflow: visible;
        }
        div[data-testid="column"]:has(.auth-art-image) [data-testid="stElementContainer"],
        div[data-testid="column"]:has(.auth-art-image) [data-testid="stMarkdownContainer"] {
            width: 100% !important;
            max-width: none !important;
            overflow: visible !important;
        }
        .auth-bank-svg {
            width: min(560px, 90%);
            height: auto;
            display: block;
        }
        .auth-art-image {
            width: clamp(300px, 50vw, 700px);
            flex: 0 0 auto;
            max-width: none;
            display: flex;
            align-items: center;
            justify-content: center;
            filter: drop-shadow(0 22px 28px rgba(37, 99, 235, 0.16));
            margin-top: 32px;
            transform: translateX(80px);
        }
        .auth-art-image img {
            display: block;
            width: 100% !important;
            max-width: none !important;
            height: auto !important;
            transform-origin: center;
        }
        .auth-copyright {
            margin-top: auto;
            padding-top: 22px;
            color: #94a3b8;
            font-size: 0.76rem;
            line-height: 1.4;
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
        [data-testid="stElementContainer"]:has(.side-card-marker) {
            display: none;
        }
        div[data-testid="column"]:has(.side-card-marker) {
            min-height: calc(100vh - 89px);
            border-right: 1px solid var(--app-border);
            background: rgba(249, 251, 255, 0.86);
            padding: 14px 12px 16px 12px;
            min-width: 245px;
            max-width: 245px;
            width: 100% !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.side-card-marker) {
            display: grid !important;
            grid-template-columns: 245px minmax(0, 1fr);
            column-gap: 14px;
            margin: 0 12px 20px;
            width: calc(100% - 24px);
            align-items: start;
        }
        div[data-testid="stHorizontalBlock"]:has(.side-card-marker) > div[data-testid="column"] {
            align-self: start;
            min-width: 0;
            width: 100% !important;
            flex: unset !important;
        }
        div[data-testid="column"]:has(.side-card-marker) div[data-testid="stVerticalBlock"] {
            align-items: stretch;
            justify-content: flex-start;
            gap: 0;
        }
        div[data-testid="column"]:has(.side-card-marker) div[data-testid="stButton"],
        div[data-testid="column"]:has(.side-card-marker) .stButton,
        div[data-testid="column"]:has(.side-card-marker) [data-testid="stElementContainer"] {
            width: 100%;
            min-width: 0;
        }
        div[data-testid="column"]:has(.side-card-marker) div[data-testid="stButton"] {
            margin-bottom: 0.35rem;
        }
        div[data-testid="column"]:has(.side-card-marker) .stButton {
            margin-bottom: 0.35rem;
        }
        div[data-testid="column"]:has(.side-card-marker) div[data-testid="stButton"] > button,
        div[data-testid="column"]:has(.side-card-marker) .stButton > button {
            width: 100%;
            min-width: 221px;
            white-space: nowrap;
            justify-content: center;
            padding-left: 14px;
            padding-right: 14px;
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
            padding: 14px 0 18px;
            width: 100%;
            box-sizing: border-box;
        }
        div[data-testid="stVerticalBlock"]:has(.chat-workspace-marker) {
            min-height: calc(100vh - 88px);
            display: flex;
            flex-direction: column;
            width: 100%;
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
        div[data-testid="stHorizontalBlock"]:has(.chat-control-marker.mode) {
            align-items: flex-end;
            margin: 0.35rem 0 0.75rem;
        }
        div[data-testid="stHorizontalBlock"]:has(.chat-control-marker.mode) > div[data-testid="column"] {
            min-width: 0;
        }
        .chat-setting-label {
            min-height: 40px;
            display: flex;
            align-items: center;
            color: #475569;
            font-size: 0.78rem;
            font-weight: 700;
            white-space: nowrap;
        }
        [data-testid="stElementContainer"]:has(.chat-control-marker.mode) + [data-testid="stElementContainer"] div[data-testid="stSelectbox"] {
            width: 100%;
        }
        [data-testid="stElementContainer"]:has(.chat-control-marker.language) + [data-testid="stElementContainer"] div[data-testid="stSelectbox"] {
            width: 100%;
        }
        [data-testid="stElementContainer"]:has(.chat-control-marker.topk) + [data-testid="stElementContainer"] div[data-testid="stNumberInput"] {
            width: 100%;
        }
        [data-testid="stElementContainer"]:has(.chat-control-marker) + [data-testid="stElementContainer"] div[data-testid="stSelectbox"] > div,
        [data-testid="stElementContainer"]:has(.chat-control-marker) + [data-testid="stElementContainer"] div[data-testid="stNumberInput"] input {
            min-height: 40px;
        }
        [data-testid="stElementContainer"]:has(.chat-control-marker) + [data-testid="stElementContainer"] div[data-testid="stSelectbox"],
        [data-testid="stElementContainer"]:has(.chat-control-marker) + [data-testid="stElementContainer"] div[data-testid="stNumberInput"] {
            margin-top: 0;
        }
        div[data-testid="stVerticalBlock"]:has(.chat-transcript-marker) {
            padding: 8px 0 4px;
        }
        div[data-testid="stChatInput"] {
            position: sticky;
            bottom: 1rem;
            z-index: 50;
            background: rgba(255, 255, 255, 0.96);
            border-radius: 10px;
            padding: 0.25rem 0 0;
        }
        div[data-testid="stChatInput"] > div {
            border: 1px solid var(--app-blue) !important;
            box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.12) !important;
        }
        div[data-testid="stChatInput"] textarea {
            border: 0 !important;
            box-shadow: none !important;
        }
        div[data-testid="stChatInput"] textarea:focus {
            border: 0 !important;
            box-shadow: none !important;
        }
        div[data-testid="stChatInput"] button {
            border: 0 !important;
        }
        .bubble-row {
            display: flex;
            margin: 12px 0;
            gap: 10px;
            align-items: flex-start;
            min-width: 0;
        }
        .bubble-row.user {
            justify-content: flex-end;
        }
        .chat-avatar {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            flex: 0 0 auto;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        .chat-avatar.user {
            background: #dbe7f6;
            color: #64748b;
            font-size: 1rem;
            font-weight: 800;
        }
        .chat-avatar.bot {
            background-color: #eef4ff;
            background-position: center;
            background-repeat: no-repeat;
            background-size: cover;
            border: 1px solid #dbe7f6;
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
            overflow-wrap: anywhere;
            word-break: break-word;
        }
        .chat-bubble.user {
            background: var(--app-blue);
            color: #fff;
            border-color: var(--app-blue);
        }
        .loading-dots {
            min-width: 63px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            padding: 18px 21px;
        }
        .loading-dots span {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #64748b;
            animation: dotPulse 1.1s infinite ease-in-out;
        }
        .loading-dots span:nth-child(2) {
            animation-delay: 0.16s;
        }
        .loading-dots span:nth-child(3) {
            animation-delay: 0.32s;
        }
        @keyframes dotPulse {
            0%, 80%, 100% {
                opacity: 0.35;
                transform: translateY(0);
            }
            40% {
                opacity: 1;
                transform: translateY(-2px);
            }
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
            padding: 0 0 10px 58px;
            margin-top: -4px;
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
        /* Authenticated app layout reset: keep the shell simple and predictable. */
        .block-container {
            max-width: none !important;
            padding: var(--app-shell-margin) !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.fin-shell-marker) {
            width: 100% !important;
            min-height: calc(100vh - var(--app-shell-vertical-space));
            overflow: hidden;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.fin-shell-marker) > div {
            width: 100% !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.fin-shell-marker) div[data-testid="stVerticalBlock"] {
            gap: 0 !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.topbar-row-marker) {
            display: grid !important;
            grid-template-columns: minmax(0, 1fr) max-content 104px !important;
            align-items: center !important;
            gap: 12px !important;
            width: calc(100% - 24px) !important;
            height: 52px !important;
            margin: 30px 12px 0 !important;
            padding: 0 18px !important;
            border-bottom: 1px solid var(--app-border);
            background: rgba(255, 255, 255, 0.92);
            box-sizing: border-box;
        }
        div[data-testid="stHorizontalBlock"]:has(.topbar-row-marker) > div[data-testid="column"] {
            width: 100% !important;
            min-width: 0 !important;
            flex: unset !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.topbar-row-marker) div[data-testid="stButton"] > button {
            width: 100% !important;
            min-width: 92px !important;
            min-height: 30px !important;
            height: 30px !important;
            padding: 0 10px !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.side-card-marker) {
            display: grid !important;
            grid-template-columns: 245px minmax(0, 1fr) !important;
            gap: 14px !important;
            width: calc(100% - 24px) !important;
            margin: 0 12px 20px !important;
            align-items: start !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.side-card-marker) > div[data-testid="column"] {
            width: 100% !important;
            min-width: 0 !important;
            flex: unset !important;
            align-self: start !important;
        }
        div[data-testid="column"]:has(.side-card-marker) {
            width: 245px !important;
            min-width: 245px !important;
            max-width: 245px !important;
            padding: 14px 12px 16px !important;
            box-sizing: border-box !important;
        }
        div[data-testid="column"]:has(.side-card-marker) div[data-testid="stButton"],
        div[data-testid="column"]:has(.side-card-marker) [data-testid="stElementContainer"] {
            width: 100% !important;
        }
        div[data-testid="column"]:has(.side-card-marker) div[data-testid="stButton"] > button {
            width: 100% !important;
            min-width: 0 !important;
            white-space: nowrap !important;
            justify-content: center !important;
        }
        .content-pad {
            width: 100% !important;
            padding: 14px 0 18px !important;
            box-sizing: border-box !important;
        }
        div[data-testid="stVerticalBlock"]:has(.chat-workspace-marker),
        div[data-testid="column"]:has(.chat-workspace-marker),
        div[data-testid="column"]:has(.content-pad) {
            width: 100% !important;
            min-width: 0 !important;
        }
        div[data-testid="stChatInput"] {
            width: 100% !important;
        }
        .fin-topbar {
            height: 78px !important;
            min-height: 78px !important;
            border-bottom: 1px solid var(--app-border);
            display: flex !important;
            align-items: center !important;
            justify-content: space-between !important;
            padding: 0 18px !important;
            background: rgba(255, 255, 255, 0.92);
            margin: 8px 12px 0 !important;
            width: calc(100% - 24px) !important;
            box-sizing: border-box !important;
        }
        .fin-topbar-actions {
            display: flex;
            align-items: center;
            gap: 12px;
            flex: 0 0 auto;
        }
        .fin-user {
            display: inline-flex !important;
            align-items: center !important;
            gap: 8px !important;
            white-space: nowrap !important;
            flex: 0 0 auto !important;
            min-width: max-content !important;
        }
        .fin-avatar {
            width: 28px !important;
            height: 28px !important;
            min-width: 28px !important;
            flex: 0 0 28px !important;
            aspect-ratio: 1 / 1 !important;
            border-radius: 50% !important;
            line-height: 1 !important;
        }
        .fin-logout {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 92px;
            height: 30px;
            border: 1px solid var(--app-border);
            border-radius: 6px;
            color: #111827;
            text-decoration: none !important;
            font-weight: 600;
            font-size: 0.86rem;
            background: #fff;
        }
        .fin-logout:hover {
            border-color: var(--app-blue);
            color: var(--app-blue);
        }
        div[data-testid="stHorizontalBlock"]:has(.side-nav-marker) {
            display: grid !important;
            grid-template-columns: 280px minmax(0, 1fr) !important;
            gap: 14px !important;
            width: calc(100% - 24px) !important;
            margin: 0 12px 20px !important;
            align-items: start !important;
        }
        div[data-testid="column"]:has(.side-nav-marker) {
            width: 280px !important;
            min-width: 280px !important;
            max-width: 280px !important;
            padding: 14px 10px 16px !important;
            box-sizing: border-box !important;
        }
        div[data-testid="column"]:has(.side-nav-marker) div[data-testid="stButton"] {
            width: 100% !important;
            margin-bottom: 12px !important;
        }
        div[data-testid="column"]:has(.side-nav-marker) div[data-testid="stButton"] > button {
            width: 100% !important;
            min-height: 42px !important;
            white-space: nowrap !important;
            justify-content: center !important;
        }
        div[data-testid="column"]:has(.side-nav-marker) .recent-title {
            width: 260px !important;
            margin: 10px 0 !important;
            white-space: nowrap !important;
            word-break: keep-all !important;
            overflow-wrap: normal !important;
            font-size: 1.56rem !important;
            line-height: 1.2 !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.side-nav-start) {
            display: grid !important;
            grid-template-columns: 284px minmax(0, 1fr) !important;
            gap: 14px !important;
            width: calc(100% - 24px) !important;
            margin: 0 12px 20px !important;
            align-items: start !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.side-nav-start) > div[data-testid="column"] {
            min-width: 0 !important;
            flex: unset !important;
        }
        div[data-testid="column"]:has(.side-nav-start) {
            width: 284px !important;
            min-width: 284px !important;
            max-width: 284px !important;
            padding: 14px 10px 16px !important;
            box-sizing: border-box !important;
        }
        div[data-testid="column"]:has(.side-nav-start) [data-testid="stElementContainer"],
        div[data-testid="column"]:has(.side-nav-start) [data-testid="stButton"],
        div[data-testid="column"]:has(.side-nav-start) .stButton {
            width: 264px !important;
            min-width: 264px !important;
            max-width: 264px !important;
            box-sizing: border-box !important;
        }
        div[data-testid="column"]:has(.side-nav-start) [data-testid="stButton"] > button,
        div[data-testid="column"]:has(.side-nav-start) .stButton > button,
        div[data-testid="column"]:has(.side-nav-start) button {
            width: 264px !important;
            min-width: 264px !important;
            max-width: 264px !important;
            min-height: 42px !important;
            box-sizing: border-box !important;
            white-space: nowrap !important;
            justify-content: center !important;
        }
        div[data-testid="column"]:has(.side-nav-start) .recent-title {
            width: 264px !important;
            margin: 10px 0 !important;
            white-space: nowrap !important;
            word-break: keep-all !important;
            overflow-wrap: normal !important;
            font-size: 1.56rem !important;
            line-height: 1.2 !important;
        }
        div[data-testid="stButton"] {
            width: 264px !important;
            min-width: 264px !important;
            max-width: 264px !important;
        }
        div[data-testid="stButton"] button,
        button[data-testid="stBaseButton-primary"],
        button[data-testid="stBaseButton-secondary"] {
            width: 264px !important;
            min-width: 264px !important;
            max-width: 264px !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: clip !important;
            justify-content: center !important;
        }
        div[data-testid="column"]:has(.auth-panel-marker) div[data-testid="stButton"],
        div[data-testid="column"]:has(.auth-panel-marker) div[data-testid="stButton"] button {
            width: 100% !important;
            min-width: 0 !important;
            max-width: none !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.auth-art-image) > div[data-testid="column"]:first-child div[data-testid="stButton"],
        div[data-testid="stHorizontalBlock"]:has(.auth-art-image) > div[data-testid="column"]:first-child div[data-testid="stButton"] button {
            width: 100% !important;
            min-width: 0 !important;
            max-width: none !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.auth-art-image) div[data-testid="stButton"] button {
            min-height: 42px !important;
            height: 42px !important;
        }
        @media (max-width: 900px) {
            :root {
                --app-shell-margin: 12px;
                --app-shell-vertical-space: 24px;
            }
            .block-container {
                padding: var(--app-shell-margin) !important;
            }
            div[data-testid="column"]:has(.auth-panel-marker) {
                padding: 36px 0 20px 34px;
            }
            div[data-testid="stHorizontalBlock"]:has(.auth-art-image) {
                grid-template-columns: minmax(0, 0.76fr) minmax(0, 0.24fr);
            }
            div[data-testid="stHorizontalBlock"]:has(.topbar-row-marker) {
                margin: 12px 12px 0;
                width: calc(100% - 24px);
                grid-template-columns: minmax(0, 1fr) 136px 92px;
            }
            div[data-testid="stHorizontalBlock"]:has(.side-card-marker) {
                margin: 0 12px 12px;
                width: calc(100% - 24px);
                grid-template-columns: 240px minmax(0, 1fr);
            }
            div[data-testid="column"]:has(.side-card-marker) {
                min-width: 240px;
                max-width: 240px;
                padding-top: 8px;
            }
            .content-pad {
                padding: 14px 6px 16px;
            }
            div[data-testid="stHorizontalBlock"]:has(.chat-control-marker.mode) {
                display: grid !important;
                grid-template-columns: repeat(2, minmax(160px, 1fr));
                column-gap: 0.75rem;
                row-gap: 0.5rem;
                align-items: end;
            }
            div[data-testid="stHorizontalBlock"]:has(.chat-control-marker.mode) > div[data-testid="column"] {
                width: 100% !important;
                flex: unset !important;
                min-width: 0;
            }
            div[data-testid="stHorizontalBlock"]:has(.page-title):has(.chat-setting-label) {
                flex-wrap: wrap;
                row-gap: 0.5rem;
            }
            div[data-testid="stHorizontalBlock"]:has(.page-title):has(.chat-setting-label) > div[data-testid="column"] {
                min-width: 0;
                flex: 1 1 150px !important;
            }
            div[data-testid="stHorizontalBlock"]:has(.page-title):has(.chat-setting-label) > div[data-testid="column"]:has(.page-title) {
                flex: 1 1 100% !important;
                width: 100% !important;
            }
            div[data-testid="stHorizontalBlock"]:has(.chat-setting-label) {
                align-items: center;
            }
            div[data-testid="stHorizontalBlock"]:has(.chat-setting-label) > div[data-testid="column"] {
                min-width: 0;
            }
            .chat-setting-label {
                min-height: 36px;
            }
            [data-testid="stElementContainer"]:has(.chat-control-marker.mode) + [data-testid="stElementContainer"] div[data-testid="stSelectbox"],
            [data-testid="stElementContainer"]:has(.chat-control-marker.language) + [data-testid="stElementContainer"] div[data-testid="stSelectbox"],
            [data-testid="stElementContainer"]:has(.chat-control-marker.topk) + [data-testid="stElementContainer"] div[data-testid="stNumberInput"] {
                width: 100%;
                min-width: 0;
            }
            .auth-title { margin-top: 34px; }
            .auth-art {
                min-height: 700px;
                justify-content: center;
                padding-right: 18px;
                padding-left: 12px;
            }
            .auth-art-image {
                width: clamp(720px, 84vw, 1040px);
                margin-top: 32px;
                transform: translateX(80px);
            }
            .metric-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .chat-bubble { max-width: 92%; }
        }
        @media (max-width: 640px) {
            div[data-testid="stHorizontalBlock"]:has(.topbar-row-marker) {
                height: auto;
                min-height: 52px;
                grid-template-columns: minmax(0, 1fr);
                row-gap: 8px;
                padding: 12px;
            }
            .fin-user {
                padding-right: 96px;
                justify-content: flex-start;
            }
            .fin-brand {
                font-size: 1.35rem;
            }
            div[data-testid="stHorizontalBlock"]:has(.auth-art-image) {
                grid-template-columns: minmax(0, 1fr);
                min-height: calc(100vh - 2rem);
            }
            div[data-testid="column"]:has(.auth-panel-marker) {
                padding: 24px 22px 20px;
            }
            div[data-testid="column"]:has(.auth-art-image) {
                display: none;
            }
            div[data-testid="stHorizontalBlock"]:has(.chat-control-marker.mode) {
                grid-template-columns: minmax(0, 1fr);
            }
            div[data-testid="stHorizontalBlock"]:has(.page-title):has(.chat-setting-label) > div[data-testid="column"] {
                flex: 1 1 190px !important;
            }
            div[data-testid="stHorizontalBlock"]:has(.chat-setting-label) {
                flex-wrap: wrap;
                row-gap: 0;
            }
            div[data-testid="stHorizontalBlock"]:has(.chat-setting-label) > div[data-testid="column"]:has(.chat-setting-label),
            div[data-testid="stHorizontalBlock"]:has(.chat-setting-label) > div[data-testid="column"]:has(.chat-control-marker) {
                flex: 1 1 100% !important;
                width: 100% !important;
            }
            .chat-setting-label {
                min-height: 24px;
            }
            .chat-avatar {
                width: 38px;
                height: 38px;
            }
            .chat-bubble {
                max-width: calc(100% - 48px);
                padding: 10px 12px;
            }
            .disclaimer {
                padding-left: 48px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def brand_html() -> str:
    return '<div class="fin-brand"><span>FinRAG Chatbot</span></div>'
