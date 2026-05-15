import os
import unittest
from unittest.mock import patch

from api_server import ACCOUNT_SESSIONS, _auth_state, _create_account_session


class DummyRequest:
    def __init__(self, headers=None, cookies=None):
        self.headers = headers or {}
        self.cookies = cookies or {}


class ApiAuthTests(unittest.TestCase):
    def tearDown(self):
        ACCOUNT_SESSIONS.clear()

    def test_owner_google_access_is_authorized_without_passkey_when_fallback_enabled(self):
        request = DummyRequest(
            headers={
                "cf-access-authenticated-user-email": "jsbang01357@gmail.com",
                "cf-access-jwt-assertion": "token",
            }
        )

        with patch.dict(os.environ, {"ALLOW_GOOGLE_AUTH_FALLBACK": "true"}, clear=True):
            state = _auth_state(request)

        self.assertTrue(state["authorized"])
        self.assertEqual(state["auth_method"], "google")

    def test_non_owner_google_access_is_not_authorized(self):
        request = DummyRequest(
            headers={
                "cf-access-authenticated-user-email": "other@example.com",
                "cf-access-jwt-assertion": "token",
            }
        )

        with patch.dict(os.environ, {"ALLOW_GOOGLE_AUTH_FALLBACK": "true"}, clear=True):
            state = _auth_state(request)

        self.assertTrue(state["access_ok"])
        self.assertFalse(state["authorized"])

    def test_owner_account_id_session_authorizes_without_cloudflare_access(self):
        token = _create_account_session("jsbang01357@gmail.com")
        request = DummyRequest(cookies={"jisong_account_session": token})

        with patch.dict(os.environ, {}, clear=True):
            state = _auth_state(request)

        self.assertTrue(state["access_ok"])
        self.assertTrue(state["authorized"])
        self.assertEqual(state["auth_method"], "account")

    def test_cloudflare_access_can_still_be_required(self):
        request = DummyRequest()

        with patch.dict(os.environ, {"REQUIRE_CLOUDFLARE_ACCESS": "true"}, clear=True):
            state = _auth_state(request)

        self.assertFalse(state["access_ok"])
        self.assertFalse(state["authorized"])


if __name__ == "__main__":
    unittest.main()
