import csv
import hashlib
import io
import logging
import mimetypes
import os
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Callable

from app.config import get_bool_config, get_config, get_int_config
from app.core_utils import get_now
from app.gcs_helper import get_bucket

logger = logging.getLogger(__name__)

DEFAULT_SYNC_ROOT = Path(os.path.expanduser(get_config("LOCAL_SYNC_ROOT", "~/Developer/jisong_workspace"))).expanduser()
DEFAULT_SYNC_PREFIX = get_config("LOCAL_SYNC_PREFIX", "workspace_sync").strip("/")
DEFAULT_SYNC_INTERVAL_SECONDS = max(
    2, get_int_config("LOCAL_SYNC_INTERVAL_SECONDS", 5)
)
DEFAULT_SYNC_ENABLED = get_bool_config("ENABLE_FOLDER_SYNC", os.getenv("K_SERVICE") is None)
SYNC_MANIFEST_NAME = "_manifest.csv"
SYNC_FILE_RECORDS_NAME = "_files.csv"
SYNC_CONFLICT_PREFIX = "_conflicts"
IGNORED_DIR_NAMES = {
    ".git",
    ".idea",
    ".venv",
    "__pycache__",
    "node_modules",
}
IGNORED_FILE_NAMES = {
    ".DS_Store",
    "Thumbs.db",
}


@dataclass
class SyncSnapshot:
    relative_path: str
    local_path: str
    blob_name: str
    size_bytes: int
    mtime_iso: str
    content_hash: str
    content_type: str


@dataclass
class SyncRunResult:
    enabled: bool
    root: str
    prefix: str
    scanned: int = 0
    uploaded: int = 0
    deleted: int = 0
    skipped: int = 0
    conflicts: int = 0
    manifest_rows: int = 0
    file_record_rows: int = 0
    root_exists: bool = True
    reason: str = ""
    started_at: str = ""
    finished_at: str = ""
    duration_ms: int = 0


@dataclass
class SyncFileRecord:
    relative_path: str
    blob_name: str
    content_hash: str
    size_bytes: int
    mtime_iso: str
    content_type: str
    status: str
    synced_at: str
    conflict_blob_name: str = ""
    remote_hash: str = ""


def get_sync_root() -> Path:
    DEFAULT_SYNC_ROOT.mkdir(parents=True, exist_ok=True)
    return DEFAULT_SYNC_ROOT


def get_sync_prefix() -> str:
    return DEFAULT_SYNC_PREFIX or "workspace_sync"


def get_manifest_blob_name() -> str:
    return f"{get_sync_prefix()}/{SYNC_MANIFEST_NAME}"


def get_file_records_blob_name() -> str:
    return f"{get_sync_prefix()}/{SYNC_FILE_RECORDS_NAME}"


def _now_ts_label() -> str:
    return get_now().strftime("%Y%m%d_%H%M%S")


def _conflict_blob_name(relative_path: str) -> str:
    path = PurePosixPath(relative_path)
    parent = path.parent
    conflict_root = PurePosixPath(get_sync_prefix()) / SYNC_CONFLICT_PREFIX
    if str(parent) in {"", "."}:
        return str(conflict_root / f"{_now_ts_label()}_{path.name}")
    return str(conflict_root / parent / f"{_now_ts_label()}_{path.name}")


def _is_hidden_path(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    parts = relative.parts
    if any(part in IGNORED_DIR_NAMES for part in parts):
        return True
    if any(part.startswith(".") for part in parts):
        return True
    if path.name in IGNORED_FILE_NAMES:
        return True
    return False


def _guess_content_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    if guessed:
        if guessed.startswith("text/") and "charset" not in guessed:
            return f"{guessed}; charset=utf-8"
        return guessed
    return "application/octet-stream"


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _snapshot_path(root: Path, path: Path) -> SyncSnapshot:
    stat = path.stat()
    relative_path = path.relative_to(root).as_posix()
    blob_name = f"{get_sync_prefix()}/{relative_path}"
    return SyncSnapshot(
        relative_path=relative_path,
        local_path=str(path),
        blob_name=blob_name,
        size_bytes=stat.st_size,
        mtime_iso=time.strftime(
            "%Y-%m-%dT%H:%M:%S%z", time.localtime(stat.st_mtime)
        ),
        content_hash=_hash_file(path),
        content_type=_guess_content_type(path),
    )


def scan_workspace(root: Path | None = None) -> list[SyncSnapshot]:
    root = (root or get_sync_root()).expanduser()
    if not root.exists():
        return []

    snapshots: list[SyncSnapshot] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if _is_hidden_path(path, root):
            continue
        snapshots.append(_snapshot_path(root, path))
    return snapshots


def _read_manifest(bucket, manifest_blob_name: str) -> dict[str, dict[str, str]]:
    blob = bucket.blob(manifest_blob_name)
    try:
        if not blob.exists():
            return {}
        raw = blob.download_as_text(encoding="utf-8")
    except Exception:
        logger.warning("sync manifest 로드에 실패했습니다.", exc_info=True)
        return {}

    reader = csv.DictReader(io.StringIO(raw))
    records: dict[str, dict[str, str]] = {}
    for row in reader:
        relative_path = (row.get("relative_path") or "").strip()
        if not relative_path:
            continue
        records[relative_path] = {
            "relative_path": relative_path,
            "blob_name": (row.get("blob_name") or "").strip()
            or f"{get_sync_prefix()}/{relative_path}",
            "content_hash": (row.get("content_hash") or "").strip(),
            "size_bytes": (row.get("size_bytes") or "").strip(),
            "mtime_iso": (row.get("mtime_iso") or "").strip(),
            "content_type": (row.get("content_type") or "").strip(),
            "synced_at": (row.get("synced_at") or "").strip(),
        }
    return records


def _read_file_records(bucket, file_records_blob_name: str) -> list[dict[str, str]]:
    blob = bucket.blob(file_records_blob_name)
    try:
        if not blob.exists():
            return []
        raw = blob.download_as_text(encoding="utf-8")
    except Exception:
        logger.warning("sync file records 로드에 실패했습니다.", exc_info=True)
        return []

    reader = csv.DictReader(io.StringIO(raw))
    records: list[dict[str, str]] = []
    for row in reader:
        relative_path = (row.get("relative_path") or "").strip()
        blob_name = (row.get("blob_name") or "").strip()
        if not relative_path or not blob_name:
            continue
        records.append(
            {
                "relative_path": relative_path,
                "blob_name": blob_name,
                "content_hash": (row.get("content_hash") or "").strip(),
                "size_bytes": (row.get("size_bytes") or "").strip(),
                "mtime_iso": (row.get("mtime_iso") or "").strip(),
                "content_type": (row.get("content_type") or "").strip(),
                "status": (row.get("status") or "").strip() or "skipped",
                "synced_at": (row.get("synced_at") or "").strip(),
                "conflict_blob_name": (row.get("conflict_blob_name") or "").strip(),
                "remote_hash": (row.get("remote_hash") or "").strip(),
            }
        )
    return records


def _write_manifest(bucket, manifest_blob_name: str, snapshots: list[SyncSnapshot]) -> None:
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "relative_path",
            "blob_name",
            "content_hash",
            "size_bytes",
            "mtime_iso",
            "content_type",
            "synced_at",
        ],
    )
    writer.writeheader()
    synced_at = get_now().isoformat()
    for snapshot in snapshots:
        writer.writerow(
            {
                "relative_path": snapshot.relative_path,
                "blob_name": snapshot.blob_name,
                "content_hash": snapshot.content_hash,
                "size_bytes": snapshot.size_bytes,
                "mtime_iso": snapshot.mtime_iso,
                "content_type": snapshot.content_type,
                "synced_at": synced_at,
            }
        )

    blob = bucket.blob(manifest_blob_name)
    blob.upload_from_string(buffer.getvalue(), content_type="text/csv; charset=utf-8")


def _write_file_records(
    bucket,
    file_records_blob_name: str,
    records: list[SyncFileRecord],
) -> None:
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "relative_path",
            "blob_name",
            "content_hash",
            "size_bytes",
            "mtime_iso",
            "content_type",
            "status",
            "synced_at",
            "conflict_blob_name",
            "remote_hash",
        ],
    )
    writer.writeheader()
    for record in records:
        writer.writerow(
            {
                "relative_path": record.relative_path,
                "blob_name": record.blob_name,
                "content_hash": record.content_hash,
                "size_bytes": record.size_bytes,
                "mtime_iso": record.mtime_iso,
                "content_type": record.content_type,
                "status": record.status,
                "synced_at": record.synced_at,
                "conflict_blob_name": record.conflict_blob_name,
                "remote_hash": record.remote_hash,
            }
        )

    blob = bucket.blob(file_records_blob_name)
    blob.upload_from_string(buffer.getvalue(), content_type="text/csv; charset=utf-8")


def sync_workspace_once(
    root: Path | None = None,
    *,
    bucket_getter: Callable[[], object] = get_bucket,
) -> SyncRunResult:
    root = (root or get_sync_root()).expanduser()
    result = SyncRunResult(
        enabled=True,
        root=str(root),
        prefix=get_sync_prefix(),
        started_at=get_now().isoformat(),
    )
    start = time.time()

    if not root.exists():
        result.root_exists = False
        result.reason = "sync root가 없습니다."
        result.finished_at = get_now().isoformat()
        result.duration_ms = int((time.time() - start) * 1000)
        return result

    snapshots = scan_workspace(root)
    result.scanned = len(snapshots)

    bucket = bucket_getter()
    manifest_blob_name = get_manifest_blob_name()
    file_records_blob_name = get_file_records_blob_name()
    remote_records = _read_manifest(bucket, manifest_blob_name)
    local_records = {snapshot.relative_path: snapshot for snapshot in snapshots}

    uploaded = 0
    skipped = 0
    deleted = 0
    conflicts = 0
    file_records: list[SyncFileRecord] = []

    for snapshot in snapshots:
        remote = remote_records.get(snapshot.relative_path)
        remote_hash = remote.get("content_hash", "") if remote else ""
        if remote and remote.get("content_hash") == snapshot.content_hash:
            skipped += 1
            file_records.append(
                SyncFileRecord(
                    relative_path=snapshot.relative_path,
                    blob_name=snapshot.blob_name,
                    content_hash=snapshot.content_hash,
                    size_bytes=snapshot.size_bytes,
                    mtime_iso=snapshot.mtime_iso,
                    content_type=snapshot.content_type,
                    status="skipped",
                    synced_at=get_now().isoformat(),
                    remote_hash=remote_hash,
                )
            )
            continue

        blob = bucket.blob(snapshot.blob_name)
        conflict_blob_name = ""
        status = "uploaded"
        if remote and remote.get("content_hash") and remote.get("content_hash") != snapshot.content_hash:
            current_blob = bucket.blob(snapshot.blob_name)
            try:
                if current_blob.exists():
                    conflict_blob_name = _conflict_blob_name(snapshot.relative_path)
                    conflict_blob = bucket.blob(conflict_blob_name)
                    if getattr(current_blob, "metadata", None):
                        conflict_blob.metadata = dict(current_blob.metadata)
                    conflict_blob.upload_from_string(
                        current_blob.download_as_bytes(),
                        content_type=current_blob.content_type or snapshot.content_type,
                    )
                    conflicts += 1
                    status = "conflict_copy"
            except Exception:
                logger.warning("sync conflict copy failed for %s", snapshot.relative_path, exc_info=True)

        blob.metadata = {
            "relative_path": snapshot.relative_path,
            "content_hash": snapshot.content_hash,
            "synced_at": get_now().isoformat(),
        }
        blob.upload_from_filename(
            snapshot.local_path, content_type=snapshot.content_type
        )
        uploaded += 1
        file_records.append(
            SyncFileRecord(
                relative_path=snapshot.relative_path,
                blob_name=snapshot.blob_name,
                content_hash=snapshot.content_hash,
                size_bytes=snapshot.size_bytes,
                mtime_iso=snapshot.mtime_iso,
                content_type=snapshot.content_type,
                status=status,
                synced_at=get_now().isoformat(),
                conflict_blob_name=conflict_blob_name,
                remote_hash=remote_hash,
            )
        )

    blobs_to_delete = []
    deleted_records = []
    for relative_path, remote in remote_records.items():
        if relative_path in local_records:
            continue
        blob_name = remote.get("blob_name") or f"{get_sync_prefix()}/{relative_path}"
        blobs_to_delete.append(bucket.blob(blob_name))
        deleted_records.append(
            SyncFileRecord(
                relative_path=relative_path,
                blob_name=blob_name,
                content_hash=remote.get("content_hash", ""),
                size_bytes=int(remote.get("size_bytes") or 0),
                mtime_iso=remote.get("mtime_iso", ""),
                content_type=remote.get("content_type", ""),
                status="deleted",
                synced_at=get_now().isoformat(),
                remote_hash=remote.get("content_hash", ""),
            )
        )

    if blobs_to_delete:
        try:
            bucket.delete_blobs(blobs_to_delete)
            deleted += len(blobs_to_delete)
            file_records.extend(deleted_records)
        except Exception:
            logger.warning("sync bulk delete failed", exc_info=True)

    _write_manifest(bucket, manifest_blob_name, snapshots)
    _write_file_records(bucket, file_records_blob_name, file_records)

    result.uploaded = uploaded
    result.deleted = deleted
    result.skipped = skipped
    result.conflicts = conflicts
    result.manifest_rows = len(snapshots)
    result.file_record_rows = len(file_records)
    result.finished_at = get_now().isoformat()
    result.duration_ms = int((time.time() - start) * 1000)
    return result


class FolderSyncService:
    def __init__(
        self,
        *,
        root: Path | None = None,
        enabled: bool = DEFAULT_SYNC_ENABLED,
        interval_seconds: int = DEFAULT_SYNC_INTERVAL_SECONDS,
        bucket_getter: Callable[[], object] = get_bucket,
    ):
        self.root = (root or get_sync_root()).expanduser()
        self.enabled = enabled
        self.interval_seconds = max(2, int(interval_seconds))
        self.bucket_getter = bucket_getter
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_result: SyncRunResult | None = None
        self._last_error = ""
        self._last_run_at = ""

    def start(self) -> None:
        if not self.enabled or self._thread and self._thread.is_alive():
            return
        self.root.mkdir(parents=True, exist_ok=True)
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="folder-sync-service",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def _run_loop(self) -> None:
        self.sync_now()
        while not self._stop_event.wait(self.interval_seconds):
            self.sync_now()

    def sync_now(self) -> SyncRunResult:
        with self._lock:
            self._last_run_at = get_now().isoformat()
            try:
                result = sync_workspace_once(
                    self.root, bucket_getter=self.bucket_getter
                )
                self._last_result = result
                self._last_error = ""
                return result
            except Exception as exc:
                self._last_error = str(exc)
                logger.exception("folder sync failed")
                result = SyncRunResult(
                    enabled=self.enabled,
                    root=str(self.root),
                    prefix=get_sync_prefix(),
                    reason=str(exc),
                    started_at=self._last_run_at,
                    finished_at=get_now().isoformat(),
                )
                self._last_result = result
                return result

    def status(self) -> dict:
        last_result = asdict(self._last_result) if self._last_result else {}
        return {
            "enabled": self.enabled,
            "running": bool(self._thread and self._thread.is_alive()),
            "root": str(self.root),
            "prefix": get_sync_prefix(),
            "interval_seconds": self.interval_seconds,
            "last_run_at": self._last_run_at,
            "last_error": self._last_error,
            "last_result": last_result,
            "manifest_blob_name": get_manifest_blob_name(),
            "file_records_blob_name": get_file_records_blob_name(),
            "file_records": _read_file_records(self.bucket_getter(), get_file_records_blob_name()),
        }


_FOLDER_SYNC_SERVICE: FolderSyncService | None = None


def get_folder_sync_service() -> FolderSyncService:
    global _FOLDER_SYNC_SERVICE
    if _FOLDER_SYNC_SERVICE is None:
        _FOLDER_SYNC_SERVICE = FolderSyncService()
    return _FOLDER_SYNC_SERVICE


def start_folder_sync_service() -> FolderSyncService:
    service = get_folder_sync_service()
    service.start()
    return service


def stop_folder_sync_service() -> None:
    global _FOLDER_SYNC_SERVICE
    if _FOLDER_SYNC_SERVICE is not None:
        _FOLDER_SYNC_SERVICE.stop()
