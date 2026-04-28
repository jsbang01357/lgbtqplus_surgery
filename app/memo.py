import streamlit as st
import json
import zipfile
import io
import time
import random
import streamlit.components.v1 as components
from pathlib import PurePosixPath

from app.core_utils import get_now, safe_filename, slugify
from components.custom_copy_btn import copy_to_clipboard
from app.gcs_helper import get_bucket

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


def _build_memo_payload(
    title: str, content: str, created_at: str, updated_at: str
) -> str:
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

        memos.append(
            {
                "title": title,
                "created_at": created_at,
                "updated_at": updated_at,
                "file_name": file_name,
            }
        )

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
        blob.upload_from_string(
            payload.encode("utf-8"), content_type="text/plain; charset=utf-8"
        )

        load_memo_list_cached.clear()
        load_single_memo_content.clear()
        create_zip_of_memos.clear()
        if "zip_data_memos" in st.session_state:
            st.session_state.zip_data_memos = None
        return

    safe_name = slugify(title)
    if not safe_name:
        safe_name = f"memo-{random.randint(1000, 9999)}"

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
    blob.upload_from_string(
        payload.encode("utf-8"), content_type="text/plain; charset=utf-8"
    )

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


def _memo_preview(content: str, limit: int = 120) -> str:
    preview = " ".join(content.split())
    if len(preview) <= limit:
        return preview or "내용 미리보기가 없습니다."
    return f"{preview[:limit].rstrip()}..."


def render_memo_manager():
    memos_list = load_memo_list_cached()

    if "new_memo_key" not in st.session_state:
        st.session_state.new_memo_key = 0
    if "confirm_clear_memos" not in st.session_state:
        st.session_state.confirm_clear_memos = False

    with st.container():
        st.markdown(
            """
            <div class="section-block">
                <p class="section-block__eyebrow">Write</p>
                <h2 class="section-block__title">새 메모 작성</h2>
                <p class="section-block__body">
                    제목과 내용을 입력하면 시간 정보와 함께 텍스트 메모로 저장됩니다.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        title_key = f"new_title_{st.session_state.new_memo_key}"
        content_key = f"new_content_{st.session_state.new_memo_key}"

        col_new1, col_new2 = st.columns([3, 1], vertical_alignment="bottom")
        with col_new1:
            new_title = st.text_input(
                "제목", placeholder="제목을 입력하세요", key=title_key
            )
        with col_new2:
            save_btn = st.button("저장하기", type="primary", use_container_width=True)

        new_content = st.text_area(
            "내용", height=150, placeholder="여기에 내용을 입력하세요", key=content_key
        )

        if save_btn:
            saved_title = new_title.strip()
            if not saved_title:
                birds = [
                    "까치",
                    "참새",
                    "비둘기",
                    "까마귀",
                    "제비",
                    "기러기",
                    "독수리",
                    "부엉이",
                    "딱따구리",
                    "황새",
                ]
                saved_title = f"{random.choice(birds)}_{random.randint(100, 999)}"

            save_memo_txt(saved_title, new_content)
            st.toast(f"✅ '{saved_title}' 이름으로 메모 저장 완료!")
            st.session_state.new_memo_key += 1
            st.rerun()

        components.html(
            f"""
            <script>
            // unique execution: {time.time()}
            function focusMemoTitleOnce() {{
                var doc = window.parent.document;
                var active = doc.activeElement;
                if (active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA')) {{
                    return;
                }}

                var inputs = doc.querySelectorAll('input');
                for (var i=0; i<inputs.length; i++) {{
                    if (inputs[i].getAttribute('aria-label') === '제목' || inputs[i].placeholder === '제목을 입력하세요') {{
                        if (!inputs[i].value) {{
                            inputs[i].focus();
                        }}
                        return;
                    }}
                }}
            }}

            setTimeout(focusMemoTitleOnce, 120);
            </script>
            """,
            height=0,
            width=0,
        )

    st.markdown(
        """
        <div class="section-block section-block--spacious">
            <p class="section-block__eyebrow">Library</p>
            <h2 class="section-block__title">저장된 메모</h2>
            <p class="section-block__body">
                최근 수정된 메모부터 펼쳐보고 바로 수정, 복사, 다운로드할 수 있습니다.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not memos_list:
        st.info("저장된 메모가 없습니다.")

    memo_query = st.text_input(
        "메모 검색",
        placeholder="제목이나 내용으로 찾기",
        key="memo_search_query",
    ).strip().lower()

    filtered_memos = []
    for memo in memos_list:
        if not memo_query:
            filtered_memos.append(memo)
            continue

        title_match = memo_query in memo["title"].lower()
        content_match = False
        if not title_match:
            memo_full = load_single_memo_content(memo["file_name"])
            content_match = memo_query in memo_full["content"].lower()

        if title_match or content_match:
            filtered_memos.append(memo)

    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        st.metric("전체 메모 수", f"{len(memos_list)}개")
    with col_stat2:
        st.metric("표시 중", f"{len(filtered_memos)}개")

    if filtered_memos:
        for idx, m in enumerate(filtered_memos):
            t = m["title"]
            ts = m["updated_at"] or m["created_at"]
            fname = m["file_name"]
            memo_full = load_single_memo_content(fname)
            preview = _memo_preview(memo_full["content"])
            cont = memo_full["content"]

            st.markdown(
                f"""
                <div class="surface-card surface-card--compact">
                    <div class="tool-chip">Memo</div>
                    <h3 class="surface-card__title">{t}</h3>
                    <p class="surface-card__body">수정 시각 {ts}</p>
                    <p class="surface-card__body">{preview}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.expander("메모 열기 / 수정"):
                st.caption(
                    f"생성 {memo_full['created_at']} · 마지막 수정 {memo_full['updated_at']}"
                )

                edit_title = st.text_input(
                    "제목 수정", value=memo_full["title"], key=f"edit_title_{idx}_{fname}"
                )

                line_count = cont.count("\n") + 1
                dynamic_height = min(40 + (line_count * 25), 400)

                edit_content = st.text_area(
                    label="내용 수정",
                    value=cont,
                    height=dynamic_height,
                    key=f"edit_content_{idx}_{fname}",
                )

                if st.button(
                    "저장", key=f"save_{idx}_{fname}", use_container_width=True
                ):
                    new_t = edit_title.strip() or memo_full["title"]
                    save_memo_txt(new_t, edit_content, original_file_name=fname)
                    st.toast("✅ 수정되었습니다.")
                    st.rerun()

                col_copy, col_dl, col_del = st.columns([1, 1, 1])

                with col_copy:
                    copy_text = (
                        f"제목: {memo_full['title']}\n"
                        f"생성시간: {memo_full['created_at']}\n"
                        f"수정시간: {memo_full['updated_at']}\n\n"
                        f"{cont}"
                    )
                    copy_to_clipboard(
                        text=copy_text,
                        before_copy_label="복사",
                        after_copy_label="✅ 완료",
                        key=f"out_copy_{fname}",
                    )

                with col_dl:
                    st.download_button(
                        label="다운",
                        data=cont,
                        file_name=f"{safe_filename(memo_full['title']) or 'memo'}.txt",
                        mime="text/plain",
                        use_container_width=True,
                        key=f"out_dl_{fname}",
                    )

                with col_del:
                    if st.button(
                        "삭제",
                        key=f"out_del_{fname}",
                        type="secondary",
                        use_container_width=True,
                    ):
                        delete_memo_txt(fname)
                        st.toast("🗑️ 삭제되었습니다.")
                        st.rerun()
    elif memos_list and memo_query:
        st.info("검색 조건에 맞는 메모가 없습니다.")

    if memos_list:
        st.markdown(
            """
            <div class="section-block section-block--spacious">
                <p class="section-block__eyebrow">Batch</p>
                <h3 class="section-block__title">일괄 처리</h3>
                <p class="section-block__body">
                    메모를 한 번에 묶어 ZIP으로 받아 둘 수 있습니다.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

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
                st.button(
                    "📥 ZIP 다운로드 (준비 필요)",
                    disabled=True,
                    use_container_width=True,
                )

        st.markdown(
            """
            <div class="section-block section-block--spacious section-block--danger">
                <p class="section-block__eyebrow">Danger Zone</p>
                <h3 class="section-block__title">보안 관리</h3>
                <p class="section-block__body">
                    전체 메모 삭제는 복구할 수 없으니, 정리 목적이 분명할 때만 실행하세요.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.session_state.confirm_clear_memos:
            st.warning("한 번 더 누르면 전체 메모가 삭제됩니다.")

        clear_memos_label = (
            "🔥 한 번 더 누르면 전체 메모 삭제"
            if st.session_state.confirm_clear_memos
            else "🔥 모든 메모 삭제"
        )
        if st.button(
            clear_memos_label,
            type="primary",
            use_container_width=True,
            key="danger_clear_memos",
        ):
            if not st.session_state.confirm_clear_memos:
                st.session_state.confirm_clear_memos = True
                st.rerun()
            try:
                clear_all_memos()
                st.session_state.confirm_clear_memos = False
                st.toast("✅ 모든 메모가 삭제되었습니다.")
                st.rerun()
            except Exception as e:
                st.error(f"삭제 중 오류 발생: {e}")
