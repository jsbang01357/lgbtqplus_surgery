import unittest
from unittest.mock import patch

from app.storage import (
    GCSFileInfo,
    _strip_timestamp_suffix,
    create_file_download_url_safe,
    download_file_bytes,
    save_generated_file,
)


class StorageHelperTests(unittest.TestCase):
    def test_save_generated_file_rejects_oversized_content_before_gcs(self):
        with patch("app.storage.MAX_UPLOAD_SIZE_BYTES", 3):
            with self.assertRaises(ValueError):
                save_generated_file("result.pdf", b"1234", "application/pdf")

    def test_strip_timestamp_suffix_from_legacy_upload_names(self):
        self.assertEqual(
            _strip_timestamp_suffix("report_20260516_061530.pdf"),
            "report.pdf",
        )
        self.assertEqual(_strip_timestamp_suffix("report.pdf"), "report.pdf")

    def test_create_file_download_url_safe_returns_empty_on_signing_failure(self):
        file_info = GCSFileInfo(
            name="report.pdf",
            blob_name="uploads/report.pdf",
            size=10,
            updated=None,
            content_type="application/pdf",
        )

        with patch("app.storage.create_file_download_url", side_effect=RuntimeError("signing failed")):
            self.assertEqual(create_file_download_url_safe(file_info), "")

    def test_download_file_bytes_returns_content_type_and_original_name(self):
        class DummyBlob:
            content_type = "text/plain"
            metadata = {"original_name": "notes.txt"}

            def download_as_bytes(self):
                return b"hello"

        class DummyBucket:
            def blob(self, _name):
                return DummyBlob()

        with patch("app.storage.get_bucket", return_value=DummyBucket()):
            content, content_type, original_name = download_file_bytes("uploads/notes.txt")

        self.assertEqual(content, b"hello")
        self.assertEqual(content_type, "text/plain")
        self.assertEqual(original_name, "notes.txt")


if __name__ == "__main__":
    unittest.main()
