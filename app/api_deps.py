import mimetypes
import io
import re
import secrets
import logging
import threading
import time
from pathlib import Path
from urllib.parse import quote

from fastapi import Request, HTTPException, status

import os
from fastapi.responses import JSONResponse, StreamingResponse


from app import passkeys
from app.security import (
    allow_account_id_fallback,
    allow_google_auth_fallback,
    get_access_context,
    owner_email,
    require_cloudflare_access,
)
from app.gcs_helper import get_bucket
import json



logger = logging.getLogger(__name__)












# Suppress common warnings
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)

mimetypes.init()

# Allow HTTP for OAuth2 during local development
if os.getenv("GDRIVE_REDIRECT_URI", "").startswith("http://localhost"):
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

GDRIVE_TOKEN_BLOB = "auth/gdrive_token.json"
GDRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]

FRONTEND_DIR = (Path(__file__).resolve().parent.parent / "frontend").resolve()
MENU_JSON_PATH = Path(__file__).resolve().parent / "data" / "menu_list.json"
INCLUDE_RE = re.compile(r"<!--\s*include:(?P<path>[^ ]+)\s*-->")
ACCOUNT_SESSION_COOKIE = "jisong_account_session"
ACCOUNT_SESSION_TTL_SECONDS = 60 * 60 * 24 * 30
ACCOUNT_SESSIONS_BLOB = "auth/account_sessions.json"

_SESSIONS_CACHE = None
_SESSIONS_CACHE_EXPIRY = 0
_SESSIONS_LOCK = threading.Lock()

def _load_account_sessions() -> dict[str, str]:
    global _SESSIONS_CACHE, _SESSIONS_CACHE_EXPIRY
    if _SESSIONS_CACHE is not None and time.time() < _SESSIONS_CACHE_EXPIRY:
        return _SESSIONS_CACHE
        
    with _SESSIONS_LOCK:
        if _SESSIONS_CACHE is not None and time.time() < _SESSIONS_CACHE_EXPIRY:
            return _SESSIONS_CACHE
        try:
            bucket = get_bucket()
            blob = bucket.blob(ACCOUNT_SESSIONS_BLOB)
            if blob.exists():
                _SESSIONS_CACHE = json.loads(blob.download_as_text(encoding="utf-8"))
            else:
                _SESSIONS_CACHE = {}
        except Exception:
            _SESSIONS_CACHE = {} if _SESSIONS_CACHE is None else _SESSIONS_CACHE
            
        _SESSIONS_CACHE_EXPIRY = time.time() + 60
        return _SESSIONS_CACHE


def _save_account_sessions(sessions: dict[str, str]):
    try:
        bucket = get_bucket()
        blob = bucket.blob(ACCOUNT_SESSIONS_BLOB)
        blob.upload_from_string(json.dumps(sessions), content_type="application/json")
    except Exception:
        pass


def _cleanup_expired_sessions():
    try:
        global _SESSIONS_CACHE
        sessions = _load_account_sessions()
        now = time.time()
        
        expired_tokens = []
        for token, data in sessions.items():
            if isinstance(data, dict) and data.get("expires_at", 0) < now:
                expired_tokens.append(token)
                
        if expired_tokens:
            for token in expired_tokens:
                del sessions[token]
            _save_account_sessions(sessions)
            _SESSIONS_CACHE = sessions
            # logger.info(f"Cleaned up {len(expired_tokens)} expired sessions.")
    except Exception:
        pass




def get_current_user(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)
    return True

def get_current_user_no_exc(request: Request):
    ok, _ = _is_authorized(request)
    return ok

def _json(data, status_code=200):
    return JSONResponse(data, status_code=status_code)


def _error(message, status_code=400):
    return JSONResponse({"error": message}, status_code=status_code)


def _render_frontend_html() -> str:
    template = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")

    def replace_include(match: re.Match) -> str:
        relative_path = match.group("path").strip()
        include_path = (FRONTEND_DIR / relative_path).resolve()
        if FRONTEND_DIR not in include_path.parents:
            return ""
        if not include_path.exists() or include_path.suffix != ".html":
            return ""
        return include_path.read_text(encoding="utf-8")

    return INCLUDE_RE.sub(replace_include, template)


def _request_email(request: Request) -> str:
    return get_access_context(request.headers).email or owner_email()


def _request_client_host(request: Request) -> str | None:
    client = getattr(request, "client", None)
    return getattr(client, "host", None)


def _passkey_token(request: Request) -> str:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header.split(" ", 1)[1].strip()
    return request.cookies.get("jisong_passkey_session", "")


def _account_token(request: Request) -> str:
    return request.cookies.get(ACCOUNT_SESSION_COOKIE, "")


def _verify_account_session(request: Request, email: str) -> bool:
    token = _account_token(request)
    if not token:
        return False
    sessions = _load_account_sessions()
    session_data = sessions.get(token)
    if not session_data:
        return False
    
    # Handle legacy string format {"token": "email"}
    if isinstance(session_data, str):
        return session_data == email
        
    # Handle new dict format {"token": {"email": "...", "expires_at": ...}}
    if isinstance(session_data, dict):
        if session_data.get("expires_at", 0) < time.time():
            return False
        return session_data.get("email") == email
        
    return False


def _create_account_session(email: str) -> str:
    global _SESSIONS_CACHE
    token = secrets.token_urlsafe(32)
    sessions = _load_account_sessions()
    
    sessions[token] = {
        "email": email,
        "expires_at": time.time() + ACCOUNT_SESSION_TTL_SECONDS
    }
    
    _save_account_sessions(sessions)
    _SESSIONS_CACHE = sessions
    return token


def _should_secure_cookie(request: Request) -> bool:
    forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
    return request.url.scheme == "https" or forwarded_proto == "https"


def _file_response_bytes(content: bytes, filename: str, media_type: str):
    safe_name = filename.replace("\\", "_").replace("/", "_").replace('"', "'")
    ascii_name = safe_name.encode("ascii", "ignore").decode("ascii").strip()
    if not ascii_name:
        ascii_name = "download"
    encoded_name = quote(safe_name)
    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{encoded_name}'
            )
        },
    )


def _access_context_allowed(request: Request) -> tuple[bool, str]:
    access_context = get_access_context(request.headers)
    if require_cloudflare_access() and not access_context.allowed:
        return False, "Cloudflare Access 인증이 필요합니다."
    return True, ""


def _auth_state(request: Request) -> dict:
    access_context = get_access_context(request.headers)
    email = _request_email(request)
    passkey_ok = passkeys.verify_session(_passkey_token(request), email=email)
    account_id_ok = allow_account_id_fallback() and _verify_account_session(
        request, email
    )
    access_ok = access_context.allowed or not require_cloudflare_access()
    google_fallback_ok = allow_google_auth_fallback() and access_context.allowed
    authorized = access_ok and (passkey_ok or account_id_ok or google_fallback_ok)
    auth_method = ""
    if authorized:
        if passkey_ok:
            auth_method = "passkey"
        elif account_id_ok:
            auth_method = "account"
        else:
            auth_method = "google"
    return {
        "email": email,
        "access_context": access_context,
        "access_ok": access_ok,
        "passkey_ok": passkey_ok,
        "account_id_ok": account_id_ok,
        "google_fallback_ok": google_fallback_ok,
        "authorized": authorized,
        "auth_method": auth_method,
    }


def _is_authorized(request: Request) -> tuple[bool, str]:
    state = _auth_state(request)
    if not state["access_ok"]:
        return False, "Cloudflare Access 인증이 필요합니다."
    if not state["authorized"]:
        return False, "패스키 또는 계정 ID 인증이 필요합니다."
    return True, ""

