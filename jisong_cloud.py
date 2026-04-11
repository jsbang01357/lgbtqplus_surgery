import streamlit as st

from app.core_utils import get_now
from app.storage import render_file_manager
from app.memo import render_memo_manager, MEMO_PREFIX
from app.tools import render_tools
from app.access_logger import log_access, get_access_logs

# --- 설정 ---
# ACCESS_LOG_BLOB 정의는 access_logger.py로 이동됨

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

def check_for_updates():
    '''
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
    '''
    return

def set_menu(menu_name):
    st.session_state.menu = menu_name
    st.query_params["tab"] = menu_name

def main():
    st.set_page_config(page_title="Jisong Cloud", layout="wide")
    
    handle_access_log()
    check_for_updates()

    st.sidebar.title("☁️ Jisong Cloud")
    
    if "menu" not in st.session_state:
        if "tab" in st.query_params:
            st.session_state.menu = st.query_params["tab"]
        else:
            st.session_state.menu = "files"

    btn_files_type = "primary" if st.session_state.menu == "files" else "secondary"
    btn_memos_type = "primary" if st.session_state.menu == "memos" else "secondary"
    btn_tools_type = "primary" if st.session_state.menu == "tools" else "secondary"

    if st.sidebar.button("📂 웹하드", type=btn_files_type, use_container_width=True):
        set_menu("files")
        st.rerun()
        
    if st.sidebar.button("📝 메모장", type=btn_memos_type, use_container_width=True):
        set_menu("memos")
        st.rerun()

    if st.sidebar.button("🛠️ 도구모음", type=btn_tools_type, use_container_width=True):
        set_menu("tools")
        st.rerun()

    # --- [사이드바 하단 푸터 (CSS 및 HTML 주입)] ---
    st.markdown("""
        <style>
        .sidebar-footer {
            position: fixed;
            bottom: 20px;
            left: 0;
            width: 100%;
            padding: 0 1.25rem;
            z-index: 99;
        }
        @media (min-width: 576px) {
            .sidebar-footer {
                width: 300px;
            }
        }
        .sidebar-footer .status-box {
            background-color: var(--secondary-background-color);
            padding: 0.8rem 1rem;
            border-radius: 8px;
            border: 1px solid rgba(128, 128, 128, 0.2);
            margin-bottom: 10px;
            box-sizing: border-box;
        }
        .sidebar-footer p {
            font-size: 0.75rem;
            color: var(--text-color);
            margin: 0;
            line-height: 1.4;
        }
        [data-testid="stSidebarNav"]::after {
            content: "";
            display: block;
            height: 120px;
        }
        </style>
        """, unsafe_allow_html=True)

    st.sidebar.markdown(f"""
        <div class="sidebar-footer">
            <div class="status-box">
                <p>현재 시간: {get_now().strftime('%H:%M')}</p>
                <p>마지막 접속: {st.session_state.last_access_display}</p>
            </div>
            <p style="opacity: 0.6; font-weight: bold;">
                @ Jisong Bang 2026 | Ver 2.4 (260411)
            </p>
        </div>
        """, unsafe_allow_html=True)

    # --- 라우팅 ---
    if st.session_state.menu == "files":
        render_file_manager()
    elif st.session_state.menu == "memos":
        render_memo_manager()
    elif st.session_state.menu == "tools":
        render_tools()

if __name__ == "__main__":
    main()