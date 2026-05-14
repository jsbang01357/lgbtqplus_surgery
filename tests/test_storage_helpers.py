import unittest
from unittest.mock import patch

from app.storage import save_generated_file


class StorageHelperTests(unittest.TestCase):
    def test_save_generated_file_rejects_oversized_content_before_gcs(self):
        with patch("app.storage.MAX_UPLOAD_SIZE_BYTES", 3):
            with self.assertRaises(ValueError):
                save_generated_file("result.pdf", b"1234", "application/pdf")


if __name__ == "__main__":
    unittest.main()
