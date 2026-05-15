import os
import unittest
from unittest.mock import patch

from app.passkeys import CborReader, b64url_decode, b64url_encode
from app.security import allow_google_auth_fallback, get_access_context, owner_email, require_cloudflare_access


class SecurityTests(unittest.TestCase):
    def test_cloudflare_access_context_requires_email_and_jwt(self):
        headers = {
            "cf-access-authenticated-user-email": "Jsbang01357@Gmail.com",
            "cf-access-jwt-assertion": "token",
        }

        with patch.dict(os.environ, {}, clear=True):
            context = get_access_context(headers)

            self.assertEqual(context.email, "jsbang01357@gmail.com")
            self.assertTrue(context.has_jwt)
            self.assertTrue(context.allowed)

    def test_cloudflare_access_defaults_to_owner_email_only(self):
        headers = {
            "cf-access-authenticated-user-email": "other@example.com",
            "cf-access-jwt-assertion": "token",
        }

        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(owner_email(), "jsbang01357@gmail.com")
            self.assertFalse(get_access_context(headers).allowed)

    def test_cloudflare_access_allowed_email_list(self):
        headers = {
            "cf-access-authenticated-user-email": "other@example.com",
            "cf-access-jwt-assertion": "token",
        }

        with patch.dict(os.environ, {"CLOUDFLARE_ACCESS_ALLOWED_EMAILS": "me@example.com"}):
            self.assertFalse(get_access_context(headers).allowed)

    def test_require_cloudflare_access_default_on(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(require_cloudflare_access())
        with patch.dict(os.environ, {"REQUIRE_CLOUDFLARE_ACCESS": "false"}):
            self.assertFalse(require_cloudflare_access())

    def test_google_auth_fallback_default_on(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(allow_google_auth_fallback())
        with patch.dict(os.environ, {"ALLOW_GOOGLE_AUTH_FALLBACK": "false"}):
            self.assertFalse(allow_google_auth_fallback())

    def test_base64url_round_trip(self):
        payload = b"\x00hello?\xff"
        self.assertEqual(b64url_decode(b64url_encode(payload)), payload)

    def test_cbor_reader_reads_small_map(self):
        # {1: 2, "k": b"v"}
        decoded = CborReader(bytes.fromhex("a20102616b4176")).read()

        self.assertEqual(decoded, {1: 2, "k": b"v"})


if __name__ == "__main__":
    unittest.main()
