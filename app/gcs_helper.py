import json
import logging
import os
from pathlib import Path
from typing import Any

from google.cloud import storage
from google.oauth2 import service_account
from app.config import (
    get_config,
    get_bucket_name as config_bucket_name,
    get_local_storage_root,
    get_storage_backend,
    offline_mode,
)

_GCS_CLIENT_CACHE = None
_LOCAL_BUCKET_CACHE = {}
logger = logging.getLogger(__name__)


class LocalStoragePreconditionError(RuntimeError):
    pass


class LocalBlob:
    def __init__(self, root: Path, name: str):
        self._root = root
        self.name = name.replace("\\", "/").strip("/")
        self.generation = 0

    @property
    def _path(self) -> Path:
        parts = [part for part in self.name.split("/") if part and part != "."]
        if any(part == ".." for part in parts):
            raise ValueError(f"Invalid local blob name: {self.name}")

        target = (self._root.joinpath(*parts)).resolve()
        root = self._root.resolve()
        if target != root and root not in target.parents:
            raise ValueError(f"Local blob escapes storage root: {self.name}")
        return target

    def exists(self) -> bool:
        return self._path.is_file()

    def reload(self):
        if self.exists():
            self.generation = self._path.stat().st_mtime_ns
        else:
            self.generation = 0

    def download_as_text(self, encoding: str = "utf-8") -> str:
        return self._path.read_text(encoding=encoding)

    def upload_from_string(
        self,
        data: str | bytes,
        content_type: str | None = None,
        if_generation_match: int | None = None,
        **_: Any,
    ):
        del content_type
        path = self._path
        current_generation = path.stat().st_mtime_ns if path.exists() else 0
        if if_generation_match is not None and current_generation != if_generation_match:
            raise LocalStoragePreconditionError("Local blob generation mismatch.")

        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, bytes):
            path.write_bytes(data)
        else:
            path.write_text(data, encoding="utf-8")
        self.reload()

    def delete(self):
        path = self._path
        if path.exists():
            path.unlink()
        self._remove_empty_parents(path.parent)
        self.generation = 0

    def _remove_empty_parents(self, directory: Path):
        root = self._root.resolve()
        current = directory.resolve()
        while current != root and root in current.parents:
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent


class LocalBucket:
    def __init__(self, name: str, root: str):
        self.name = name
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def blob(self, name: str) -> LocalBlob:
        return LocalBlob(self.root, name)

    def list_blobs(self, prefix: str = "") -> list[LocalBlob]:
        clean_prefix = prefix.replace("\\", "/").lstrip("/")
        if any(part == ".." for part in clean_prefix.split("/")):
            raise ValueError(f"Invalid local blob prefix: {prefix}")

        if not self.root.exists():
            return []

        blobs = []
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue
            name = path.relative_to(self.root).as_posix()
            if name.startswith(clean_prefix):
                blob = LocalBlob(self.root, name)
                blob.reload()
                blobs.append(blob)
        blobs.sort(key=lambda item: item.name)
        return blobs


def _load_service_account_info(raw_value: str) -> dict | None:
    if not raw_value:
        return None

    candidate = raw_value.strip()
    if not candidate:
        return None

    if candidate.startswith("{"):
        info = json.loads(candidate)
    elif os.path.exists(candidate):
        with open(candidate, "r", encoding="utf-8") as handle:
            info = json.load(handle)
    else:
        raise ValueError("GCP_SERVICE_ACCOUNT_JSON must be raw JSON or a readable file path.")

    if "private_key" in info and isinstance(info["private_key"], str):
        info["private_key"] = info["private_key"].replace("\\n", "\n")
    return info

def get_gcs_client() -> storage.Client:
    global _GCS_CLIENT_CACHE
    if _GCS_CLIENT_CACHE is not None:
        return _GCS_CLIENT_CACHE

    sa_json = get_config("GCP_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        # Try to reconstruct from secrets [gcp_service_account] section
        try:
            from app.config import get_secrets_dict
            secrets = get_secrets_dict()
            if "gcp_service_account" in secrets:
                sa_info = dict(secrets["gcp_service_account"])
                # Handle nested private_key with newlines if needed
                if "private_key" in sa_info:
                    sa_info["private_key"] = sa_info["private_key"].replace("\\n", "\n")
                sa_json = json.dumps(sa_info)
        except Exception:
            pass

    if sa_json:
        try:
            info = _load_service_account_info(sa_json)
            credentials = service_account.Credentials.from_service_account_info(info)
            _GCS_CLIENT_CACHE = storage.Client(credentials=credentials, project=info["project_id"])
            return _GCS_CLIENT_CACHE
        except Exception as e:
            logger.warning("GCS service account JSON 로드 실패: %s", e, exc_info=True)

    # Cloud Run/ADC fallback
    _GCS_CLIENT_CACHE = storage.Client()
    return _GCS_CLIENT_CACHE


def get_bucket_name() -> str:
    bucket_name = config_bucket_name()
    if bucket_name:
        return bucket_name

    raise RuntimeError("GCS bucket name is not configured.")


def _use_local_storage() -> bool:
    return offline_mode() or get_storage_backend() in {"local", "file", "filesystem", "offline"}


def get_local_bucket() -> LocalBucket:
    bucket_name = get_bucket_name()
    root = get_local_storage_root()
    cache_key = (bucket_name, str(Path(root).expanduser().resolve()))
    if cache_key not in _LOCAL_BUCKET_CACHE:
        _LOCAL_BUCKET_CACHE[cache_key] = LocalBucket(bucket_name, root)
    return _LOCAL_BUCKET_CACHE[cache_key]


def get_bucket():
    if _use_local_storage():
        return get_local_bucket()
    return get_gcs_client().bucket(get_bucket_name())


def get_logs_blob_name() -> str:
    return "logs/access_log.json"
