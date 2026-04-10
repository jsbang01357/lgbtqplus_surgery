import streamlit as st
import os
import datetime
import json
import time
import zipfile
import io
import random
from custom_copy_btn import copy_to_clipboard
from text_cleaner import render_text_cleaner

# --- 설정 ---
MEMO_FILE = "memos.json"
ACCESS_LOG_FILE = "access_log.json"
MENU_LIST_FILE = "menu_list.json"
UPLOAD_DIR = "files"

KST = datetime.timezone(datetime.timedelta(hours=9))

def get_now():
    return datetime.datetime.now(KST)

def init_app():
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)
    if not os.path.exists(MENU_LIST_FILE):
        default_menu = ["김치찌개", "제육볶음", "돈가스", "초밥", "짜장면", "삼겹살", "치킨", "햄버거", "파스타", "샌드위치"]
        with open(MENU_LIST_FILE, "w", encoding="utf-8") as f:
            json.dump(default_menu, f, ensure_ascii=False, indent=4)

def load_memos():
    if not os.path.exists(MEMO_FILE):
        return {}
    with open(MEMO_FILE, "r") as f:
        try:
            memos = json.load(f)
        except json.JSONDecodeError:
            return {}
        for title, data in memos.items():
            if isinstance(data, str):
                memos[title] = {"content": data, "timestamp": get_now().strftime("%Y-%m-%d %H:%M")}
        return memos

def save_memos(memos):
    with open(MEMO_FILE, "w") as f:
        json.dump(memos, f, ensure_ascii=False, indent=4)

def save_uploaded_file(uploaded_file):
    try:
        name, ext = os.path.splitext(uploaded_file.name)
        timestamp = datetime.datetime.now(KST).strftime("%Y%m%d_%H%M%S")
        new_filename = f"{name}_{timestamp}{ext}"
        file_path = os.path.join(UPLOAD_DIR, new_filename)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return True
    except Exception as e:
        return False

def create_zip_of_files():
    if not os.path.exists(UPLOAD_DIR):
        return None
    files = os.listdir(UPLOAD_DIR)
    if not files:
        return None
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_name in files:
            file_path = os.path.join(UPLOAD_DIR, file_name)
            zf.write(file_path, arcname=file_name)
    zip_buffer.seek(0)
    return zip_buffer

def create_zip_of_memos(memos):
    if not memos:
        return None
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for title, data in memos.items():
            file_name = f"{title}.txt"
            zf.writestr(file_name, data["content"].encode('utf-8'))
    zip_buffer.seek(0)
    return zip_buffer

def handle_access_log():
    if "last_access_display" not in st.session_state:
        if os.path.exists(ACCESS_LOG_FILE):
            with open(ACCESS_LOG_FILE, "r") as f:
                try:
                    data = json.load(f)
                    st.session_state.last_access_display = data.get("last_access", "기록 없음")
                except (json.JSONDecodeError, ValueError):
                    st.session_state.last_access_display = "기록 오류"
        else:
            st.session_state.last_access_display = "최초 접속"
        with open(ACCESS_LOG_FILE, "w") as f:
            json.dump({"last_access": get_now().strftime("%Y-%m-%d %H:%M:%S")}, f)

def check_for_updates():
    if "last_memo_mtime" not in st.session_state:
        st.session_state.last_memo_mtime = os.path.getmtime(MEMO_FILE) if os.path.exists(MEMO_FILE) else 0
    if "last_file_mtime" not in st.session_state:
        st.session_state.last_file_mtime = os.path.getmtime(UPLOAD_DIR) if os.path.exists(UPLOAD_DIR) else 0

    cur_memo_mtime = os.path.getmtime(MEMO_FILE) if os.path.exists(MEMO_FILE) else 0
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

def set_menu(menu_name):
    st.session_state.menu = menu_name
    st.query_params["tab"] = menu_name

def main():
    st.set_page_config(page_title="Jisong Cloud", layout="wide")
    
    init_app()
    handle_access_log()
    check_for_updates()
    memos = load_memos()

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
    # 색상을 var(--text-color) 계열로 지정하여 라이트/다크 모드에 전부 호환되게 설정
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
                width: 300px; /* 기본 사이드바 너비 대응 */
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
        /* 기존 기본 공간 확보용 (사이드바 메뉴가 많아질 경우 가려짐 방지) */
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
                <p>🕒 현재 시간: {get_now().strftime('%H:%M')}</p>
                <p>🔒 마지막 접속: {st.session_state.last_access_display}</p>
            </div>
            <p style="text-align: center; opacity: 0.6; font-weight: bold;">
                Ver 2.1 (2026-04-10)<br>
                © Jisong Bang 2026
            </p>
        </div>
        """, unsafe_allow_html=True)
    # ------------------------------------------------

    # --- [메뉴 1] 웹하드 기능 ---
    if st.session_state.menu == "files":
        st.title("📂 웹하드")
        
        if "file_uploader_key" not in st.session_state:
            st.session_state["file_uploader_key"] = 0

        def process_uploaded_files():
            current_key = f"uploader_{st.session_state['file_uploader_key']}"
            files = st.session_state.get(current_key, [])
            if files:
                success_count = 0
                for u_file in files:
                    if save_uploaded_file(u_file):
                        success_count += 1
                if success_count > 0:
                    st.toast(f"✅ {success_count}개 파일 업로드 완료!")
                    st.session_state["file_uploader_key"] += 1

        st.file_uploader(
            "파일 선택 (PPT, PDF 등)", 
            accept_multiple_files=True, 
            key=f"uploader_{st.session_state['file_uploader_key']}",
            on_change=process_uploaded_files
        )

        st.markdown("---")
        st.subheader("💾 저장된 파일")
        
        if os.path.exists(UPLOAD_DIR):
            files = os.listdir(UPLOAD_DIR)
            files.sort(key=lambda f: os.path.getmtime(os.path.join(UPLOAD_DIR, f)), reverse=True)
            
            if files:
                for file_name in files:
                    file_path = os.path.join(UPLOAD_DIR, file_name)
                    timestamp = os.path.getmtime(file_path)
                    file_time = datetime.datetime.fromtimestamp(timestamp, tz=KST).strftime('%Y-%m-%d %H:%M')
                    
                    col_d1, col_d2 = st.columns([4, 1])
                    
                    with col_d1:
                        with open(file_path, "rb") as f:
                            st.download_button(
                                label=f"{file_name} ({file_time})", 
                                data=f,
                                file_name=file_name,
                                mime="application/octet-stream",
                                use_container_width=True
                            )
                    
                    with col_d2:
                        if st.button("🗑️", key=f"del_{file_name}", use_container_width=True):
                            try:
                                os.remove(file_path)
                                st.toast(f"🗑️ '{file_name}' 삭제됨")
                                st.session_state.last_file_mtime = time.time()
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"삭제 오류: {e}")
                
                st.markdown("---")
                st.markdown("📦 일괄 처리")
                zip_data = create_zip_of_files()
                if zip_data:
                    st.download_button(
                        label="📥 모든 파일 ZIP으로 다운로드",
                        data=zip_data,
                        file_name=f"files_{get_now().strftime('%Y%m%d_%H%M')}.zip",
                        mime="application/zip",
                        use_container_width=True
                    )

                st.markdown("---")
                st.markdown("🧹 보안 관리")
                if st.button("🔥 모든 파일 삭제", type="primary", use_container_width=True):
                    try:
                        files_to_delete = os.listdir(UPLOAD_DIR)
                        for f in files_to_delete:
                            os.remove(os.path.join(UPLOAD_DIR, f))
                        st.toast("✅ 모든 파일이 삭제되었습니다.")
                        st.session_state.last_file_mtime = time.time()
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"삭제 중 오류 발생: {e}")
            else:
                st.write("📂 현재 저장된 파일이 없습니다.")
        else:
            st.write("📂 저장소 폴더가 생성되지 않았습니다.")

    # --- [메뉴 2] 메모장 기능 ---
    elif st.session_state.menu == "memos":
        st.title("📝 메모장")
        
        # 새 메모 폼 초기화를 위한 Key
        if "new_memo_key" not in st.session_state:
            st.session_state.new_memo_key = 0

        with st.container():
            st.subheader("새 메모 작성")
            title_key = f"new_title_{st.session_state.new_memo_key}"
            content_key = f"new_content_{st.session_state.new_memo_key}"

            col_new1, col_new2 = st.columns([3, 1], vertical_alignment="bottom")
            with col_new1:
                new_title = st.text_input("제목", placeholder="제목을 입력하세요", key=title_key)
            with col_new2:
                save_btn = st.button("저장하기", type="primary", use_container_width=True)

            new_content = st.text_area("내용", height=150, placeholder="여기에 내용을 입력하세요", key=content_key)
            
            if save_btn:
                saved_title = new_title.strip()
                if not saved_title:
                    birds = ["까치", "참새", "비둘기", "까마귀", "제비", "기러기", "독수리", "부엉이", "딱따구리", "황새"]
                    saved_title = f"{random.choice(birds)}_{random.randint(100, 999)}"
                
                memos[saved_title] = {"content": new_content, "timestamp": get_now().strftime("%Y-%m-%d %H:%M")}
                save_memos(memos)
                st.session_state.last_memo_mtime = time.time()
                st.toast(f"✅ '{saved_title}' 이름으로 메모 저장 완료!")
                
                st.session_state.new_memo_key += 1
                time.sleep(0.5)
                st.rerun()

        st.markdown("---")
        st.subheader("💾 저장된 메모")

        if not memos:
            st.info("저장된 메모가 없습니다.")
        
        for idx, (t, d) in enumerate(reversed(list(memos.items()))):
            # 1행: 제목 드롭다운 (가로 100%)
            with st.expander(f"📖 {t} ({d['timestamp']})"):
                # 드롭다운 안에서 제목 수정 및 내용 수정
                edit_title = st.text_input("제목 수정", value=t, key=f"edit_title_{idx}_{t}")
                
                line_count = d['content'].count('\n') + 1
                dynamic_height = min(40 + (line_count * 25), 400)

                edit_content = st.text_area(
                    label="내용 수정",
                    value=d['content'],
                    height=dynamic_height,
                    key=f"edit_content_{idx}_{t}"
                )
                if st.button("📝 수정 내용 저장", key=f"save_{idx}_{t}", use_container_width=True):
                    new_t = edit_title.strip()
                    if not new_t:
                        new_t = t
                        
                    if new_t != t:
                        memos[new_t] = {"content": edit_content, "timestamp": get_now().strftime("%Y-%m-%d %H:%M")}
                        del memos[t]
                    else:
                        memos[t] = {"content": edit_content, "timestamp": get_now().strftime("%Y-%m-%d %H:%M")}
                    
                    save_memos(memos)
                    st.session_state.last_memo_mtime = time.time()
                    st.toast("✅ 수정되었습니다.")
                    time.sleep(0.5)
                    st.rerun()

            # 2행: 버튼들 (제목 바로 아래 줄)
            col_copy, col_dl, col_del = st.columns([1, 1, 1])
            with col_copy:
                copy_to_clipboard(text=d['content'], before_copy_label="📋 복사", after_copy_label="✅ 완료", key=f"out_copy_{t}")
            with col_dl:
                st.download_button(
                    label="📥 다운",
                    data=d['content'],
                    file_name=f"{t}.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key=f"out_dl_{t}"
                )
            with col_del:
                if st.button("🗑️ 삭제", key=f"out_del_{t}", type="secondary", use_container_width=True):
                    del memos[t]
                    save_memos(memos)
                    st.session_state.last_memo_mtime = time.time()
                    st.toast("🗑️ 삭제되었습니다.")
                    time.sleep(0.5)
                    st.rerun()
            
            st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True) # 메모 간 간격

        if memos:
            st.markdown("---")
            st.markdown("📦 일괄 처리")
            zip_memo_data = create_zip_of_memos(memos)
            if zip_memo_data:
                st.download_button(
                    label="📥 모든 메모 ZIP으로 다운로드",
                    data=zip_memo_data,
                    file_name=f"memos_{get_now().strftime('%Y%m%d_%H%M')}.zip",
                    mime="application/zip",
                    use_container_width=True
                )

            st.markdown("---")
            st.markdown("🧹 보안 관리")
            if st.button("🔥 모든 메모 삭제", type="primary", use_container_width=True):
                memos.clear()
                save_memos(memos)
                st.session_state.last_memo_mtime = time.time()
                st.toast("✅ 모든 메모가 삭제되었습니다.")
                time.sleep(0.5)
                st.rerun()

    # --- [메뉴 3] 도구모음 ---
    elif st.session_state.menu == "tools":
        st.title("🛠️ 도구모음")

        selected_tool = st.selectbox(
            "사용할 도구를 선택하세요", 
            ["🧹 텍스트 클리너", "📝 글자수 카운터", "🍴 오늘 뭐 먹지?"]
        )
        st.markdown("---")

        if selected_tool == "🧹 텍스트 클리너":
            render_text_cleaner()

        elif selected_tool == "📝 글자수 카운터":
            st.subheader("📝 글자수 카운터")
            st.info("텍스트를 입력하면 단어수, 글자수, 예상 A4 페이지 수를 계산합니다.")
            
            input_text = st.text_area("분석할 텍스트를 입력하세요", height=300, placeholder="여기에 내용을 붙여넣으세요...")
            
            if st.button("분석하기", type="primary", use_container_width=True):
                if input_text:
                    char_count_with_spaces = len(input_text)
                    char_count_without_spaces = len(input_text.replace(" ", "").replace("\n", "").replace("\r", ""))
                    word_count = len(input_text.split())
                    a4_pages = char_count_with_spaces / 1500
                    
                    st.markdown("---")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("단어 수", f"{word_count}개")
                    with col2:
                        st.metric("글자 수 (공백 포함)", f"{char_count_with_spaces}자")
                    with col3:
                        st.metric("글자 수 (공백 제외)", f"{char_count_without_spaces}자")
                    with col4:
                        st.metric("예상 A4 분량", f"{a4_pages:.2f}쪽")
                    st.caption("※ A4 분량은 공백 포함 1,500자를 1쪽으로 계산한 결과입니다.")
                else:
                    st.warning("텍스트를 입력해주세요.")

        elif selected_tool == "🍴 오늘 뭐 먹지?":
            st.subheader("🍴 오늘 뭐 먹지?")
            st.info("결정하기 힘들 때, 랜덤으로 메뉴를 추천해 드립니다!")
            
            if st.button("🎲 메뉴 추천받기", use_container_width=True):
                if os.path.exists(MENU_LIST_FILE):
                    try:
                        with open(MENU_LIST_FILE, "r", encoding="utf-8") as f:
                            menu_list = json.load(f)
                        selected_menu = random.choice(menu_list)
                        st.balloons()
                        st.success(f"오늘의 추천 메뉴는 바로... **{selected_menu}** 입니다! 맛있게 드세요! 😋")
                    except Exception as e:
                        st.error(f"메뉴를 불러오는 중 오류가 발생했습니다: {e}")
                else:
                    st.error("menu_list.json 파일이 없습니다.")

if __name__ == "__main__":
    main()