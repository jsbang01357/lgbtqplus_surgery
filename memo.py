import streamlit as st
import os
import json
import zipfile
import io
import random
from pathlib import PurePosixPath

from core_utils import get_now, safe_filename, slugify
from custom_copy_btn import copy_to_clipboard
from gcs_helper import get_bucket

MEMO_PREFIX = "memos"
OLD_JSON_FILE = "memos.json"



def init_memos():
    if OLD_JSON_FILE:
        try:
            import os
            if os.path.exists(OLD_JSON_FILE):
                with open(OLD_JSON_FILE, "r", encoding="utf-8") as f:
                    old_memos = json.load(f)

                for title, data in old_memos.items():
                    content = data.get("content", data if isinstance(data, str) else "")
                    save_memo_txt(title=title, content=content)

                os.rename(OLD_JSON_FILE, f"{OLD_JSON_FILE}.bak")
        except Exception:
            pass


def parse_memo_text(raw_text: str, fallback_name: str):
    lines = raw_text.splitlines()
    title = fallback_name.replace(".txt", "")
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
                in_header = False
                content_lines.append(line)
        else:
            content_lines.append(line)

    content = "\n".join(content_lines).strip()
    return {
        "title": title,
        "content": content,
        "created_at": created_at,
        "updated_at": updated_at,
        "file_name": fallback_name,
    }


def _build_memo_payload(title: str, content: str, created_at: str, updated_at: str) -> str:
    return (
        f"TITLE: {title}\n"
        f"CREATED_AT: {created_at}\n"
        f"UPDATED_AT: {updated_at}\n\n"
        f"{content}"
    )


@st.cache_data(ttl=30)
def load_memo_list_cached():
    init_memos()
    bucket = get_bucket()
    blobs = bucket.list_blobs(prefix=f"{MEMO_PREFIX}/")
    memos = []

    for blob in blobs:
        if blob.name.endswith("/") or not blob.name.endswith(".txt"):
            continue

        file_name = PurePosixPath(blob.name).name
        metadata = blob.metadata or {}

        title = metadata.get("title", file_name.replace(".txt", ""))
        created_at = metadata.get("created_at", "")
        updated_at = metadata.get("updated_at", "")

        memos.append({
            "title": title,
            "created_at": created_at,
            "updated_at": updated_at,
            "file_name": file_name,
        })

    memos.sort(key=lambda x: x["updated_at"] or x["created_at"], reverse=True)
    return memos


@st.cache_data(ttl=60)
def load_single_memo_content(file_name: str):
    bucket = get_bucket()
    blob = bucket.blob(f"{MEMO_PREFIX}/{file_name}")
    raw_text = blob.download_as_text(encoding="utf-8")
    parsed = parse_memo_text(raw_text, fallback_name=file_name)
    return parsed


def save_memo_txt(title, content, original_file_name=None):
    init_memos()
    bucket = get_bucket()
    timestamp = get_now().strftime("%Y-%m-%d %H:%M:%S")

    if original_file_name:
        blob_name = f"{MEMO_PREFIX}/{original_file_name}"
        blob = bucket.blob(blob_name)

        created_at = timestamp
        if blob.exists():
            old = load_single_memo_content(original_file_name)
            created_at = old["created_at"] or timestamp

        payload = _build_memo_payload(title, content, created_at, timestamp)
        blob.metadata = {
            "title": title,
            "created_at": created_at,
            "updated_at": timestamp,
        }
        blob.upload_from_string(payload.encode("utf-8"), content_type="text/plain; charset=utf-8")

        load_memo_list_cached.clear()
        load_single_memo_content.clear()
        create_zip_of_memos.clear()
        if "zip_data_memos" in st.session_state:
            st.session_state.zip_data_memos = None
        return

    safe_name = slugify(title)
    if not safe_name:
        safe_name = f"memo-{random.randint(1000,9999)}"

    ts = get_now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{ts}_{safe_name}.txt"
    blob_name = f"{MEMO_PREFIX}/{file_name}"
    blob = bucket.blob(blob_name)

    payload = _build_memo_payload(title, content, timestamp, timestamp)
    blob.metadata = {
        "title": title,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    blob.upload_from_string(payload.encode("utf-8"), content_type="text/plain; charset=utf-8")

    load_memo_list_cached.clear()
    load_single_memo_content.clear()
    create_zip_of_memos.clear()
    if "zip_data_memos" in st.session_state:
        st.session_state.zip_data_memos = None


def delete_memo_txt(file_name):
    if not file_name:
        return
    bucket = get_bucket()
    blob = bucket.blob(f"{MEMO_PREFIX}/{file_name}")
    if blob.exists():
        blob.delete()

    load_memo_list_cached.clear()
    load_single_memo_content.clear()
    create_zip_of_memos.clear()
    if "zip_data_memos" in st.session_state:
        st.session_state.zip_data_memos = None


def clear_all_memos():
    bucket = get_bucket()
    blobs = list(bucket.list_blobs(prefix=f"{MEMO_PREFIX}/"))
    for blob in blobs:
        blob.delete()

    load_memo_list_cached.clear()
    load_single_memo_content.clear()
    create_zip_of_memos.clear()
    if "zip_data_memos" in st.session_state:
        st.session_state.zip_data_memos = None


@st.cache_data(ttl=60)
def create_zip_of_memos(memo_list):
    if not memo_list:
        return None

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for m in memo_list:
            memo_full = load_single_memo_content(m["file_name"])
            safe_name = safe_filename(memo_full["title"]) or "memo"
            file_name = f"{safe_name}.txt"
            zf.writestr(file_name, memo_full["content"].encode("utf-8"))

    zip_buffer.seek(0)
    return zip_buffer


def render_memo_manager():
    st.title("📝 메모장")
    memos_list = load_memo_list_cached()

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
            st.toast(f"✅ '{saved_title}' 이름으로 메모 저장 완료!")
            st.session_state.new_memo_key += 1
            st.rerun()

    st.markdown("---")
    st.subheader("💾 저장된 메모")

    if not memos_list:
        st.info("저장된 메모가 없습니다.")

    for idx, m in enumerate(memos_list):
        t = m["title"]
        ts = m["updated_at"] or m["created_at"]
        fname = m["file_name"]

        with st.expander(f"📖 {t} ({ts})"):
            memo_full = load_single_memo_content(fname)
            cont = memo_full["content"]

            edit_title = st.text_input("제목 수정", value=memo_full["title"], key=f"edit_title_{idx}_{fname}")

            line_count = cont.count("\n") + 1
            dynamic_height = min(40 + (line_count * 25), 400)

            edit_content = st.text_area(
                label="내용 수정",
                value=cont,
                height=dynamic_height,
                key=f"edit_content_{idx}_{fname}",
            )

            if st.button("📝 수정 내용 저장", key=f"save_{idx}_{fname}", use_container_width=True):
                new_t = edit_title.strip() or memo_full["title"]
                save_memo_txt(new_t, edit_content, original_file_name=fname)
                st.toast("✅ 수정되었습니다.")
                st.rerun()

            col_copy, col_dl, col_del = st.columns([1, 1, 1])

            with col_copy:
                copy_to_clipboard(
                    text=cont,
                    before_copy_label="📋 복사",
                    after_copy_label="✅ 완료",
                    key=f"out_copy_{fname}",
                )

            with col_dl:
                st.download_button(
                    label="📥 다운",
                    data=cont,
                    file_name=f"{safe_filename(memo_full['title']) or 'memo'}.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key=f"out_dl_{fname}",
                )

            with col_del:
                if st.button("🗑️ 삭제", key=f"out_del_{fname}", type="secondary", use_container_width=True):
                    delete_memo_txt(fname)
                    st.toast("🗑️ 삭제되었습니다.")
                    st.rerun()

        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

    if memos_list:
        st.markdown("---")
        st.markdown("📦 일괄 처리")
        
        if "zip_data_memos" not in st.session_state:
            st.session_state.zip_data_memos = None

        col_m_zip1, col_m_zip2 = st.columns([1, 1])
        with col_m_zip1:
            if st.button("📦 모든 메모 ZIP 준비하기", use_container_width=True):
                with st.spinner("압축 중..."):
                    st.session_state.zip_data_memos = create_zip_of_memos(memos_list)
                    st.toast("✅ ZIP 준비 완료!")

        with col_m_zip2:
            if st.session_state.zip_data_memos:
                st.download_button(
                    label="📥 준비된 ZIP 다운로드",
                    data=st.session_state.zip_data_memos,
                    file_name=f"memos_{get_now().strftime('%Y%m%d_%H%M')}.zip",
                    mime="application/zip",
                    use_container_width=True,
                )
            else:
                st.button("📥 ZIP 다운로드 (준비 필요)", disabled=True, use_container_width=True)

        st.markdown("---")
        st.markdown("🧹 보안 관리")
        if st.button("🔥 모든 메모 삭제", type="primary", use_container_width=True):
            try:
                clear_all_memos()
                st.toast("✅ 모든 메모가 삭제되었습니다.")
                st.rerun()
            except Exception as e:
                st.error(f"삭제 중 오류 발생: {e}")