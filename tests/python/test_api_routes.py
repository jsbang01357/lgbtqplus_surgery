import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import api_server


class ApiRouteProtectionTests(unittest.TestCase):
    def test_files_endpoint_requires_authorization(self):
        with patch("api_server.start_folder_sync_service"), \
            patch("api_server.start_gdrive_sync_service"), \
            patch("api_server.stop_folder_sync_service"), \
            patch("app.api_deps._is_authorized", return_value=(False, "auth required")):
            with TestClient(api_server.app) as client:
                response = client.get("/api/files")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "auth required")

    def test_files_endpoint_returns_empty_download_url_when_signing_is_unavailable(self):
        dummy_file = type(
            "DummyFile",
            (),
            {
                "name": "report.pdf",
                "blob_name": "uploads/report.pdf",
                "size": 123,
                "updated": None,
                "content_type": "application/pdf",
            },
        )()

        with patch("api_server.start_folder_sync_service"), \
            patch("api_server.start_gdrive_sync_service"), \
            patch("api_server.stop_folder_sync_service"), \
            patch("app.api_deps._is_authorized", return_value=(True, "")), \
            patch("app.routers.files.list_uploaded_files", return_value=[dummy_file]), \
            patch("app.routers.files.create_file_download_url_safe", return_value=""):
            with TestClient(api_server.app) as client:
                response = client.get("/api/files")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "files": [
                    {
                        "name": "report.pdf",
                        "blob_name": "uploads/report.pdf",
                        "size": 123,
                        "updated": "",
                        "content_type": "application/pdf",
                        "download_url": "",
                    }
                ]
            },
        )


if __name__ == "__main__":
    unittest.main()
