import logging
logger = logging.getLogger(__name__)
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
import json
import time
from pydantic import BaseModel

from app.models import AccountLoginRequest
from app.api_deps import _json, ACCOUNT_SESSION_TTL_SECONDS, ACCOUNT_SESSION_COOKIE, _load_account_sessions, _save_account_sessions, _is_authorized, GDRIVE_SCOPES, GDRIVE_TOKEN_BLOB, _error, _request_email, _request_client_host, _account_token, _create_account_session, _should_secure_cookie, _access_context_allowed, _auth_state, _load_users, _save_users
from app.security import account_login_id, verify_account_password, allow_account_id_fallback, allow_google_auth_fallback, owner_email, require_cloudflare_access
from app import passkeys
from app.gcs_helper import get_bucket
from app.request_utils import get_client_ip
from google_auth_oauthlib.flow import Flow

router = APIRouter()

class AccountRegisterRequest(BaseModel):
    account_id: str
    password: str

def verify_registered_user(login_id: str, password: str) -> bool:
    from app.security import _verify_hash
    try:
        users = _load_users()
        user_data = users.get(login_id)
        if user_data:
            hashed = user_data.get("password_hash")
            if hashed:
                return _verify_hash(password, hashed)
    except Exception as e:
        logger.error(f"Failed to verify registered user {login_id}: {e}")
    return False

@router.get('/api/session')
async def session(request: Request):
    state = _auth_state(request)
    access_context = state["access_context"]
    email = state["email"]
    return _json(
        {
            "cloudflare_access_required": require_cloudflare_access(),
            "account_id_fallback_allowed": allow_account_id_fallback(),
            "google_auth_fallback_allowed": allow_google_auth_fallback(),
            "account_login_id": account_login_id(),
            "client_ip": get_client_ip(request.headers, _request_client_host(request)),
            "passkey_registered": passkeys.has_registered_credential(email),
            "cloudflare_access": {
                "email": access_context.email,
                "has_jwt": access_context.has_jwt,
                "allowed": access_context.allowed,
            },
            "passkey_authenticated": state["passkey_ok"],
            "account_authenticated": state["account_id_ok"],
            "authorized": state["authorized"],
            "auth_method": state["auth_method"],
        }
    )


# Simple in-memory rate limiter for login
login_attempts = {}  # {ip: [timestamp1, timestamp2, ...]}

@router.post('/api/auth/account/login')
async def account_login(request: Request, payload: AccountLoginRequest):
    if not allow_account_id_fallback():
        return _json({"error": "계정 ID fallback이 꺼져 있습니다."}, status_code=403)

    client_ip = get_client_ip(request.headers, _request_client_host(request))
    now = time.time()
    # Clean up old attempts (older than 10 minutes)
    attempts = [t for t in login_attempts.get(client_ip, []) if now - t < 600]
    if len(attempts) >= 10:
        return _json(
            {"error": "너무 많은 로그인 시도가 있었습니다. 잠시 후 다시 시도해주세요."},
            status_code=429,
        )

    login_id = payload.account_id.strip().lower()
    password = payload.password

    try:
        login_success = False
        if verify_registered_user(login_id, password):
            login_success = True
        elif login_id == account_login_id() and verify_account_password(password):
            login_success = True
            
        if not login_success:
            attempts.append(now)
            login_attempts[client_ip] = attempts
            return _json(
                {"error": "계정 ID 또는 비밀번호가 올바르지 않습니다."}, status_code=401
            )
    except Exception:
        logger.exception("Login verification error")
        return _json({"error": "인증 처리 중 오류가 발생했습니다."}, status_code=500)

    # Success, clear attempts
    if client_ip in login_attempts:
        del login_attempts[client_ip]
    try:
        token = _create_account_session(login_id)
    except Exception:
        logger.exception("Failed to create session")
        return _json({"error": "세션 생성에 실패했습니다."}, status_code=500)

    response = _json(
        {"ok": True, "email": login_id, "expires_in": ACCOUNT_SESSION_TTL_SECONDS}
    )
    response.set_cookie(
        ACCOUNT_SESSION_COOKIE,
        token,
        max_age=ACCOUNT_SESSION_TTL_SECONDS,
        httponly=True,
        secure=_should_secure_cookie(request),
        samesite="lax",
    )
    return response

@router.post('/api/auth/account/register')
async def account_register(payload: AccountRegisterRequest):
    from app.config import allow_public_registration
    if not allow_public_registration():
        return _json({"error": "공개 회원가입이 비활성화되어 있습니다. 관리자에게 계정 생성을 요청하세요."}, status_code=403)

    login_id = payload.account_id.strip().lower()
    password = payload.password
    
    if not login_id or not password:
        return _json({"error": "이메일과 비밀번호를 입력해주세요."}, status_code=400)
        
    if "@" not in login_id:
        return _json({"error": "올바른 이메일 형식이 아닙니다."}, status_code=400)
        
    if len(password) < 6:
        return _json({"error": "비밀번호는 최소 6자리 이상이어야 합니다."}, status_code=400)
        
    try:
        users = _load_users()
        if login_id in users or login_id == account_login_id():
            return _json({"error": "이미 가입된 이메일입니다."}, status_code=400)
            
        from app.security import hash_password
        hashed = hash_password(password)
        users[login_id] = {
            "password_hash": hashed,
            "role": "viewer",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
        _save_users(users)
        return _json({"ok": True})
    except Exception as e:
        logger.exception("Registration failed")
        return _json({"error": f"회원가입 처리 중 오류가 발생했습니다: {str(e)}"}, status_code=500)

@router.post('/api/auth/passkey/register/options')
async def passkey_register_options(request: Request):
    email = _request_email(request)
    try:
        return _json(passkeys.registration_options(email))
    except Exception as exc:
        return _json({"error": str(exc)}, status_code=400)

@router.post('/api/auth/passkey/register/verify')
async def passkey_register_verify(request: Request):
    email = _request_email(request)
    payload = await request.json()
    try:
        result = passkeys.verify_registration(email, payload)
        return _json({"ok": True, **result})
    except Exception as exc:
        logger.exception("Passkey registration error")
        return _json({"error": str(exc)}, status_code=400)

@router.post('/api/auth/passkey/login/options')
async def passkey_login_options(request: Request):
    ok, message = _access_context_allowed(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    email = _request_email(request)
    try:
        return _json(passkeys.authentication_options(email))
    except ValueError as exc:
        if "등록된 passkey가 없습니다" in str(exc):
            return _json({"error": str(exc)}, status_code=404)
        logger.exception("Passkey login options ValueError")
        return _json({"error": str(exc)}, status_code=400)
    except Exception as exc:
        logger.exception("Passkey login options error")
        return _json({"error": str(exc)}, status_code=400)

@router.post('/api/auth/passkey/login/verify')
async def passkey_login_verify(request: Request):
    ok, message = _access_context_allowed(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    email = _request_email(request)
    payload = await request.json()
    try:
        result = passkeys.verify_authentication(email, payload)
    except Exception as exc:
        return _json({"error": str(exc)}, status_code=400)
    response = _json({"ok": True, "expires_in": result["expires_in"]})
    response.set_cookie(
        "jisong_passkey_session",
        result["token"],
        max_age=result["expires_in"],
        httponly=True,
        secure=_should_secure_cookie(request),
        samesite="lax",
    )
    return response

@router.post('/api/auth/logout')
async def auth_logout(request: Request):
    response = JSONResponse({"ok": True})
    # Remove passkey cookie
    response.delete_cookie("jisong_passkey_session")

    # Remove account session from store and cookie
    token = _account_token(request)
    if token:
        sessions = _load_account_sessions()
        if token in sessions:
            del sessions[token]
            _save_account_sessions(sessions)
    response.delete_cookie(ACCOUNT_SESSION_COOKIE)
    return response

@router.get('/api/auth/gdrive/url')
async def gdrive_auth_url(request: Request):
    try:
        ok, message = _is_authorized(request)
        if not ok:
            return _error(message, 401)
            
        from app.config import get_gdrive_oauth_config
        config = get_gdrive_oauth_config()
        
        if not config["client_id"] or not config["client_secret"]:
            return _error("GDRIVE_CLIENT_ID 및 GDRIVE_CLIENT_SECRET이 설정되지 않았습니다.")
            
        client_config = {
            "web": {
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=GDRIVE_SCOPES,
            redirect_uri=config["redirect_uri"]
        )
        
        auth_url, _ = flow.authorization_url(access_type='offline', include_granted_scopes='true', prompt='consent')
        return _json({"url": auth_url})
    except Exception as e:
        logger.exception("Failed to generate GDrive auth URL")
        return _error(f"인증 URL 생성 중 오류가 발생했습니다: {str(e)}", 500)

@router.get('/api/auth/gdrive/callback')
async def gdrive_auth_callback(request: Request):
    try:
        code = request.query_params.get("code")
        if not code:
            error_param = request.query_params.get("error")
            if error_param:
                return Response(f"<html><body><h3>Google 인증 거부됨</h3><p>{error_param}</p></body></html>", media_type="text/html")
            return _error("Authorization code not found", 400)
            
        from app.config import get_gdrive_oauth_config
        config = get_gdrive_oauth_config()
        
        client_config = {
            "web": {
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=GDRIVE_SCOPES,
            redirect_uri=config["redirect_uri"]
        )
        
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        # Save token to GCS
        token_data = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }
        bucket = get_bucket()
        blob = bucket.blob(GDRIVE_TOKEN_BLOB)
        blob.upload_from_string(json.dumps(token_data), content_type="application/json")
        
        return Response(
            "<html><head><meta charset='UTF-8'></head><body><h3>Google Drive 연결 성공!</h3><p>이 창을 닫고 앱을 새로고침 하세요.</p><script>setTimeout(() => window.close(), 3000)</script></body></html>",
            media_type="text/html"
        )
    except Exception as e:
        logger.exception("GDrive callback failed")
        return Response(f"<html><body><h3>오류 발생</h3><p>{str(e)}</p></body></html>", media_type="text/html")
