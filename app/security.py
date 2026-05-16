import os
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

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
    value = os.getenv("REQUIRE_CLOUDFLARE_ACCESS", "false")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def allow_google_auth_fallback() -> bool:
    value = os.getenv("ALLOW_GOOGLE_AUTH_FALLBACK", "true")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def allow_account_id_fallback() -> bool:
    value = os.getenv("ALLOW_ACCOUNT_ID_FALLBACK", "true")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def account_login_id() -> str:
    return os.getenv("JISONG_ACCOUNT_LOGIN_ID", owner_email()).strip().lower()


def account_login_password() -> str:
    from app.gcs_helper import get_bucket
    try:
        bucket = get_bucket()
        blob = bucket.blob("auth/account_password.txt")
        if blob.exists():
            return blob.download_as_text(encoding="utf-8").strip()
    except Exception:
        logger.exception("계정 비밀번호를 GCS에서 읽지 못했습니다.")
    return ""

def update_account_password(new_password: str):
    from app.gcs_helper import get_bucket
    bucket = get_bucket()
    blob = bucket.blob("auth/account_password.txt")
    blob.upload_from_string(new_password, content_type="text/plain")
