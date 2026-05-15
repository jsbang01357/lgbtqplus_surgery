import streamlit as st
from datetime import datetime
from app.core_utils import get_now
from app.storage import render_file_manager
from app.memo import render_memo_manager
from app.ai import get_monthly_gemini_cost_label, render_ai
from app.tools import render_tools
from app.access_logger import log_access, get_access_logs
from app.auth import is_authenticated, login_screen, should_require_auth_for_all_pages
from app.idle_timeout import inject_idle_timeout

# --- 설정 ---
# ACCESS_LOG_BLOB 정의는 access_logger.py로 이동됨


def inject_global_styles():
    st.markdown(
        """
        <style>
        :root {
            --app-bg: #f3f6fb;
            --panel-bg: rgba(255, 255, 255, 0.92);
            --panel-border: rgba(15, 23, 42, 0.08);
            --panel-shadow: 0 20px 45px rgba(15, 23, 42, 0.08);
            --accent: #274c9a;
            --accent-strong: #1a2f63;
            --accent-soft: #e9effc;
            --text-main: #18212b;
            --text-muted: #61707d;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(39, 76, 154, 0.12), transparent 28%),
                linear-gradient(180deg, #f8faff 0%, var(--app-bg) 100%);
        }

        [data-testid="stAppViewContainer"] > .main {
            background: transparent;
        }

        [data-testid="stHeader"] {
            background: rgba(243, 246, 251, 0.82);
            backdrop-filter: blur(10px);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #14213f 0%, #1d3260 100%);
            border-right: 1px solid rgba(26, 47, 99, 0.12);
        }

        [data-testid="stSidebar"] > div:first-child {
            background: linear-gradient(180deg, #14213f 0%, #1d3260 100%);
        }

        [data-testid="stSidebar"] .block-container {
            padding-top: 1.2rem;
            padding-bottom: 1rem;
        }

        .app-shell {
            margin-bottom: 1.1rem;
            padding: 1.2rem 1.2rem 0.2rem 1.2rem;
            text-align: left;
        }

        .app-shell__eyebrow {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: rgba(255, 255, 255, 0.72);
            margin-bottom: 0.35rem;
        }

        .app-shell__title {
            font-size: 2.05rem;
            font-weight: 700;
            color: #ffffff !important;
            margin: 0;
        }

        .app-shell__subtitle {
            margin: 0.45rem 0 0 0;
            font-size: 0.88rem;
            line-height: 1.5;
            color: rgba(255, 255, 255, 0.82) !important;
        }

        .sidebar-section-label {
            margin: 0.5rem 0 0.55rem 0.2rem;
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: rgba(255, 255, 255, 0.65);
        }

        [data-testid="stSidebar"] .stButton > button {
            justify-content: flex-start;
            min-height: 2.9rem;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: rgba(255, 255, 255, 0.08);
            color: #f9fcfb;
            font-weight: 600;
            box-shadow: none;
            transition: all 0.18s ease;
        }

        [data-testid="stSidebar"] .stButton > button:hover {
            border-color: rgba(255, 255, 255, 0.18);
            background: rgba(255, 255, 255, 0.14);
            color: #ffffff;
        }

        [data-testid="stSidebar"] .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #f2f6ff 0%, #dbe7ff 100%);
            color: var(--accent-strong) !important;
            border-color: rgba(255, 255, 255, 0.55);
            box-shadow: 0 12px 28px rgba(10, 24, 20, 0.18);
        }

        [data-testid="stSidebar"] .stButton > button[kind="primary"] *,
        [data-testid="stSidebar"] .stButton > button[kind="primary"] p,
        [data-testid="stSidebar"] .stButton > button[kind="primary"] span,
        [data-testid="stSidebar"] .stButton > button[kind="primary"] div {
            color: var(--accent-strong) !important;
            -webkit-text-fill-color: var(--accent-strong) !important;
        }

        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: #f7faff;
        }

        .app-shell,
        .app-shell * {
            color: #f7faff !important;
        }

        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 2rem;
            max-width: 1220px;
        }

        .content-hero {
            border: 1px solid var(--panel-border);
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(244, 247, 255, 0.94));
            border-radius: 18px;
            padding: 1.35rem 1.5rem;
            box-shadow: var(--panel-shadow);
            margin-bottom: 1rem;
        }

        .content-hero--auth {
            margin-top: 1.45rem;
        }

        .content-hero__eyebrow {
            margin: 0 0 0.45rem 0;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--accent);
            font-weight: 700;
        }

        .content-hero__title {
            margin: 0;
            font-size: 1.65rem;
            line-height: 1.2;
            color: var(--text-main);
        }

        .content-hero__body {
            margin: 0.55rem 0 0 0;
            font-size: 0.95rem;
            line-height: 1.6;
            color: var(--text-muted);
        }

        .surface-card {
            border: 1px solid var(--panel-border);
            background: var(--panel-bg);
            border-radius: 16px;
            padding: 1.2rem 1.25rem;
            box-shadow: var(--panel-shadow);
            backdrop-filter: blur(10px);
            margin-bottom: 1rem;
        }

        .surface-card--compact {
            padding: 1rem 1.1rem;
        }

        .surface-card__title {
            margin: 0;
            font-size: 1rem;
            color: var(--text-main);
            font-weight: 700;
        }

        .surface-card__body {
            margin: 0.35rem 0 0 0;
            color: var(--text-muted);
            font-size: 0.9rem;
            line-height: 1.55;
        }

        .file-card__header {
            display: flex;
            align-items: flex-start;
            gap: 0.95rem;
        }

        .file-card__icon {
            width: 3rem;
            height: 3.5rem;
            flex: 0 0 3rem;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 14px;
            background: linear-gradient(180deg, rgba(242, 246, 255, 0.9), rgba(233, 239, 252, 0.75));
            border: 1px solid rgba(39, 76, 154, 0.08);
        }

        .file-card__icon svg {
            width: 2.5rem;
            height: auto;
            display: block;
        }

        .file-card__meta {
            min-width: 0;
            flex: 1 1 auto;
        }

        .file-card__meta-row {
            display: flex;
            align-items: center;
            gap: 0.55rem;
            margin-bottom: 0.25rem;
        }

        .file-card__type {
            display: inline-flex;
            align-items: center;
            height: 1.5rem;
            padding: 0 0.55rem;
            border-radius: 999px;
            background: var(--accent-soft);
            color: var(--accent-strong);
            font-size: 0.72rem;
            font-weight: 700;
        }

        .tool-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.45rem 0.7rem;
            border-radius: 999px;
            background: var(--accent-soft);
            color: var(--accent-strong);
            font-size: 0.82rem;
            font-weight: 700;
            margin-bottom: 0.8rem;
        }

        .section-block {
            margin: 0.95rem 0 0.65rem 0;
            padding: 0 0 0.75rem 0;
            border-bottom: 1px solid rgba(15, 23, 42, 0.08);
        }

        .section-block--spacious {
            margin-top: 2.15rem;
            padding-top: 0.35rem;
        }

        .section-block--spacious::before {
            content: "";
            display: block;
            width: 100%;
            height: 1px;
            margin-bottom: 1rem;
            background: linear-gradient(90deg, rgba(39, 76, 154, 0.16), rgba(39, 76, 154, 0.02));
        }

        .section-block--spacious.section-block--danger::before {
            background: linear-gradient(90deg, rgba(190, 47, 47, 0.18), rgba(190, 47, 47, 0.02));
        }

        .section-block__eyebrow {
            margin: 0 0 0.2rem 0;
            font-size: 0.72rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--accent);
            font-weight: 700;
        }

        .section-block__title {
            margin: 0;
            font-size: 1rem;
            line-height: 1.35;
            color: var(--text-main);
            font-weight: 700;
        }

        .section-block__body {
            margin: 0.3rem 0 0 0;
            font-size: 0.9rem;
            line-height: 1.5;
            color: var(--text-muted);
        }

        .section-block--danger {
            border-bottom-color: rgba(184, 31, 31, 0.16);
        }

        .section-block--danger .section-block__eyebrow {
            color: #be2f2f;
        }

        .section-block--danger .section-block__title {
            color: #8f1f1f;
        }

        .section-block--danger .section-block__body {
            color: #8b4d4d;
        }

        .st-key-danger_clear_files button,
        .st-key-danger_clear_memos button,
        .st-key-danger_clear_logs button {
            background: linear-gradient(135deg, #c53b3b 0%, #a61f1f 100%) !important;
            color: #fff7f7 !important;
            border: 1px solid rgba(122, 18, 18, 0.28) !important;
            box-shadow: 0 14px 28px rgba(166, 31, 31, 0.18) !important;
        }

        .st-key-danger_clear_files button *,
        .st-key-danger_clear_memos button *,
        .st-key-danger_clear_logs button * {
            color: #fff7f7 !important;
            -webkit-text-fill-color: #fff7f7 !important;
        }

        .st-key-danger_clear_files button:hover,
        .st-key-danger_clear_memos button:hover,
        .st-key-danger_clear_logs button:hover {
            background: linear-gradient(135deg, #d24646 0%, #b32525 100%) !important;
            border-color: rgba(122, 18, 18, 0.38) !important;
        }

        .stTextArea textarea,
        .stTextInput input,
        .stSelectbox [data-baseweb="select"] > div,
        .stMultiSelect [data-baseweb="select"] > div {
            border-radius: 12px !important;
            border-color: rgba(15, 23, 42, 0.12) !important;
            background: rgba(255, 255, 255, 0.92) !important;
        }

        .stButton > button {
            border-radius: 12px;
            font-weight: 600;
            white-space: normal;
            line-height: 1.4;
            height: auto;
            min-height: 2.9rem;
        }

        [data-testid="metric-container"] {
            border-radius: 14px;
            border: 1px solid var(--panel-border);
            background: rgba(255, 255, 255, 0.9);
            box-shadow: 0 14px 28px rgba(15, 23, 42, 0.05);
            padding: 0.85rem 1rem;
        }

        [data-testid="metric-container"] [data-testid="stMetricLabel"],
        [data-testid="metric-container"] [data-testid="stMetricValue"] {
            overflow-wrap: anywhere;
        }

        [data-testid="stForm"] {
            border: 1px solid var(--panel-border);
            background: rgba(255, 255, 255, 0.92);
            border-radius: 18px;
            padding: 1.2rem 1.2rem 1.1rem 1.2rem;
            box-shadow: var(--panel-shadow);
        }

        [data-testid="stForm"] .stButton,
        [data-testid="stForm"] [data-testid="stFormSubmitButton"] {
            margin-bottom: 0.35rem;
        }

        .sidebar-footer {
            position: static;
            width: 100%;
            padding: 0 0.9rem;
            margin-top: 1.2rem;
            box-sizing: border-box;
        }

        @media (min-width: 576px) {
            .sidebar-footer {
                position: fixed;
                bottom: 18px;
                left: 0;
                width: 300px;
                padding: 0 1.1rem;
                z-index: 99;
            }
        }

        .sidebar-footer .status-box {
            background: rgba(255, 255, 255, 0.1);
            padding: 0.95rem 1rem;
            border-radius: 14px;
            border: 1px solid rgba(255, 255, 255, 0.12);
            box-shadow: none;
            margin-bottom: 0.7rem;
            box-sizing: border-box;
        }

        .status-box__row {
            display: flex;
            justify-content: space-between;
            gap: 0.8rem;
            align-items: center;
            min-height: 2.45rem;
            padding: 0.35rem 0.75rem;
            font-size: 0.82rem;
            color: #f9fcfb;
            font-weight: 600;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: rgba(255, 255, 255, 0.08);
            margin-bottom: 0.55rem;
            box-sizing: border-box;
        }

        .status-box__row:last-child {
            margin-bottom: 0;
        }

        .status-box__value {
            color: #f7faff;
            font-weight: 700;
            text-align: right;
            overflow-wrap: anywhere;
        }

        .sidebar-footer__meta {
            margin: 0;
            padding: 0 0.1rem;
            color: rgba(255, 255, 255, 0.36);
            font-size: 0.74rem;
            line-height: 1.5;
            font-weight: 600;
        }

        [data-testid="stSidebarNav"]::after {
            content: "";
            display: block;
            height: 24px;
        }

        @media (min-width: 576px) {
            [data-testid="stSidebarNav"]::after {
                height: 136px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def handle_access_log():
    if "last_access_display" not in st.session_state:
        # 최초 로딩 시 최신 기록 하나 가져오기 (표시용)
        logs = get_access_logs()
        if logs:
            st.session_state.last_access_display = logs[0].get("time", "기록 없음")
        else:
            st.session_state.last_access_display = "최초 접속"

        # 새로운 로그 직접 기록
        log_access()


def format_last_access_display(raw_value: str) -> str:
    if not raw_value or raw_value in {"기록 없음", "최초 접속", "기본 없음"}:
        return raw_value or "기록 없음"

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            parsed = datetime.strptime(raw_value, fmt)
            return parsed.strftime("%m/%d %H:%M")
        except ValueError:
            continue
    return raw_value


def get_sidebar_ai_cost_display() -> str:
    try:
        return get_monthly_gemini_cost_label()
    except Exception:
        return "확인 실패"


def check_for_updates():
    """
    if "last_memo_mtime" not in st.session_state:
        st.session_state.last_memo_mtime = os.path.getmtime(MEMO_DIR) if os.path.exists(MEMO_DIR) else 0
    if "last_file_mtime" not in st.session_state:
        st.session_state.last_file_mtime = os.path.getmtime(UPLOAD_DIR) if os.path.exists(UPLOAD_DIR) else 0

    cur_memo_mtime = os.path.getmtime(MEMO_DIR) if os.path.exists(MEMO_DIR) else 0
    cur_file_mtime = os.path.getmtime(UPLOAD_DIR) if os.path.exists(UPLOAD_DIR) else 0

    updated = False
    if cur_memo_mtime > st.session_state.last_memo_mtime:
        st.session_state.last_memo_mtime = cur_memo_mtime
        updated = True
    if cur_file_mtime > st.session_state.last_file_mtime:
        st.session_state.last_file_mtime = cur_file_mtime
        updated = True

    if updated:
        st.toast("🔄 외부에서 파일/데이터가 업데이트되었습니다!", icon="🔄")
    """
    return


def set_menu(menu_name):
    st.session_state.menu = menu_name
    st.query_params["tab"] = menu_name


def main():
    st.set_page_config(page_title="Jisong Cloud", layout="wide")
    inject_global_styles()
    inject_idle_timeout()

    handle_access_log()
    check_for_updates()

    st.sidebar.markdown(
        """
        <div class="app-shell">
            <h1 class="app-shell__title">☁️ Jisong Cloud</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "menu" not in st.session_state:
        if "tab" in st.query_params:
            st.session_state.menu = st.query_params["tab"]
        else:
            st.session_state.menu = "files"

    if should_require_auth_for_all_pages() and not is_authenticated():
        login_screen()
        return

    st.sidebar.markdown(
        '<p class="sidebar-section-label">Workspace</p>',
        unsafe_allow_html=True,
    )

    btn_files_type = "primary" if st.session_state.menu == "files" else "secondary"
    btn_memos_type = "primary" if st.session_state.menu == "memos" else "secondary"
    btn_ai_type = "primary" if st.session_state.menu == "ai" else "secondary"
    btn_tools_type = "primary" if st.session_state.menu == "tools" else "secondary"

    if st.sidebar.button("📂 웹하드", type=btn_files_type, use_container_width=True):
        set_menu("files")
        st.rerun()

    if st.sidebar.button("📋 메모장", type=btn_memos_type, use_container_width=True):
        set_menu("memos")
        st.rerun()

    if st.sidebar.button("✨ AI", type=btn_ai_type, use_container_width=True):
        set_menu("ai")
        st.rerun()

    if st.sidebar.button("🛠️ 도구모음", type=btn_tools_type, use_container_width=True):
        set_menu("tools")
        st.rerun()

    st.sidebar.markdown(
        f"""
            <div class="sidebar-footer">
                <div class="status-box">
                    <div class="status-box__row">
                        <span>현재 시간</span>
                        <span class="status-box__value">{get_now().strftime("%H:%M")}</span>
                    </div>
                    <div class="status-box__row">
                    <span>직전 접속</span>
                    <span class="status-box__value">{format_last_access_display(st.session_state.last_access_display)}</span>
                </div>
                    <div class="status-box__row">
                    <span>이번 달 AI</span>
                    <span class="status-box__value">{get_sidebar_ai_cost_display()}</span>
                </div>
            </div>
            <p class="sidebar-footer__meta">Jisong Bang 2026<br>Ver 4.0 (260513)</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- 라우팅 ---
    if st.session_state.menu == "files":
        if not is_authenticated():
            login_screen()
        else:
            render_file_manager()
    elif st.session_state.menu == "memos":
        if not is_authenticated():
            login_screen()
        else:
            render_memo_manager()
    elif st.session_state.menu == "ai":
        if not is_authenticated():
            login_screen()
        else:
            render_ai()
    elif st.session_state.menu == "tools":
        render_tools()


if __name__ == "__main__":
    main()
