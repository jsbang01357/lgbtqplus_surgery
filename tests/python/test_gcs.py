import unittest
import tempfile
import json
import os
from unittest.mock import patch

import app.gcs_helper as gcs_helper


class DummyBucket:
    def __init__(self, name):
        self.name = name


class DummyClient:
    def bucket(self, name):
        return DummyBucket(name)


class GcsHelperTests(unittest.TestCase):
    def test_get_bucket_uses_configured_bucket_name(self):
        with patch.object(gcs_helper, "get_gcs_client", return_value=DummyClient()), \
            patch.object(gcs_helper, "get_bucket_name", return_value="test-bucket"):
            bucket = gcs_helper.get_bucket()

        self.assertEqual(bucket.name, "test-bucket")

    def test_get_logs_blob_name_is_stable(self):
        self.assertEqual(gcs_helper.get_logs_blob_name(), "logs/access_log.json")

    def test_load_service_account_info_accepts_raw_json(self):
        info = gcs_helper._load_service_account_info('{"project_id":"demo","private_key":"line1\\\\nline2"}')

        self.assertEqual(info["project_id"], "demo")
        self.assertEqual(info["private_key"], "line1\nline2")

    def test_load_service_account_info_accepts_file_path(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump({"project_id": "demo-file", "private_key": "line1\\nline2"}, handle)
            path = handle.name

        try:
            info = gcs_helper._load_service_account_info(path)
        finally:
            import os
            os.unlink(path)

        self.assertEqual(info["project_id"], "demo-file")
        self.assertEqual(info["private_key"], "line1\nline2")

    def test_local_storage_bucket_round_trip(self):
        with tempfile.TemporaryDirectory() as root:
            gcs_helper._LOCAL_BUCKET_CACHE = {}
            with patch.dict(
                os.environ,
                {
                    "STORAGE_BACKEND": "local",
                    "LOCAL_STORAGE_ROOT": root,
                    "GCS_BUCKET_NAME": "local-test",
                },
            ):
                bucket = gcs_helper.get_bucket()
                blob = bucket.blob("surgery_ops/cases/case_1.json")
                blob.upload_from_string('{"ok": true}', content_type="application/json")

                self.assertTrue(blob.exists())
                self.assertEqual(blob.download_as_text(), '{"ok": true}')
                self.assertEqual(
                    [item.name for item in bucket.list_blobs(prefix="surgery_ops/cases/")],
                    ["surgery_ops/cases/case_1.json"],
                )

                blob.delete()
                self.assertFalse(blob.exists())


if __name__ == "__main__":
    unittest.main()
