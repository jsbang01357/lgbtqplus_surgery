import unittest
from unittest.mock import patch

from app.storage import _strip_timestamp_suffix, save_generated_file


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


if __name__ == "__main__":
    unittest.main()
