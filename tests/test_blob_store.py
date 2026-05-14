import tempfile
import unittest
from unittest.mock import patch

from app.blob_store import LocalMirrorBucket


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


if __name__ == "__main__":
    unittest.main()
