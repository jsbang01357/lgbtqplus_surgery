import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from app.blob_store import LocalMirrorBucket


class FakeRemoteBlob:
    def __init__(self, name: str, bucket: "FakeRemoteBucket"):
        self.name = name
        self.bucket = bucket
        self.content_type = None
        self.metadata = {}
        self.updated = None

    def exists(self):
        return self.name in self.bucket.items

    def upload_from_string(self, data, content_type=None, **kwargs):
        payload = data.encode("utf-8") if isinstance(data, str) else bytes(data)
        self.bucket.items[self.name] = {
            "data": payload,
            "content_type": content_type,
            "metadata": dict(self.metadata or {}),
            "updated": datetime.now(timezone.utc),
        }
        self._load()

    def download_as_bytes(self):
        return self.bucket.items[self.name]["data"]

    def delete(self):
        self.bucket.items.pop(self.name, None)

    def _load(self):
        item = self.bucket.items.get(self.name)
        if not item:
            return
        self.content_type = item.get("content_type")
        self.metadata = item.get("metadata") or {}
        self.updated = item.get("updated")


class FakeRemoteBucket:
    def __init__(self):
        self.items = {}

    def blob(self, name: str):
        blob = FakeRemoteBlob(name, self)
        blob._load()
        return blob

    def list_blobs(self, prefix: str = ""):
        return [self.blob(name) for name in sorted(self.items) if name.startswith(prefix)]


class LocalBlobStoreTests(unittest.TestCase):
    def test_local_bucket_round_trip_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict("os.environ", {"LOCAL_STORAGE_ROOT": tmpdir}, clear=False):
                bucket = LocalMirrorBucket()
                blob = bucket.blob("uploads/example.txt")
                blob.metadata = {"title": "예시"}
                blob.upload_from_string("hello", content_type="text/plain")

                loaded = bucket.blob("uploads/example.txt")
                self.assertTrue(loaded.exists())
                self.assertEqual(loaded.download_as_text(), "hello")
                self.assertEqual(loaded.content_type, "text/plain")
                self.assertEqual(loaded.metadata["title"], "예시")

                names = [item.name for item in bucket.list_blobs(prefix="uploads/")]
                self.assertEqual(names, ["uploads/example.txt"])

    def test_rejects_unsafe_blob_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict("os.environ", {"LOCAL_STORAGE_ROOT": tmpdir}, clear=False):
                bucket = LocalMirrorBucket()
                with self.assertRaises(ValueError):
                    bucket.blob("../escape.txt").exists()

    def test_local_mirror_pushes_local_only_file_to_remote(self):
        remote = FakeRemoteBucket()
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {
                "LOCAL_STORAGE_ROOT": tmpdir,
                "STORAGE_BACKEND": "local_mirror",
                "LOCAL_STORAGE_SYNC_TO_GCS": "true",
                "LOCAL_STORAGE_PULL_FROM_GCS": "false",
            }
            with patch.dict("os.environ", env, clear=False):
                bucket = LocalMirrorBucket(remote_bucket=remote)
                blob = bucket.blob("uploads/local.txt")
                blob.upload_from_string("local", content_type="text/plain")

                self.assertIn("uploads/local.txt", remote.items)
                self.assertEqual(remote.items["uploads/local.txt"]["data"], b"local")

    def test_local_mirror_pulls_remote_file_to_local(self):
        remote = FakeRemoteBucket()
        remote_blob = remote.blob("memos/remote.txt")
        remote_blob.metadata = {"title": "remote"}
        remote_blob.upload_from_string("remote", content_type="text/plain")

        with tempfile.TemporaryDirectory() as tmpdir:
            env = {
                "LOCAL_STORAGE_ROOT": tmpdir,
                "STORAGE_BACKEND": "local_mirror",
                "LOCAL_STORAGE_SYNC_TO_GCS": "false",
                "LOCAL_STORAGE_PULL_FROM_GCS": "true",
            }
            with patch.dict("os.environ", env, clear=False):
                bucket = LocalMirrorBucket(remote_bucket=remote)
                names = [item.name for item in bucket.list_blobs(prefix="memos/")]

                self.assertEqual(names, ["memos/remote.txt"])
                self.assertEqual(
                    bucket.blob("memos/remote.txt").download_as_text(), "remote"
                )

    def test_exists_pulls_single_remote_blob_to_local(self):
        remote = FakeRemoteBucket()
        remote.blob("logs/gemini_usage.json").upload_from_string(
            "[]", content_type="application/json"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            env = {
                "LOCAL_STORAGE_ROOT": tmpdir,
                "STORAGE_BACKEND": "local_mirror",
                "LOCAL_STORAGE_SYNC_TO_GCS": "false",
                "LOCAL_STORAGE_PULL_FROM_GCS": "true",
            }
            with patch.dict("os.environ", env, clear=False):
                bucket = LocalMirrorBucket(remote_bucket=remote)
                blob = bucket.blob("logs/gemini_usage.json")

                self.assertTrue(blob.exists())
                self.assertEqual(blob.download_as_text(), "[]")


if __name__ == "__main__":
    unittest.main()
