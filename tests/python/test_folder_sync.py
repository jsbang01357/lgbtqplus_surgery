import csv
import io
import tempfile
import unittest
from pathlib import Path

from app.folder_sync import get_manifest_blob_name, scan_workspace, sync_workspace_once


class FakeBlob:
    def __init__(self, bucket, name):
        self.bucket = bucket
        self.name = name
        stored = self.bucket.objects.get(self.name, {})
        self.metadata = dict(stored.get("metadata", {}))
        self.content_type = stored.get("content_type", "")

    def exists(self):
        return self.name in self.bucket.objects

    def download_as_text(self, encoding="utf-8"):
        return self.bucket.objects[self.name]["data"].decode(encoding)

    def download_as_bytes(self):
        return self.bucket.objects[self.name]["data"]

    def upload_from_string(self, data, content_type=None):
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.content_type = content_type or self.content_type
        self.bucket.objects[self.name] = {
            "data": data,
            "content_type": self.content_type,
            "metadata": dict(self.metadata),
        }

    def upload_from_filename(self, filename, content_type=None):
        with open(filename, "rb") as handle:
            self.upload_from_string(handle.read(), content_type=content_type)

    def delete(self):
        self.bucket.objects.pop(self.name, None)


class FakeBucket:
    def __init__(self):
        self.objects = {}

    def blob(self, name):
        return FakeBlob(self, name)


def _manifest_csv(rows):
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
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


class FolderSyncTests(unittest.TestCase):
    def test_scan_workspace_ignores_hidden_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "labs").mkdir()
            (root / "labs" / "result.csv").write_text("a,b\n1,2\n", encoding="utf-8")
            (root / ".git").mkdir()
            (root / ".git" / "config").write_text("ignored", encoding="utf-8")
            (root / ".DS_Store").write_text("ignored", encoding="utf-8")

            snapshots = scan_workspace(root)

        self.assertEqual([item.relative_path for item in snapshots], ["labs/result.csv"])

    def test_sync_workspace_uploads_changes_and_rewrites_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = root / "workspace" / "patient_001"
            data_dir.mkdir(parents=True)
            csv_file = data_dir / "labs.csv"
            csv_file.write_text("patient_id,value\np1,10\n", encoding="utf-8")

            bucket = FakeBucket()
            manifest_blob_name = get_manifest_blob_name()
            bucket.objects[manifest_blob_name] = {
                "data": _manifest_csv(
                    [
                        {
                            "relative_path": "workspace/patient_001/old.csv",
                            "blob_name": "workspace_sync/workspace/patient_001/old.csv",
                            "content_hash": "old-hash",
                            "size_bytes": "4",
                            "mtime_iso": "2026-05-17T00:00:00+0900",
                            "content_type": "text/csv; charset=utf-8",
                            "synced_at": "2026-05-17T00:00:00+0900",
                        }
                    ]
                ).encode("utf-8"),
                "content_type": "text/csv; charset=utf-8",
                "metadata": {},
            }
            bucket.objects["workspace_sync/workspace/patient_001/old.csv"] = {
                "data": b"old",
                "content_type": "text/csv; charset=utf-8",
                "metadata": {},
            }

            result = sync_workspace_once(root, bucket_getter=lambda: bucket)

        self.assertEqual(result.uploaded, 1)
        self.assertEqual(result.deleted, 1)
        self.assertEqual(result.manifest_rows, 1)
        self.assertIn("workspace_sync/workspace/patient_001/labs.csv", bucket.objects)
        self.assertNotIn("workspace_sync/workspace/patient_001/old.csv", bucket.objects)
        manifest = bucket.objects[manifest_blob_name]["data"].decode("utf-8")
        self.assertIn("workspace/patient_001/labs.csv", manifest)
        self.assertNotIn("old.csv", manifest)

    def test_sync_workspace_creates_conflict_copy_when_remote_hash_differs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = root / "workspace" / "patient_002"
            data_dir.mkdir(parents=True)
            csv_file = data_dir / "labs.csv"
            csv_file.write_text("patient_id,value\np2,20\n", encoding="utf-8")

            bucket = FakeBucket()
            manifest_blob_name = get_manifest_blob_name()
            bucket.objects[manifest_blob_name] = {
                "data": _manifest_csv(
                    [
                        {
                            "relative_path": "workspace/patient_002/labs.csv",
                            "blob_name": "workspace_sync/workspace/patient_002/labs.csv",
                            "content_hash": "old-hash",
                            "size_bytes": "8",
                            "mtime_iso": "2026-05-17T00:00:00+0900",
                            "content_type": "text/csv; charset=utf-8",
                            "synced_at": "2026-05-17T00:00:00+0900",
                        }
                    ]
                ).encode("utf-8"),
                "content_type": "text/csv; charset=utf-8",
                "metadata": {},
            }
            bucket.objects["workspace_sync/workspace/patient_002/labs.csv"] = {
                "data": b"remote-old",
                "content_type": "text/csv; charset=utf-8",
                "metadata": {"content_hash": "remote-different"},
            }

            result = sync_workspace_once(root, bucket_getter=lambda: bucket)

        self.assertEqual(result.conflicts, 1)
        file_records_blob = bucket.objects["workspace_sync/_files.csv"]["data"].decode("utf-8")
        self.assertIn("conflict_copy", file_records_blob)
        self.assertIn("_conflicts", file_records_blob)
        conflict_keys = [key for key in bucket.objects if "_conflicts" in key]
        self.assertTrue(conflict_keys)


if __name__ == "__main__":
    unittest.main()
