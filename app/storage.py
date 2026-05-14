import streamlit as st
import datetime
import zipfile
import io
import mimetypes
import html
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path, PurePosixPath
from typing import Optional
from urllib.parse import quote

from app.core_utils import get_now, KST
from app.gcs_helper import get_bucket

UPLOAD_PREFIX = "uploads"
MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024
FILE_ICON_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons" / "filetypes"


@dataclass
class GCSFileInfo:
    name: str
    blob_name: str
    size: int
    updated: Optional[datetime.datetime]
    content_type: Optional[str]


def init_storage():
    return


def guess_content_type(filename: str) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def normalize_blob_name(prefix: str, filename: str) -> str:
    prefix = prefix.strip("/")
    safe_name = filename.replace("\\", "_").replace("/", "_")
    return str(PurePosixPath(prefix) / safe_name)


def _list_uploaded_files_from_gcs():
    bucket = get_bucket()
    blobs = bucket.list_blobs(prefix=f"{UPLOAD_PREFIX}/")
    items = []

    for blob in blobs:
        if blob.name.endswith("/"):
            continue
        items.append(
            GCSFileInfo(
                name=PurePosixPath(blob.name).name,
                blob_name=blob.name,
                size=blob.size or 0,
                updated=blob.updated,
                content_type=blob.content_type,
            )
        )

    items.sort(
        key=lambda x: x.updated or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc),
        reverse=True,
    )
    return items


@st.cache_data(ttl=30)
def list_uploaded_files_cached():
    return _list_uploaded_files_from_gcs()


def list_uploaded_files():
    return list_uploaded_files_cached()


def save_uploaded_file(uploaded_file):
    try:
        bucket = get_bucket()

        name, ext = PurePosixPath(uploaded_file.name).stem, PurePosixPath(uploaded_file.name).suffix
        timestamp = get_now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"{name}_{timestamp}{ext}"

        blob_name = normalize_blob_name(UPLOAD_PREFIX, new_filename)
        blob = bucket.blob(blob_name)

        content = uploaded_file.getvalue()
        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            st.error(f"{uploaded_file.name} 파일이 50MB 제한을 초과했습니다.")
            return False
        content_type = uploaded_file.type or guess_content_type(uploaded_file.name)

        blob.upload_from_string(content, content_type=content_type)

        # 저장 후 목록 캐시 비우기
        list_uploaded_files_cached.clear()
        create_zip_of_files.clear()
        return True
    except Exception as e:
        st.error(f"업로드 오류: {e}")
        return False


def save_generated_file(
    filename: str,
    content: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise ValueError("생성된 파일이 50MB 제한을 초과했습니다.")

    name = PurePosixPath(filename).stem or "file"
    ext = PurePosixPath(filename).suffix
    timestamp = get_now().strftime("%Y%m%d_%H%M%S")
    new_filename = f"{name}_{timestamp}{ext}"
    blob_name = normalize_blob_name(UPLOAD_PREFIX, new_filename)

    bucket = get_bucket()
    blob = bucket.blob(blob_name)
    blob.upload_from_string(content, content_type=content_type)

    list_uploaded_files_cached.clear()
    create_zip_of_files.clear()
    return new_filename


def delete_uploaded_file(blob_name: str):
    bucket = get_bucket()
    blob = bucket.blob(blob_name)
    blob.delete()

    # 삭제 후 목록 캐시 비우기
    list_uploaded_files_cached.clear()
    download_file_bytes.clear()
    create_zip_of_files.clear()


def clear_all_uploaded_files():
    bucket = get_bucket()
    blobs = list(bucket.list_blobs(prefix=f"{UPLOAD_PREFIX}/"))
    for blob in blobs:
        blob.delete()

    # 전체 삭제 후 목록 캐시 비우기
    list_uploaded_files_cached.clear()
    download_file_bytes.clear()
    create_zip_of_files.clear()


@st.cache_data(ttl=300)
def download_file_bytes(blob_name: str) -> bytes:
    bucket = get_bucket()
    blob = bucket.blob(blob_name)
    return blob.download_as_bytes()


def create_file_download_url(file_info: GCSFileInfo) -> str:
    bucket = get_bucket()
    blob = bucket.blob(file_info.blob_name)
    safe_ascii_name = file_info.name.replace("\\", "_").replace('"', "'")
    encoded_name = quote(file_info.name)
    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=15),
        method="GET",
        response_disposition=(
            f"attachment; filename=\"{safe_ascii_name}\"; filename*=UTF-8''{encoded_name}"
        ),
        response_type=file_info.content_type or "application/octet-stream",
    )


@st.cache_data(ttl=60)
def create_zip_of_files():
    files = list_uploaded_files()
    if not files:
        return None

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            data = download_file_bytes(f.blob_name)
            zf.writestr(f.name, data)

    zip_buffer.seek(0)
    return zip_buffer


def _format_file_size(size: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def _file_icon_key(filename: str) -> str:
    ext = PurePosixPath(filename).suffix.lower()
    if ext == ".pdf":
        return "pdf"
    if ext in {".doc", ".docx"}:
        return "word"
    if ext in {".ppt", ".pptx", ".key"}:
        return "powerpoint"
    if ext in {".xls", ".xlsx", ".csv"}:
        return "excel"
    if ext in {".txt", ".rtf"}:
        return "text"
    if ext in {".md", ".markdown"}:
        return "markdown"
    if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"}:
        return "image"
    if ext in {".zip", ".7z", ".rar", ".tar", ".gz"}:
        return "archive"
    if ext in {".mp4", ".mov", ".avi", ".mkv", ".mp3", ".wav", ".m4a"}:
        return "media"
    return "generic"


def _file_type_label(filename: str) -> str:
    ext = PurePosixPath(filename).suffix.lower().lstrip(".")
    if not ext:
        return "FILE"
    return ext.upper()


@st.cache_data(show_spinner=False)
def _load_file_icon_svg(icon_key: str) -> str:
    icon_path = FILE_ICON_DIR / f"{icon_key}.svg"
    if not icon_path.exists():
        icon_path = FILE_ICON_DIR / "generic.svg"
    return icon_path.read_text(encoding="utf-8")


def render_file_manager():
    init_storage()


    if "file_uploader_key" not in st.session_state:
        st.session_state["file_uploader_key"] = 0
    if "confirm_clear_files" not in st.session_state:
        st.session_state.confirm_clear_files = False
    if "scroll_to_bottom_once" not in st.session_state:
        st.session_state.scroll_to_bottom_once = False

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

    st.markdown(
        """
        <div class="section-block">
            <p class="section-block__eyebrow">Upload</p>
            <h2 class="section-block__title">새 파일 추가</h2>
            <p class="section-block__body">
                여러 파일을 한 번에 올리면 업로드 시각이 자동으로 붙어서 덮어쓰지 않고 저장됩니다.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.file_uploader(
        "파일 선택 (PPT, PDF 등, 파일당 최대 50MB)",
        accept_multiple_files=True,
        key=f"uploader_{st.session_state['file_uploader_key']}",
        on_change=process_uploaded_files,
    )

    st.markdown(
        """
        <div class="section-block section-block--spacious">
            <p class="section-block__eyebrow">Library</p>
            <h2 class="section-block__title">저장된 파일</h2>
            <p class="section-block__body">
                최근 업로드된 파일부터 정렬되어 보이며, 바로 다운로드하거나 삭제할 수 있습니다.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    files = list_uploaded_files()
    file_query = st.text_input(
        "파일 검색",
        placeholder="파일명으로 찾기",
        key="file_search_query",
    ).strip().lower()

    filtered_files = [
        file_info for file_info in files if file_query in file_info.name.lower()
    ]

    total_size = sum(file_info.size for file_info in files)
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1:
        st.metric("전체 파일 수", f"{len(files)}개")
    with col_stat2:
        st.metric("표시 중", f"{len(filtered_files)}개")
    with col_stat3:
        st.metric("전체 용량", _format_file_size(total_size))

    if filtered_files:
        for file_info in filtered_files:
            file_time = "-"
            if file_info.updated:
                file_time = file_info.updated.astimezone(KST).strftime("%Y-%m-%d %H:%M")
            icon_key = _file_icon_key(file_info.name)
            icon_svg = _load_file_icon_svg(icon_key)
            file_name = html.escape(file_info.name)
            file_type = html.escape(_file_type_label(file_info.name))
            st.markdown(
                f"""
                <div class="surface-card surface-card--compact">
                    <div class="file-card__header">
                        <div class="file-card__icon" aria-hidden="true">{icon_svg}</div>
                        <div class="file-card__meta">
                            <div class="file-card__meta-row">
                                <span class="file-card__type">{file_type}</span>
                            </div>
                            <h3 class="surface-card__title">{file_name}</h3>
                            <p class="surface-card__body">수정 시각 {file_time}</p>
                            <p class="surface-card__body">용량 {_format_file_size(file_info.size)}</p>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col_download, col_delete = st.columns([1, 1])

            with col_download:
                try:
                    st.link_button(
                        "다운로드",
                        create_file_download_url(file_info),
                        use_container_width=True,
                    )
                except Exception as e:
                    st.button("다운로드", disabled=True, use_container_width=True)
                    st.caption(f"다운로드 링크 생성 실패: {e}")

            with col_delete:
                if st.button("삭제", key=f"del_{file_info.blob_name}", use_container_width=True):
                    try:
                        delete_uploaded_file(file_info.blob_name)
                        st.toast(f"🗑️ '{file_info.name}' 삭제됨")
                        st.rerun()
                    except Exception as e:
                        st.error(f"삭제 오류: {e}")

        st.markdown(
            """
            <div class="section-block section-block--spacious">
                <p class="section-block__eyebrow">Batch</p>
                <h3 class="section-block__title">일괄 처리</h3>
                <p class="section-block__body">
                    파일을 한 번에 ZIP으로 묶어서 다운로드할 수 있습니다.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        zip_data = create_zip_of_files()
        st.download_button(
            label="📥 ZIP 다운로드",
            data=zip_data,
            file_name=f"files_{get_now().strftime('%Y%m%d_%H%M')}.zip",
            mime="application/zip",
            use_container_width=True,
            disabled=zip_data is None,
        )

        st.markdown(
            """
            <div class="section-block section-block--spacious section-block--danger">
                <p class="section-block__eyebrow">Danger Zone</p>
                <h3 class="section-block__title">보안 관리</h3>
                <p class="section-block__body">
                    전체 파일 삭제는 되돌릴 수 없으니 저장소를 비울 때만 사용하세요.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.session_state.confirm_clear_files:
            st.warning("한 번 더 누르면 전체 파일이 삭제됩니다.")

        clear_files_label = (
            "🔥 한 번 더 누르면 전체 파일 삭제"
            if st.session_state.confirm_clear_files
            else "🔥 모든 파일 삭제"
        )
        if st.button(
            clear_files_label,
            type="primary",
            use_container_width=True,
            key="danger_clear_files",
        ):
            if not st.session_state.confirm_clear_files:
                st.session_state.confirm_clear_files = True
                st.session_state.scroll_to_bottom_once = True
                st.rerun()
            try:
                clear_all_uploaded_files()
                st.session_state.confirm_clear_files = False
                st.toast("✅ 모든 파일이 삭제되었습니다.")
                st.rerun()
            except Exception as e:
                st.error(f"삭제 중 오류 발생: {e}")
    elif files and file_query:
        st.info("검색 조건에 맞는 파일이 없습니다.")
    else:
        st.info("현재 저장된 파일이 없습니다.")


    if st.session_state.get("scroll_to_bottom_once"):
        st.session_state.scroll_to_bottom_once = False
        st.markdown(
            """
            <script>
            window.parent.document
                .querySelector('[data-testid="stAppViewContainer"]')
                .scrollTo({top: 999999, behavior: 'smooth'});
            </script>
            """,
            unsafe_allow_html=True,
        )
