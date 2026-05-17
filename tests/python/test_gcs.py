import unittest
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


if __name__ == "__main__":
    unittest.main()
