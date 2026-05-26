
import datetime
import zipfile
import mimetypes

import re
import tempfile
import os
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path, PurePosixPath
from typing import Optional
from urllib.parse import quote

from app.core_utils import get_now, ttl_cache
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


def _display_file_name(blob_name: str, metadata: dict | None = None) -> str:
    metadata = metadata or {}
    if metadata.get("original_name"):
        return metadata["original_name"]
    filename = PurePosixPath(blob_name).name
    return _strip_timestamp_suffix(filename)


def _strip_timestamp_suffix(filename: str) -> str:
    path = PurePosixPath(filename)
    stem = re.sub(r"_[0-9]{8}_[0-9]{6}$", "", path.stem)
    return f"{stem}{path.suffix}"


def _list_uploaded_files_from_gcs():
    bucket = get_bucket()
    blobs = bucket.list_blobs(prefix=f"{UPLOAD_PREFIX}/")
    items = []

    for blob in blobs:
        if blob.name.endswith("/"):
            continue
        items.append(
            GCSFileInfo(
                name=_display_file_name(blob.name, blob.metadata),
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


@ttl_cache(seconds=30)
def list_uploaded_files_cached():
    return _list_uploaded_files_from_gcs()


def list_uploaded_files():
    return list_uploaded_files_cached()


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
    return new_filename


def delete_uploaded_file(blob_name: str):
    if not blob_name:
        return
    bucket = get_bucket()
    blob = bucket.blob(blob_name)
    if blob.exists():
        blob.delete()
    
    # 삭제 후 목록 캐시 비우기
    list_uploaded_files_cached.clear()


def clear_all_uploaded_files():
    bucket = get_bucket()
    blobs = list(bucket.list_blobs(prefix=f"{UPLOAD_PREFIX}/"))
    if blobs:
        bucket.delete_blobs(blobs)

    # 전체 삭제 후 목록 캐시 비우기
    list_uploaded_files_cached.clear()


def download_file_bytes(blob_name: str) -> tuple[bytes, str, str]:
    bucket = get_bucket()
    blob = bucket.blob(blob_name)
    content = blob.download_as_bytes()
    metadata = blob.metadata or {}
    original_name = _display_file_name(blob_name, metadata)
    content_type = blob.content_type or guess_content_type(original_name)
    return content, content_type, original_name


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


def create_file_download_url_safe(file_info: GCSFileInfo) -> str:
    try:
        return create_file_download_url(file_info)
    except Exception:
        return ""


def create_zip_of_files():
    files = list_uploaded_files()
    if not files:
        return None

    bucket = get_bucket()
    fd, temp_path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)

    with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            blob = bucket.blob(f.blob_name)
            with zf.open(f.name, "w") as dest:
                blob.download_to_file(dest)

    return temp_path


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


@ttl_cache(seconds=3600)
def _load_file_icon_svg(icon_key: str) -> str:
    icon_path = FILE_ICON_DIR / f"{icon_key}.svg"
    if not icon_path.exists():
        icon_path = FILE_ICON_DIR / "generic.svg"
    return icon_path.read_text(encoding="utf-8")
