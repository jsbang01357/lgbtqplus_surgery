import streamlit as st
import os
import json
import time
import zipfile
import io
import random
from utils import get_now, safe_filename
from custom_copy_btn import copy_to_clipboard

MEMO_DIR = "memos"
OLD_JSON_FILE = "memos.json"

def init_memos():
    """메모 파일 저장소를 초기화하고, 기존 JSON을 txt로 마이그레이션 합니다."""
    if not os.path.exists(MEMO_DIR):
        os.makedirs(MEMO_DIR)
    
    # 마이그레이션
    if os.path.exists(OLD_JSON_FILE):
        try:
            with open(OLD_JSON_FILE, "r") as f:
                old_memos = json.load(f)
            
            # txt로 전부 저장
            for title, data in old_memos.items():
                content = data.get("content", data if isinstance(data, str) else "")
                timestamp = data.get("timestamp", get_now().strftime("%Y-%m-%d %H:%M:%S"))
                
                safe_name = safe_filename(title)
                if not safe_name: safe_name = "memo"
                file_path = os.path.join(MEMO_DIR, f"{safe_name}.txt")
                
                # 방어: 파일명이 겹치면 뒤에 랜덤 숫자
                if os.path.exists(file_path):
                    safe_name = f"{safe_name}_{random.randint(1000,9999)}"
                    file_path = os.path.join(MEMO_DIR, f"{safe_name}.txt")
                
                with open(file_path, "w", encoding="utf-8") as out:
                    out.write(f"TITLE: {title}\n")
                    out.write(f"CREATED_AT: {timestamp}\n")
                    out.write(f"UPDATED_AT: {timestamp}\n\n")
                    out.write(content)
                    
            # 마이그레이션 끝난 백업 처리
            os.rename(OLD_JSON_FILE, f"{OLD_JSON_FILE}.bak")
        except Exception:
            pass

def load_memos_from_txt():
    """모든 txt 메모를 읽어 Dict 배열로 반환합니다. 파싱 후 정렬됨."""
    init_memos()
    memos = {}
    
    for file_name in os.listdir(MEMO_DIR):
        if not file_name.endswith(".txt"):
            continue
            
        file_path = os.path.join(MEMO_DIR, file_name)
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        title = file_name.replace('.txt', '') # fallback
        created_at = ""
        updated_at = ""
        content_lines = []
        
        in_header = True
        for line in lines:
            if in_header:
                if line.startswith("TITLE: "):
                    title = line[7:].strip()
                elif line.startswith("CREATED_AT: "):
                    created_at = line[12:].strip()
                elif line.startswith("UPDATED_AT: "):
                    updated_at = line[12:].strip()
                elif line.strip() == "":
                    in_header = False
                else:
                    # 헤더 양식이 아니면 바로 본문 취급
                    in_header = False
                    content_lines.append(line)
            else:
                content_lines.append(line)
                
        content = "".join(content_lines).strip()
        memos[file_name] = {
            "title": title,
            "content": content,
            "created_at": created_at,
            "updated_at": updated_at,
            "file_name": file_name
        }
    
    # 시간 역순 정렬 (updated_at 우선)
    sorted_memos = sorted(memos.values(), key=lambda x: x["updated_at"] or x["created_at"], reverse=True)
    return sorted_memos

def save_memo_txt(title, content, original_file_name=None):
    init_memos()
    timestamp = get_now().strftime("%Y-%m-%d %H:%M:%S")
    
    if original_file_name:
        file_path = os.path.join(MEMO_DIR, original_file_name)
    else:
        # 새 파일
        safe_name = safe_filename(title)
        if not safe_name:
            safe_name = f"memo_{random.randint(1000,9999)}"
        file_name = f"{safe_name}.txt"
        file_path = os.path.join(MEMO_DIR, file_name)
        
        count = 1
        while os.path.exists(file_path):
            file_name = f"{safe_name}_{count}.txt"
            file_path = os.path.join(MEMO_DIR, file_name)
            count += 1
            
        original_file_name = file_name
        
    created_at = timestamp
    # 기존 파일이 있다면 created_at을 유지하기 위해 파싱
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("CREATED_AT: "):
                    created_at = line[12:].strip()
                    break

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"TITLE: {title}\n")
        f.write(f"CREATED_AT: {created_at}\n")
        f.write(f"UPDATED_AT: {timestamp}\n\n")
        f.write(content)

def delete_memo_txt(file_name):
    if not file_name: return
    file_path = os.path.join(MEMO_DIR, file_name)
    if os.path.exists(file_path):
        os.remove(file_path)

def clear_all_memos():
    init_memos()
    for file_name in os.listdir(MEMO_DIR):
        file_path = os.path.join(MEMO_DIR, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)

def create_zip_of_memos(memo_list):
    if not memo_list:
        return None
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for m in memo_list:
            safe_name = safe_filename(m["title"]) or "memo"
            file_name = f"{safe_name}.txt"
            zf.writestr(file_name, m["content"].encode('utf-8'))
    zip_buffer.seek(0)
    return zip_buffer

def render_memo_manager():
    """메모장 UI 메인 렌더링"""
    st.title("📝 메모장")
    memos_list = load_memos_from_txt()
    
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
            
            save_memo_txt(saved_title, new_content)
            st.session_state.last_memo_mtime = time.time()
            st.toast(f"✅ '{saved_title}' 이름으로 메모 저장 완료!")
            
            st.session_state.new_memo_key += 1
            time.sleep(0.5)
            st.rerun()

    st.markdown("---")
    st.subheader("💾 저장된 메모")

    if not memos_list:
        st.info("저장된 메모가 없습니다.")
    
    for idx, m in enumerate(memos_list):
        t = m["title"]
        cont = m["content"]
        ts = m["updated_at"] or m["created_at"]
        fname = m["file_name"]
        
        with st.expander(f"📖 {t} ({ts})"):
            edit_title = st.text_input("제목 수정", value=t, key=f"edit_title_{idx}_{fname}")
            
            line_count = cont.count('\n') + 1
            dynamic_height = min(40 + (line_count * 25), 400)

            edit_content = st.text_area(
                label="내용 수정",
                value=cont,
                height=dynamic_height,
                key=f"edit_content_{idx}_{fname}"
            )
            if st.button("📝 수정 내용 저장", key=f"save_{idx}_{fname}", use_container_width=True):
                new_t = edit_title.strip() or t
                save_memo_txt(new_t, edit_content, original_file_name=fname)
                st.session_state.last_memo_mtime = time.time()
                st.toast("✅ 수정되었습니다.")
                time.sleep(0.5)
                st.rerun()

        col_copy, col_dl, col_del = st.columns([1, 1, 1])
        with col_copy:
            copy_to_clipboard(text=cont, before_copy_label="📋 복사", after_copy_label="✅ 완료", key=f"out_copy_{fname}")
        with col_dl:
            st.download_button(
                label="📥 다운",
                data=cont,
                file_name=f"{safe_filename(t) or 'memo'}.txt",
                mime="text/plain",
                use_container_width=True,
                key=f"out_dl_{fname}"
            )
        with col_del:
            if st.button("🗑️ 삭제", key=f"out_del_{fname}", type="secondary", use_container_width=True):
                delete_memo_txt(fname)
                st.session_state.last_memo_mtime = time.time()
                st.toast("🗑️ 삭제되었습니다.")
                time.sleep(0.5)
                st.rerun()
        
        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

    if memos_list:
        st.markdown("---")
        st.markdown("📦 일괄 처리")
        zip_memo_data = create_zip_of_memos(memos_list)
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
            clear_all_memos()
            st.session_state.last_memo_mtime = time.time()
            st.toast("✅ 모든 메모가 삭제되었습니다.")
            time.sleep(0.5)
            st.rerun()
