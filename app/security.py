import os
import logging
import hashlib
import secrets
import base64
from dataclasses import dataclass
from app.core_utils import ttl_cache

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


def _verify_cloudflare_jwt(jwt_token: str) -> dict | None:
    """Cloudflare Access JWT의 서명, 만료 시간, Issuer를 암호학적으로 검증합니다."""
    team_domain = os.getenv("CLOUDFLARE_ACCESS_TEAM_DOMAIN", "").strip()
    if not team_domain:
        logger.warning("CLOUDFLARE_ACCESS_TEAM_DOMAIN 환경 변수가 비어 있어 JWT 서명 검증을 건너뜁니다.")
        return None
        
    try:
        import jwt
    except ImportError:
        logger.warning("PyJWT 모듈이 설치되어 있지 않아 Cloudflare JWT 서명 검증을 건너뜁니다.")
        return None

    if not team_domain.startswith("http"):
        team_domain = f"https://{team_domain}"
        
    certs_url = f"{team_domain}/cdn-cgi/access/certs"
    aud = os.getenv("CLOUDFLARE_ACCESS_AUD", "").strip()
    
    try:
        jwks_client = jwt.PyJWKClient(certs_url)
        signing_key = jwks_client.get_signing_key_from_jwt(jwt_token)
        data = jwt.decode(
            jwt_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=aud if aud else None,
            issuer=team_domain,
            options={"verify_aud": bool(aud)}
        )
        return data
    except Exception as exc:
        logger.error(f"Cloudflare JWT 검증 실패: {exc}")
        return None


def get_access_context(headers) -> AccessContext:
    email = headers.get(CF_ACCESS_EMAIL_HEADER, "").strip().lower()
    jwt_token = headers.get(CF_ACCESS_JWT_HEADER, "").strip()
    has_jwt = bool(jwt_token)
    
    allowed = bool(email and has_jwt)
    
    if require_cloudflare_access() and has_jwt:
        payload = _verify_cloudflare_jwt(jwt_token)
        if not payload or payload.get("email", "").strip().lower() != email:
            logger.warning(f"인증 오류: Cloudflare JWT 검증 실패 또는 이메일 불일치 (Email: {email})")
            allowed = False
            
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


def hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256 기반으로 비밀번호를 단방향 안전 해싱합니다."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    salt_b64 = base64.b64encode(salt).decode("ascii")
    key_b64 = base64.b64encode(key).decode("ascii")
    return f"pbkdf2$sha256$100000${salt_b64}${key_b64}"


def _verify_hash(password: str, hashed: str) -> bool:
    """해시된 비밀번호와 입력된 비밀번호를 비교합니다."""
    if not hashed.startswith("pbkdf2$sha256$"):
        return False
    try:
        parts = hashed.split("$")
        if len(parts) != 5:
            return False
        _, _, iterations_str, salt_b64, key_b64 = parts
        iterations = int(iterations_str)
        salt = base64.b64decode(salt_b64)
        key = base64.b64decode(key_b64)
        new_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return secrets.compare_digest(key, new_key)
    except Exception:
        return False


@ttl_cache(seconds=60)
def account_login_password() -> str:
    """현재 저장소 백엔드에서 해싱된 계정 비밀번호 정보를 읽어 캐싱합니다."""
    from app.gcs_helper import get_bucket
    try:
        bucket = get_bucket()
        blob = bucket.blob("auth/account_password.txt")
        if blob.exists():
            return blob.download_as_text(encoding="utf-8").strip()
    except Exception:
        logger.exception("계정 비밀번호를 저장소에서 읽지 못했습니다.")
    return ""


def verify_account_password(password: str) -> bool:
    """계정 비밀번호의 유효성을 검증하며, 하위 호환 평문 발견 시 자동 해싱 마이그레이션(Self-Healing)합니다."""
    from app.config import get_admin_password
    if password and password == get_admin_password():
        return True

    stored = account_login_password()
    if not stored:
        return False
    
    # 1. 해싱된 비밀번호 포맷인 경우 검증
    if stored.startswith("pbkdf2$sha256$"):
        return _verify_hash(password, stored)
        
    # 2. 하위 호환 평문인 경우 (Self-Healing 마이그레이션 진행)
    if password == stored:
        try:
            logger.info("평문 비밀번호를 감지하여 신규 PBKDF2 해싱 포맷으로 자동 업그레이드합니다.")
            update_account_password(password)
        except Exception:
            logger.exception("비밀번호 해싱 자동 마이그레이션 중 오류가 발생했습니다.")
        return True
    
    return False


def update_account_password(new_password: str):
    """비밀번호를 PBKDF2로 안전하게 해싱하여 현재 저장소 백엔드에 저장하고, 캐시를 갱신합니다."""
    from app.gcs_helper import get_bucket
    hashed = hash_password(new_password)
    bucket = get_bucket()
    blob = bucket.blob("auth/account_password.txt")
    blob.upload_from_string(hashed, content_type="text/plain; charset=utf-8")
    account_login_password.clear()
