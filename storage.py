import streamlit as st
import os
import datetime
import zipfile
import io
import time
from utils import get_now, KST

UPLOAD_DIR = "files"

def init_storage():
    """파일 업로드 디렉토리를 초기화합니다."""
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

def save_uploaded_file(uploaded_file):
    init_storage()
    try:
        name, ext = os.path.splitext(uploaded_file.name)
        timestamp = get_now().strftime("%Y%m%d_%H%M%S")
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

def render_file_manager():
    """웹하드 UI 메인 컴포넌트 렌더링"""
    st.title("📂 웹하드")
    init_storage()
    
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
                            use_container_width=True,
                            key=f"dl_{file_name}"
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
