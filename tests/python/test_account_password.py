import app.routers.auth
import app.routers.settings
import asyncio
import json
import os
import unittest
from unittest.mock import patch

import api_server
import app.models


class DummyRequest:
    def __init__(self, payload=None, headers=None, cookies=None):
        self._payload = payload or {}
        self.headers = headers or {}
        self.cookies = cookies or {}

    async def json(self):
        return self._payload


class AccountPasswordTests(unittest.TestCase):
    def test_account_login_issues_session_cookie(self):
        request = DummyRequest(
            payload={"account_id": "owner@example.com", "password": "secret"}
        )

        with patch.dict(os.environ, {"ALLOW_ACCOUNT_ID_FALLBACK": "true"}, clear=True), \
            patch("app.routers.auth.account_login_id", return_value="owner@example.com"), \
            patch("app.routers.auth.verify_account_password", return_value=True), \
            patch("app.routers.auth.owner_email", return_value="owner@example.com"), \
            patch("app.routers.auth._create_account_session", return_value="issued-token"), \
            patch("app.routers.auth._should_secure_cookie", return_value=False):
            response = asyncio.run(app.routers.auth.account_login(request, app.models.AccountLoginRequest(**request._payload)))

        body = json.loads(response.body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["email"], "owner@example.com")
        self.assertEqual(body["expires_in"], app.routers.auth.ACCOUNT_SESSION_TTL_SECONDS)
        self.assertIn("jisong_account_session=issued-token", response.headers["set-cookie"])

    def test_account_login_rejects_wrong_password(self):
        request = DummyRequest(
            payload={"account_id": "owner@example.com", "password": "wrong"}
        )

        with patch.dict(os.environ, {"ALLOW_ACCOUNT_ID_FALLBACK": "true"}, clear=True), \
            patch("app.routers.auth.account_login_id", return_value="owner@example.com"), \
            patch("app.routers.auth.verify_account_password", return_value=False):
            response = asyncio.run(app.routers.auth.account_login(request, app.models.AccountLoginRequest(**request._payload)))

        body = json.loads(response.body)
        self.assertEqual(response.status_code, 401)
        self.assertIn("비밀번호", body["error"])

    def test_password_update_saves_new_password(self):
        request = DummyRequest(payload={"new_password": "new-secret"})

        with patch("app.routers.settings.update_account_password") as mock_update:
            response = asyncio.run(app.routers.settings.settings_password_update(request, app.models.PasswordUpdateRequest(**request._payload), True))

        self.assertEqual(response.status_code, 200)
        mock_update.assert_called_once_with("new-secret")

    def test_password_update_rejects_short_password(self):
        request = DummyRequest(payload={"new_password": "123"})

        with patch("app.routers.settings.update_account_password") as mock_update:
            response = asyncio.run(app.routers.settings.settings_password_update(request, app.models.PasswordUpdateRequest(**request._payload), True))

        body = json.loads(response.body)
        self.assertEqual(response.status_code, 400)
        self.assertIn("4자리", body["error"])
        mock_update.assert_not_called()


if __name__ == "__main__":
    unittest.main()
