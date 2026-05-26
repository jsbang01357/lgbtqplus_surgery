

import logging
import json
import zipfile

import random
import tempfile
import os
from pathlib import PurePosixPath

from app.core_utils import get_now, safe_filename, slugify, ttl_cache

from app.gcs_helper import get_bucket

logger = logging.getLogger(__name__)

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


@ttl_cache(seconds=30)
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


@ttl_cache(seconds=60)
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
        generation = 0
        if blob.exists():
            try:
                blob.reload()
                generation = blob.generation or 0
                old = load_single_memo_content(original_file_name)
                created_at = old.get("created_at") or timestamp
            except Exception:
                generation = 0

        payload = _build_memo_payload(title, content, created_at, timestamp)
        blob.metadata = {
            "title": title,
            "created_at": created_at,
            "updated_at": timestamp,
        }
        try:
            blob.upload_from_string(
                payload.encode("utf-8"),
                content_type="text/plain; charset=utf-8",
                if_generation_match=generation,
            )
        except Exception as exc:
            logger.warning(f"메모 저장 중 동시성 충돌 발생: {exc}")
            raise RuntimeError("다른 사용자가 이 메모를 수정했습니다. 다시 시도해주세요.")

        load_memo_list_cached.clear()
        load_single_memo_content.clear()
        create_zip_of_memos.clear()
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


def clear_all_memos():
    bucket = get_bucket()
    blobs = list(bucket.list_blobs(prefix=f"{MEMO_PREFIX}/"))
    if blobs:
        bucket.delete_blobs(blobs)
    
    load_memo_list_cached.clear()
    load_single_memo_content.clear()
    create_zip_of_memos.clear()


@ttl_cache(seconds=60)
def create_zip_of_memos(memo_list):
    if not memo_list:
        return None

    fd, temp_path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)

    with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for m in memo_list:
            memo_full = load_single_memo_content(m["file_name"])
            safe_name = safe_filename(memo_full["title"]) or "memo"
            file_name = f"{safe_name}.txt"
            zf.writestr(file_name, memo_full["content"].encode("utf-8"))

    return temp_path


