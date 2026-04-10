import streamlit as st
import datetime
import zipfile
import io
import mimetypes
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Optional

from google.cloud import storage
from google.oauth2 import service_account

from core_utils import get_now, KST

UPLOAD_PREFIX = "uploads"


@dataclass
class GCSFileInfo:
    name: str
    blob_name: str
    size: int
    updated: Optional[datetime.datetime]
    content_type: Optional[str]


@st.cache_resource
def get_gcs_client() -> storage.Client:
    info = dict(st.secrets["gcp_service_account"])
    credentials = service_account.Credentials.from_service_account_info(info)
    return storage.Client(credentials=credentials, project=info["project_id"])


@st.cache_resource
def get_bucket_name():
    return st.secrets["gcs"]["bucket_name"]


def get_bucket():
    client = get_gcs_client()
    return client.bucket(get_bucket_name())


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
        content_type = uploaded_file.type or guess_content_type(uploaded_file.name)

        blob.upload_from_string(content, content_type=content_type)

        # 저장 후 목록 캐시 비우기
        list_uploaded_files_cached.clear()
        return True
    except Exception as e:
        st.error(f"업로드 오류: {e}")
        return False


def delete_uploaded_file(blob_name: str):
    bucket = get_bucket()
    blob = bucket.blob(blob_name)
    blob.delete()

    # 삭제 후 목록 캐시 비우기
    list_uploaded_files_cached.clear()


def clear_all_uploaded_files():
    bucket = get_bucket()
    blobs = list(bucket.list_blobs(prefix=f"{UPLOAD_PREFIX}/"))
    for blob in blobs:
        blob.delete()

    # 전체 삭제 후 목록 캐시 비우기
    list_uploaded_files_cached.clear()


def download_file_bytes(blob_name: str) -> bytes:
    bucket = get_bucket()
    blob = bucket.blob(blob_name)
    return blob.download_as_bytes()


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


def render_file_manager():
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
        on_change=process_uploaded_files,
    )

    st.markdown("---")
    st.subheader("💾 저장된 파일")

    files = list_uploaded_files()

    if files:
        for file_info in files:
            file_time = "-"
            if file_info.updated:
                file_time = file_info.updated.astimezone(KST).strftime("%Y-%m-%d %H:%M")

            col_d1, col_d2 = st.columns([4, 1])

            with col_d1:
                data = download_file_bytes(file_info.blob_name)
                st.download_button(
                    label=f"{file_info.name} ({file_time})",
                    data=data,
                    file_name=file_info.name,
                    mime=file_info.content_type or "application/octet-stream",
                    use_container_width=True,
                    key=f"dl_{file_info.blob_name}",
                )

            with col_d2:
                if st.button("🗑️", key=f"del_{file_info.blob_name}", use_container_width=True):
                    try:
                        delete_uploaded_file(file_info.blob_name)
                        st.toast(f"🗑️ '{file_info.name}' 삭제됨")
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
                use_container_width=True,
            )

        st.markdown("---")
        st.markdown("🧹 보안 관리")
        if st.button("🔥 모든 파일 삭제", type="primary", use_container_width=True):
            try:
                clear_all_uploaded_files()
                st.toast("✅ 모든 파일이 삭제되었습니다.")
                st.rerun()
            except Exception as e:
                st.error(f"삭제 중 오류 발생: {e}")
    else:
        st.write("📂 현재 저장된 파일이 없습니다.")