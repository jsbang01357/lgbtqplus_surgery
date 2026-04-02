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

# 한국 시간(KST) 타임존 정의 (UTC+9)
KST = datetime.timezone(datetime.timedelta(hours=9))

def get_now():
    """현재 시간을 KST 기준으로 반환합니다. 호출 시점의 실시간 시간을 보장합니다."""
    return datetime.datetime.now(KST)

# --- 초기화 및 데이터 관리 ---
def init_app():
    """앱 실행 시 필요한 디렉토리 및 기본 파일 생성"""
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)
    
    # menu_list.json 파일이 없으면 기본 메뉴로 생성
    if not os.path.exists(MENU_LIST_FILE):
        default_menu = ["김치찌개", "제육볶음", "돈가스", "초밥", "짜장면", "삼겹살", "치킨", "햄버거", "파스타", "샌드위치"]
        with open(MENU_LIST_FILE, "w", encoding="utf-8") as f:
            json.dump(default_menu, f, ensure_ascii=False, indent=4)

def load_memos():
    if not os.path.exists(MEMO_FILE):
        return {}
    with open(MEMO_FILE, "r") as f:
        memos = json.load(f)
        for title, data in memos.items():
            if isinstance(data, str):
                memos[title] = {"content": data, "timestamp": get_now().strftime("%Y-%m-%d %H:%M")}
        return memos

def save_memos(memos):
    with open(MEMO_FILE, "w") as f:
        json.dump(memos, f, ensure_ascii=False, indent=4)

def save_uploaded_file(uploaded_file):
    """업로드된 파일을 서버(files 폴더)에 저장"""
    try:
        # 파일명과 확장자 분리 후 타임스탬프 추가
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
    """UPLOAD_DIR 내의 모든 파일을 압축하여 bytes로 반환"""
    if not os.path.exists(UPLOAD_DIR):
        return None
    
    files = os.listdir(UPLOAD_DIR)
    if not files:
        return None
        
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_name in files:
            file_path = os.path.join(UPLOAD_DIR, file_name)
            # 압축 내부 파일 날짜도 KST로 맞추려면 별도 처리가 필요하지만, 
            # 여기서는 파일 자체만 담습니다.
            zf.write(file_path, arcname=file_name)
    
    zip_buffer.seek(0)
    return zip_buffer

# --- 접속 기록 관리 함수 ---
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

# --- 메인 함수 ---
def main():
    st.set_page_config(page_title="Jisong Cloud", layout="wide")
    
    init_app()
    handle_access_log()
    memos = load_memos()

    # --- [사이드바 메뉴] ---
    st.sidebar.title("Jisong Cloud")
    
    if "menu" not in st.session_state:
        st.session_state.menu = "files"

    # 버튼 상태 강조 로직 업데이트
    btn_files_type = "primary" if st.session_state.menu == "files" else "secondary"
    btn_memos_type = "primary" if st.session_state.menu == "memos" else "secondary"
    btn_cleaner_type = "primary" if st.session_state.menu == "cleaner" else "secondary"
    btn_tools_type = "primary" if st.session_state.menu == "tools" else "secondary"

    if st.sidebar.button("📂 웹하드", type=btn_files_type, use_container_width=True):
        st.session_state.menu = "files"
        st.rerun()
        
    if st.sidebar.button("📝 메모장", type=btn_memos_type, use_container_width=True):
        st.session_state.menu = "memos"
        st.rerun()

    if st.sidebar.button("🧹 텍스트 클리너", type=btn_cleaner_type, use_container_width=True):
        st.session_state.menu = "cleaner"
        st.rerun()
    
    if st.sidebar.button("🛠️ 도구모음", type=btn_tools_type, use_container_width=True):
        st.session_state.menu = "tools"
        st.rerun()

    st.sidebar.markdown("---")
    # KST 기준 시간 표시
    st.sidebar.caption(f"🕒 현재 시간: {get_now().strftime('%H:%M')}")
    st.sidebar.caption(f"🔒 마지막 접속: {st.session_state.last_access_display}")
    st.sidebar.markdown("---")
    st.sidebar.caption("Ver 2.0 (2026-04-02)") 
    st.sidebar.caption("@Jisong Bang 2026") 

    # --- [메뉴 1] 파일 전송 기능 ---
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
                    # 업로더 초기화를 위해 key 변경
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
            
            # 정렬 로직 (최신순)
            files.sort(key=lambda f: os.path.getmtime(os.path.join(UPLOAD_DIR, f)), reverse=True)
            
            if files:
                for file_name in files:
                    file_path = os.path.join(UPLOAD_DIR, file_name)
                    
                    # [수정 4] 파일의 수정 시간(timestamp)을 가져와 KST로 변환
                    timestamp = os.path.getmtime(file_path)
                    # fromtimestamp에 두 번째 인자로 tz(타임존)을 주면 해당 시간대로 변환됩니다.
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
                        time.sleep(1)
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
        
        with st.container():
            st.subheader("새 메모 작성")
            col_new1, col_new2 = st.columns([3, 1], vertical_alignment="bottom")
            with col_new1:
                new_title = st.text_input("제목", placeholder="제목을 입력하세요")
            with col_new2:
                save_btn = st.button("저장하기", type="primary", use_container_width=True)

            new_content = st.text_area("내용", height=150, placeholder="여기에 내용을 입력하세요")
            
            if save_btn:
                # 제목이 비어있으면 랜덤 새 이름(번호 포함) 할당
                if not new_title.strip():
                    birds = [
                        "까치", "참새", "비둘기", "까마귀", "제비", 
                        "기러기", "독수리", "부엉이", "딱따구리", "황새",
                        "두루미", "원앙", "갈매기", "꾀꼬리", "종달새",
                        "백조", "올빼미", "황매", "파랑새", "황조롱이"
                    ]
                    new_title = f"{random.choice(birds)}_{random.randint(100, 999)}"
                
                memos[new_title] = {"content": new_content, "timestamp": get_now().strftime("%Y-%m-%d %H:%M")}
                save_memos(memos)
                st.toast(f"✅ '{new_title}' 이름으로 메모 저장 완료!")
                time.sleep(0.5)
                st.rerun()

        st.markdown("---")
        st.subheader("💾 저장된 메모")

        if not memos:
            st.info("저장된 메모가 없습니다.")
        
        for t, d in reversed(list(memos.items())):
            with st.expander(f"{t} ({d['timestamp']})"):
                line_count = d['content'].count('\n') + 1
                dynamic_height = 40 + (line_count * 25)

                edited_content = st.text_area(
                    label="내용 수정",
                    value=d['content'],
                    height=dynamic_height,
                    key=f"content_{t}"
                )

                col_m1, col_m2, col_m3, col_m4 = st.columns([3, 1, 1, 1])
                with col_m1:
                    if st.button("수정 내용 저장", key=f"save_{t}", use_container_width=True):
                        memos[t] = {"content": edited_content, "timestamp": get_now().strftime("%Y-%m-%d %H:%M")}
                        save_memos(memos)
                        st.toast("✅ 수정되었습니다.")
                        time.sleep(0.5)
                        st.rerun()
                with col_m2:
                    copy_to_clipboard(text=edited_content, before_copy_label="📋 복사", after_copy_label="✅ 완료", key=f"copy_{t}")
                with col_m3:
                    st.download_button(
                        label="📥 다운로드",
                        data=edited_content,
                        file_name=f"{t}.txt",
                        mime="text/plain",
                        use_container_width=True,
                        key=f"dl_memo_{t}"
                    )
                with col_m4:
                    if st.button("삭제", key=f"del_memo_{t}", type="secondary", use_container_width=True):
                        del memos[t]
                        save_memos(memos)
                        st.toast("🗑️ 삭제되었습니다.")
                        time.sleep(0.5)
                        st.rerun()

    # --- [메뉴 3] 텍스트 클리너 ---
    elif st.session_state.menu == "cleaner":
        render_text_cleaner()

    # --- [메뉴 4] 도구모음 기능 ---
    elif st.session_state.menu == "tools":
        st.title("🛠️ 도구모음")

        # 도구 선택 드롭다운
        selected_tool = st.selectbox("사용할 도구를 선택하세요", ["📝 글자수 카운터", "🍴 오늘 뭐 먹지?"])
        st.markdown("---")

        if selected_tool == "📝 글자수 카운터":
            st.subheader("📝 글자수 카운터")
            st.info("텍스트를 입력하면 단어수, 글자수, 예상 A4 페이지 수를 계산합니다.")
            
            input_text = st.text_area("분석할 텍스트를 입력하세요", height=300, placeholder="여기에 내용을 붙여넣으세요...")
            
            if st.button("분석하기", type="primary", use_container_width=True):
                if input_text:
                    # 계산 로직
                    char_count_with_spaces = len(input_text)
                    char_count_without_spaces = len(input_text.replace(" ", "").replace("\n", "").replace("\r", ""))
                    word_count = len(input_text.split())
                    # A4 기준: 공백 포함 1,500자당 1페이지로 계산 (일반적인 기준)
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