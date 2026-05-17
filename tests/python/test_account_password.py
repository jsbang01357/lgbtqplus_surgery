import asyncio
import json
import os
import unittest
from unittest.mock import patch

import api_server


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
            patch.object(api_server, "account_login_id", return_value="owner@example.com"), \
            patch.object(api_server, "verify_account_password", return_value=True), \
            patch.object(api_server, "owner_email", return_value="owner@example.com"), \
            patch.object(api_server, "_create_account_session", return_value="issued-token"), \
            patch.object(api_server, "_should_secure_cookie", return_value=False):
            response = asyncio.run(api_server.account_login(request))

        body = json.loads(response.body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["email"], "owner@example.com")
        self.assertEqual(body["expires_in"], api_server.ACCOUNT_SESSION_TTL_SECONDS)
        self.assertIn("jisong_account_session=issued-token", response.headers["set-cookie"])

    def test_account_login_rejects_wrong_password(self):
        request = DummyRequest(
            payload={"account_id": "owner@example.com", "password": "wrong"}
        )

        with patch.dict(os.environ, {"ALLOW_ACCOUNT_ID_FALLBACK": "true"}, clear=True), \
            patch.object(api_server, "account_login_id", return_value="owner@example.com"), \
            patch.object(api_server, "verify_account_password", return_value=False):
            response = asyncio.run(api_server.account_login(request))

        body = json.loads(response.body)
        self.assertEqual(response.status_code, 401)
        self.assertIn("비밀번호", body["error"])

    def test_password_update_saves_new_password(self):
        request = DummyRequest(payload={"new_password": "new-secret"})

        with patch.object(api_server, "_is_authorized", return_value=(True, "")), \
            patch("app.security.update_account_password") as mock_update:
            response = asyncio.run(api_server.settings_password_update(request))

        self.assertEqual(response.status_code, 200)
        mock_update.assert_called_once_with("new-secret")

    def test_password_update_rejects_short_password(self):
        request = DummyRequest(payload={"new_password": "123"})

        with patch.object(api_server, "_is_authorized", return_value=(True, "")), \
            patch("app.security.update_account_password") as mock_update:
            response = asyncio.run(api_server.settings_password_update(request))

        body = json.loads(response.body)
        self.assertEqual(response.status_code, 400)
        self.assertIn("4자리", body["error"])
        mock_update.assert_not_called()


if __name__ == "__main__":
    unittest.main()
