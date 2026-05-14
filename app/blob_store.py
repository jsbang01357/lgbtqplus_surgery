import datetime
import json
import os
from pathlib import Path, PurePosixPath

from google.cloud import storage


LOCAL_BACKENDS = {"local", "local_mirror"}


def get_storage_backend() -> str:
    return os.getenv("STORAGE_BACKEND", "gcs").strip().lower() or "gcs"


def is_local_storage_backend() -> bool:
    return get_storage_backend() in LOCAL_BACKENDS


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _local_root() -> Path:
    return Path(os.getenv("LOCAL_STORAGE_ROOT", "/data/jisong-cloud")).resolve()


def _metadata_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.meta.json")


def _utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _parse_datetime(value: str | None) -> datetime.datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed


def _safe_blob_path(root: Path, blob_name: str) -> Path:
    normalized = PurePosixPath(blob_name)
    if normalized.is_absolute() or ".." in normalized.parts:
        raise ValueError(f"Invalid blob name: {blob_name}")
    path = (root / Path(*normalized.parts)).resolve()
    if root not in path.parents and path != root:
        raise ValueError(f"Invalid blob path: {blob_name}")
    return path


def _local_blob_names(root: Path, prefix: str = "") -> list[str]:
    base = _safe_blob_path(root, prefix)
    if not base.exists():
        return []
    names = []
    for path in base.rglob("*"):
        if not path.is_file() or path.name.endswith(".meta.json"):
            continue
        names.append(path.relative_to(root).as_posix())
    return sorted(names)


class LocalBlob:
    def __init__(
        self,
        bucket: "LocalMirrorBucket",
        name: str,
        size: int = 0,
        updated: datetime.datetime | None = None,
        content_type: str | None = None,
        metadata: dict | None = None,
    ):
        self.bucket = bucket
        self.name = name
        self.size = size
        self.updated = updated
        self.content_type = content_type
        self.metadata = metadata or {}
        self.generation = None

    @property
    def _path(self) -> Path:
        return _safe_blob_path(self.bucket.root, self.name)

    @property
    def _meta_path(self) -> Path:
        return _metadata_path(self._path)

    def _load_metadata(self):
        path = self._path
        if not path.exists():
            return
        try:
            raw = json.loads(self._meta_path.read_text(encoding="utf-8"))
        except Exception:
            raw = {}
        stat = path.stat()
        self.size = stat.st_size
        self.updated = _parse_datetime(raw.get("updated")) or datetime.datetime.fromtimestamp(
            stat.st_mtime, tz=datetime.timezone.utc
        )
        self.content_type = raw.get("content_type")
        self.metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}

    def _write_metadata(self, content_type: str | None):
        self._meta_path.write_text(
            json.dumps(
                {
                    "content_type": content_type,
                    "metadata": self.metadata or {},
                    "updated": _utc_now().isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self._load_metadata()

    def exists(self) -> bool:
        if (
            not self._path.exists()
            and self.bucket.should_pull_from_gcs
            and self.bucket.remote_blob_exists(self.name)
        ):
            self.bucket.pull_blob_from_gcs(self.name)
        return self._path.exists()

    def reload(self):
        self._load_metadata()

    def upload_from_string(self, data, content_type: str | None = None, **kwargs):
        if isinstance(data, str):
            payload = data.encode("utf-8")
        else:
            payload = bytes(data)

        path = self._path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        self._write_metadata(content_type)

        if self.bucket.should_mirror_to_gcs:
            remote_blob = self.bucket.remote_bucket.blob(self.name)
            remote_blob.metadata = self.metadata or {}
            mirror_kwargs = dict(kwargs)
            mirror_kwargs.pop("if_generation_match", None)
            remote_blob.upload_from_string(
                payload, content_type=content_type, **mirror_kwargs
            )

    def download_as_bytes(self) -> bytes:
        if not self.exists() and self.bucket.should_pull_from_gcs:
            self.bucket.pull_blob_from_gcs(self.name)
        return self._path.read_bytes()

    def download_as_text(self, encoding: str = "utf-8") -> str:
        return self.download_as_bytes().decode(encoding)

    def delete(self):
        if self._path.exists():
            self._path.unlink()
        if self._meta_path.exists():
            self._meta_path.unlink()
        if self.bucket.should_mirror_to_gcs:
            remote_blob = self.bucket.remote_bucket.blob(self.name)
            if remote_blob.exists():
                remote_blob.delete()

    def generate_signed_url(self, *args, **kwargs):
        raise RuntimeError("로컬 저장소 파일은 앱의 다운로드 버튼으로 내려받습니다.")


class LocalMirrorBucket:
    def __init__(self, remote_bucket: storage.Bucket | None = None):
        self.root = _local_root()
        self.root.mkdir(parents=True, exist_ok=True)
        self.remote_bucket = remote_bucket
        self.should_mirror_to_gcs = (
            get_storage_backend() == "local_mirror"
            and remote_bucket is not None
            and _bool_env("LOCAL_STORAGE_SYNC_TO_GCS", True)
        )
        self.should_pull_from_gcs = (
            get_storage_backend() == "local_mirror"
            and remote_bucket is not None
            and _bool_env("LOCAL_STORAGE_PULL_FROM_GCS", True)
        )
        self.should_push_to_gcs = self.should_mirror_to_gcs

    def blob(self, blob_name: str) -> LocalBlob:
        blob = LocalBlob(self, blob_name)
        blob._load_metadata()
        return blob

    def list_blobs(self, prefix: str = ""):
        if self.should_pull_from_gcs:
            self.pull_prefix_from_gcs(prefix)
        if self.should_push_to_gcs:
            self.push_prefix_to_gcs(prefix)

        base = _safe_blob_path(self.root, prefix)
        if not base.exists():
            return []

        blobs = []
        for path in base.rglob("*"):
            if not path.is_file() or path.name.endswith(".meta.json"):
                continue
            blob_name = path.relative_to(self.root).as_posix()
            blob = self.blob(blob_name)
            blobs.append(blob)
        return blobs

    def pull_prefix_from_gcs(self, prefix: str):
        if self.remote_bucket is None:
            return
        for remote_blob in self.remote_bucket.list_blobs(prefix=prefix):
            if remote_blob.name.endswith("/"):
                continue
            local_blob = self.blob(remote_blob.name)
            local_updated = local_blob.updated
            remote_updated = remote_blob.updated
            if local_blob.exists() and local_updated and remote_updated:
                if local_updated >= remote_updated:
                    continue
            self._write_remote_blob(remote_blob)

    def push_prefix_to_gcs(self, prefix: str):
        if self.remote_bucket is None:
            return
        for blob_name in _local_blob_names(self.root, prefix):
            local_blob = self.blob(blob_name)
            remote_blob = self.remote_bucket.blob(blob_name)
            remote_exists = remote_blob.exists()
            remote_updated = getattr(remote_blob, "updated", None)
            if remote_exists and local_blob.updated and remote_updated:
                if remote_updated >= local_blob.updated:
                    continue
            remote_blob.metadata = local_blob.metadata or {}
            remote_blob.upload_from_string(
                local_blob.download_as_bytes(),
                content_type=local_blob.content_type,
            )

    def sync_prefix(self, prefix: str):
        if self.should_pull_from_gcs:
            self.pull_prefix_from_gcs(prefix)
        if self.should_push_to_gcs:
            self.push_prefix_to_gcs(prefix)

    def sync_all(self):
        for prefix in ("uploads/", "memos/", "logs/"):
            self.sync_prefix(prefix)

    def get_status(self) -> dict:
        local_files = _local_blob_names(self.root)
        status = {
            "backend": get_storage_backend(),
            "root": str(self.root),
            "local_file_count": len(local_files),
            "local_total_bytes": sum(
                _safe_blob_path(self.root, name).stat().st_size for name in local_files
            ),
            "sync_to_gcs": self.should_mirror_to_gcs,
            "pull_from_gcs": self.should_pull_from_gcs,
            "remote_available": self.remote_bucket is not None,
        }
        if self.remote_bucket is not None:
            try:
                status["remote_file_count"] = sum(
                    1
                    for blob in self.remote_bucket.list_blobs()
                    if not blob.name.endswith("/")
                )
            except Exception as exc:
                status["remote_error"] = str(exc)
        return status

    def pull_blob_from_gcs(self, blob_name: str):
        if self.remote_bucket is None:
            return
        remote_blob = self.remote_bucket.blob(blob_name)
        if remote_blob.exists():
            self._write_remote_blob(remote_blob)

    def remote_blob_exists(self, blob_name: str) -> bool:
        if self.remote_bucket is None:
            return False
        try:
            return self.remote_bucket.blob(blob_name).exists()
        except Exception:
            return False

    def _write_remote_blob(self, remote_blob):
        path = _safe_blob_path(self.root, remote_blob.name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(remote_blob.download_as_bytes())
        metadata = {
            "content_type": remote_blob.content_type,
            "metadata": remote_blob.metadata or {},
            "updated": (remote_blob.updated or _utc_now()).isoformat(),
        }
        _metadata_path(path).write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
