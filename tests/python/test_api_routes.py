import unittest
import tempfile
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

    def test_file_upload_stores_uploaded_blob(self):
        class FakeBlob:
            def __init__(self, bucket, name):
                self.bucket = bucket
                self.name = name
                stored = bucket.objects.get(name, {})
                self.metadata = stored.get("metadata", {})
                self.content_type = stored.get("content_type", "")

            def exists(self):
                return self.name in self.bucket.objects

            def upload_from_string(self, data, content_type=None):
                self.bucket.objects[self.name] = {
                    "data": data,
                    "content_type": content_type,
                    "metadata": dict(self.metadata),
                }

        class FakeBucket:
            def __init__(self):
                self.objects = {}

            def blob(self, name):
                return FakeBlob(self, name)

        bucket = FakeBucket()

        with patch("api_server.start_folder_sync_service"), \
            patch("api_server.start_gdrive_sync_service"), \
            patch("api_server.stop_folder_sync_service"), \
            patch("app.api_deps._is_authorized", return_value=(True, "")), \
            patch("app.routers.files.get_bucket", return_value=bucket):
            with TestClient(api_server.app) as client:
                response = client.post(
                    "/api/files",
                    files={"file0": ("한글.txt", b"hello", "text/plain")},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["uploaded"][0]["name"], "한글.txt")
        self.assertIn("uploads/한글.txt", bucket.objects)
        self.assertEqual(bucket.objects["uploads/한글.txt"]["data"], b"hello")

    def test_file_download_uses_rfc5987_filename_for_unicode_names(self):
        with patch("api_server.start_folder_sync_service"), \
            patch("api_server.start_gdrive_sync_service"), \
            patch("api_server.stop_folder_sync_service"), \
            patch("app.api_deps._is_authorized", return_value=(True, "")), \
            patch(
                "app.routers.files.download_file_bytes",
                return_value=(b"hello", "text/plain; charset=utf-8", "한글 메모.txt"),
            ):
            with TestClient(api_server.app) as client:
                response = client.get(
                    "/api/files/download", params={"blob_name": "uploads/file.txt"}
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"hello")
        content_disposition = response.headers["content-disposition"]
        self.assertIn("filename=", content_disposition)
        self.assertIn("filename*=UTF-8''", content_disposition)
        self.assertIn("%ED%95%9C%EA%B8%80%20%EB%A9%94%EB%AA%A8.txt", content_disposition)

    def test_memo_zip_route_returns_zip_file(self):
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as handle:
            handle.write(b"zip-bytes")
            zip_path = handle.name

        with patch("api_server.start_folder_sync_service"), \
            patch("api_server.start_gdrive_sync_service"), \
            patch("api_server.stop_folder_sync_service"), \
            patch("app.api_deps._is_authorized", return_value=(True, "")), \
            patch("app.routers.memos.load_memo_list_cached", return_value=[{"file_name": "memo.txt"}]), \
            patch("app.routers.memos.create_zip_of_memos", return_value=zip_path):
            with TestClient(api_server.app) as client:
                response = client.get("/api/memos/zip")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"zip-bytes")
        self.assertEqual(response.headers["content-type"], "application/zip")

    def test_memo_download_uses_rfc5987_filename_for_unicode_titles(self):
        with patch("api_server.start_folder_sync_service"), \
            patch("api_server.start_gdrive_sync_service"), \
            patch("api_server.stop_folder_sync_service"), \
            patch("app.api_deps._is_authorized", return_value=(True, "")), \
            patch(
                "app.routers.memos.load_single_memo_content",
                return_value={"title": "진료 메모", "content": "body"},
            ):
            with TestClient(api_server.app) as client:
                response = client.get("/api/memos/memo.txt/download")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"body")
        content_disposition = response.headers["content-disposition"]
        self.assertIn("filename*=UTF-8''", content_disposition)
        self.assertIn("%EC%A7%84%EB%A3%8C%20%EB%A9%94%EB%AA%A8.txt", content_disposition)


if __name__ == "__main__":
    unittest.main()
