import app.routers.auth
import os
import unittest
from unittest.mock import patch


from app.api_deps import _auth_state, _create_account_session


class DummyRequest:
    def __init__(self, headers=None, cookies=None):
        self.headers = headers or {}
        self.cookies = cookies or {}


class ApiAuthTests(unittest.TestCase):
    def setUp(self):
        self.account_sessions = {}
        self._patchers = [
            patch("app.api_deps._load_account_sessions", side_effect=self._load_account_sessions),
            patch("app.api_deps._save_account_sessions", side_effect=self._save_account_sessions),
        ]
        for patcher in self._patchers:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self._patchers):
            patcher.stop()

    def _load_account_sessions(self):
        return dict(self.account_sessions)

    def _save_account_sessions(self, sessions):
        self.account_sessions = dict(sessions)

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

    def test_session_includes_passkey_registered_flag(self):
        request = DummyRequest()

        with patch("app.api_deps._auth_state", return_value={
            "email": "jsbang01357@gmail.com",
            "access_context": type("Ctx", (), {"email": "", "has_jwt": False, "allowed": False})(),
            "authorized": False,
            "auth_method": "",
            "passkey_ok": False,
            "account_id_ok": False,
            "google_fallback_ok": False,
        }), \
            patch("app.passkeys.has_registered_credential", return_value=True), \
            patch("app.security.account_login_id", return_value="jsbang01357@gmail.com"), \
            patch("app.request_utils.get_client_ip", return_value="127.0.0.1"):
            response = __import__("asyncio").run(app.routers.auth.session(request))

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'"passkey_registered":true', response.body)


if __name__ == "__main__":
    unittest.main()
