import unittest
import tempfile
import json
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


if __name__ == "__main__":
    unittest.main()
