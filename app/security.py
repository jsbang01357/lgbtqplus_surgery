import os
from dataclasses import dataclass


CF_ACCESS_EMAIL_HEADER = "cf-access-authenticated-user-email"
CF_ACCESS_JWT_HEADER = "cf-access-jwt-assertion"
DEFAULT_OWNER_EMAIL = "jsbang01357@gmail.com"


@dataclass(frozen=True)
class AccessContext:
    email: str
    has_jwt: bool
    allowed: bool


def _allowed_emails() -> set[str]:
    raw = os.getenv("CLOUDFLARE_ACCESS_ALLOWED_EMAILS", "")
    emails = {item.strip().lower() for item in raw.split(",") if item.strip()}
    return emails or {owner_email()}


def owner_email() -> str:
    return os.getenv("JISONG_OWNER_EMAIL", DEFAULT_OWNER_EMAIL).strip().lower()


def get_access_context(headers) -> AccessContext:
    email = headers.get(CF_ACCESS_EMAIL_HEADER, "").strip().lower()
    has_jwt = bool(headers.get(CF_ACCESS_JWT_HEADER, "").strip())
    allowed = bool(email and has_jwt)
    allowed_emails = _allowed_emails()
    if allowed_emails:
        allowed = allowed and email in allowed_emails
    return AccessContext(email=email, has_jwt=has_jwt, allowed=allowed)


def require_cloudflare_access() -> bool:
    value = os.getenv("REQUIRE_CLOUDFLARE_ACCESS", "true")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def allow_google_auth_fallback() -> bool:
    value = os.getenv("ALLOW_GOOGLE_AUTH_FALLBACK", "true")
    return value.strip().lower() in {"1", "true", "yes", "on"}
