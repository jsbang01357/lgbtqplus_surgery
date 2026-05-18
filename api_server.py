import mimetypes
import io
import re
import secrets
import logging
from dataclasses import asdict
from contextlib import asynccontextmanager
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
import os
from starlette.responses import FileResponse, JSONResponse, Response, StreamingResponse
from starlette.background import BackgroundTask
from starlette.routing import Route

from app import passkeys
from app.security import (
    account_login_id,
    verify_account_password,
    allow_account_id_fallback,
    allow_google_auth_fallback,
    get_access_context,
    owner_email,
    require_cloudflare_access,
)
from app.storage import (
    create_zip_of_files,
    create_file_download_url,
    delete_uploaded_file,
    guess_content_type,
    list_uploaded_files_cached,
    list_uploaded_files,
    normalize_blob_name,
    MAX_UPLOAD_SIZE_BYTES,
    UPLOAD_PREFIX,
)
from app.memo import (
    create_zip_of_memos,
    delete_memo_txt,
    load_memo_list_cached,
    load_single_memo_content,
    save_memo_txt,
)
from app.ai import (
    GEMINI_MODEL,
    format_krw_cost,
    USD_TO_KRW_RATE,
    _get_gemini_api_key,
    _get_model_name,
    _load_gemini_usage_logs,
    _get_usage_limit_status,
    _parse_usage_time,
    _postprocess_ai_result,
    _record_gemini_usage,
    _run_gemini_analysis,
    _sum_usage_costs,
)
from app.folder_sync import get_folder_sync_service, start_folder_sync_service, stop_folder_sync_service
from app.gcs_helper import get_bucket
from app.core_utils import get_now
from app.request_utils import get_client_ip
from app.md_pdf import markdown_to_pdf_bytes
from app.access_logger import get_access_logs, clear_access_logs, log_access_request
from app.text_cleaner import (
    _clean_ai_mode,
    _apply_basic_cleaning_options,
    _convert_markdown_to_plain_text,
    _convert_markdown_to_word_text,
)
from app.settlement import calculate_settlement
from app.v6_bridge import ParserBridgeError, parser_bridge_available, run_v6_parse
import json

logger = logging.getLogger(__name__)

FRONTEND_DIR = (Path(__file__).resolve().parent / "frontend").resolve()
MENU_JSON_PATH = Path(__file__).resolve().parent / "data" / "menu_list.json"
INCLUDE_RE = re.compile(r"<!--\s*include:(?P<path>[^ ]+)\s*-->")
ACCOUNT_SESSION_COOKIE = "jisong_account_session"
ACCOUNT_SESSION_TTL_SECONDS = 60 * 60 * 24 * 30
ACCOUNT_SESSIONS_BLOB = "auth/account_sessions.json"

import threading
import time

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


def _json(data, status_code=200):
    return JSONResponse(data, status_code=status_code)


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
    safe_name = filename.replace("\\", "_").replace('"', "'")
    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
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


async def health(_request: Request):
    return _json({"ok": True, "service": "jisong-cloud-api"})


async def session(request: Request):
    state = _auth_state(request)
    access_context = state["access_context"]
    return _json(
        {
            "cloudflare_access_required": require_cloudflare_access(),
            "account_id_fallback_allowed": allow_account_id_fallback(),
            "google_auth_fallback_allowed": allow_google_auth_fallback(),
            "account_login_id": account_login_id(),
            "client_ip": get_client_ip(request.headers, _request_client_host(request)),
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


async def account_login(request: Request):
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

    try:
        payload = await request.json()
    except Exception:
        return _json({"error": "잘못된 요청 형식입니다."}, status_code=400)

    login_id = (
        str(payload.get("account_id") or payload.get("email") or "").strip().lower()
    )
    password = str(payload.get("password") or "")

    try:
        if login_id != account_login_id() or not verify_account_password(password):
            attempts.append(now)
            login_attempts[client_ip] = attempts
            return _json(
                {"error": "계정 ID 또는 비밀번호가 올바르지 않습니다."}, status_code=401
            )
    except Exception as exc:
        logger.exception("Login verification error")
        return _json({"error": "인증 처리 중 오류가 발생했습니다."}, status_code=500)

    # Success, clear attempts
    if client_ip in login_attempts:
        del login_attempts[client_ip]
    email = owner_email()
    try:
        token = _create_account_session(email)
    except Exception as exc:
        logger.exception("Failed to create session")
        return _json({"error": "세션 생성에 실패했습니다."}, status_code=500)

    response = _json(
        {"ok": True, "email": email, "expires_in": ACCOUNT_SESSION_TTL_SECONDS}
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


async def usage_summary(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        return _json({"error": message}, status_code=401)

    try:
        multiplier = float(request.query_params.get("multiplier", 1.0))
        exchange_rate = float(
            request.query_params.get("exchange_rate", USD_TO_KRW_RATE)
        )
    except ValueError:
        multiplier = 1.0
        exchange_rate = USD_TO_KRW_RATE

    try:
        logs = _load_gemini_usage_logs()
        today_krw, month_krw, today_usd, month_usd = _sum_usage_costs(logs)

        base_multiplier = 10.0 * multiplier
        today_adjusted = today_usd * exchange_rate * base_multiplier
        month_adjusted = month_usd * exchange_rate * base_multiplier

        return _json(
            {
                "model": GEMINI_MODEL,
                "today_cost": today_adjusted,
                "month_cost": month_adjusted,
                "today_cost_usd": today_usd,
                "month_cost_usd": month_usd,
                "today_cost_label": format_krw_cost(today_adjusted),
                "month_cost_label": format_krw_cost(month_adjusted),
                "request_count": len(logs),
            }
        )
    except Exception as exc:
        return _json({"error": str(exc)}, status_code=500)


async def settings_password_update(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    payload = await request.json()
    new_password = payload.get("new_password", "").strip()
    if len(new_password) < 4:
        return _json({"error": "비밀번호는 4자리 이상이어야 합니다."}, status_code=400)

    from app.security import update_account_password

    try:
        update_account_password(new_password)
        return _json({"ok": True})
    except Exception as exc:
        return _json({"error": f"비밀번호 변경 실패: {exc}"}, status_code=500)


async def settings_access_logs(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    try:
        logs = get_access_logs()[:50]
    except Exception as exc:
        return _json({"error": str(exc)}, status_code=500)
    ip_counts: dict[str, int] = {}
    for entry in logs:
        ip = str(entry.get("ip") or "Unknown")
        ip_counts[ip] = ip_counts.get(ip, 0) + 1
    top_ips = [
        {"ip": ip, "count": count}
        for ip, count in sorted(
            ip_counts.items(), key=lambda item: item[1], reverse=True
        )[:5]
    ]
    return _json(
        {
            "total": len(logs),
            "unique_ips": len(ip_counts),
            "latest": logs[0] if logs else {},
            "top_ips": top_ips,
            "logs": logs[:12],
        }
    )


async def settings_access_logs_clear(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    try:
        clear_access_logs()
        return _json({"ok": True})
    except Exception as exc:
        return _json({"error": str(exc)}, status_code=500)


async def tool_text_cleaner(request: Request):
    # 도구는 비인증으로 열려있으되 민감기능만 제한할 수 있음.
    # 여기서는 전체 허용하되 필요시 _is_authorized 체크 추가 가능
    payload = await request.json()
    text = (payload.get("text") or "").strip()
    if not text:
        return _json({"error": "텍스트를 입력하세요."}, status_code=400)

    mode = payload.get("mode", "basic")
    options = payload.get("options", {})

    cleaned = text
    if mode == "basic":
        if options.get("ai_mode"):
            api_key = _get_gemini_api_key()
            if api_key:
                try:
                    from google import genai

                    client = genai.Client(api_key=api_key)
                    clean_prompt = (
                        "너는 텍스트를 정리하는 인공지능 비서야.\n"
                        "입력받은 텍스트의 내용을 절대 수정하거나 요약하지 말고, 다음 규칙에 따라 형식만 깔끔하게 다듬어줘:\n"
                        "1. 불필요한 줄바꿈 제거 및 문단 정렬\n"
                        "2. 깨진 특수문자나 인코딩 오류 복구 (가능한 경우)\n"
                        "3. 마크다운 형식을 유지하거나 적절히 적용하여 가독성 향상\n"
                        "4. 불필요한 공백 제거\n"
                        "정리된 텍스트만 출력해줘.\n\n"
                        f"텍스트:\n{text}"
                    )
                    response = client.models.generate_content(
                        model=_get_model_name(), contents=clean_prompt
                    )
                    cleaned = response.text or text
                except Exception:
                    # Fallback to regex if AI fails
                    cleaned = _clean_ai_mode(
                        text,
                        convert_numbered_lists=options.get(
                            "ai_numbered_to_dash", False
                        ),
                    )
            else:
                cleaned = _clean_ai_mode(
                    text,
                    convert_numbered_lists=options.get("ai_numbered_to_dash", False),
                )

        cleaned = _apply_basic_cleaning_options(
            cleaned,
            opt_tab=options.get("opt_tab", True),
            opt_multi_space=options.get("opt_multi_space", True),
            opt_empty_lines=options.get("opt_empty_lines", True),
            opt_trim_lines=options.get("opt_trim_lines", True),
            opt_line_numbers=options.get("opt_line_numbers", False),
            opt_urls=options.get("opt_urls", False),
            opt_special_chars=options.get("opt_special_chars", False),
            opt_merge_lines=options.get("opt_merge_lines", False),
        )
    elif mode == "plain":
        cleaned = _convert_markdown_to_plain_text(
            text,
            keep_link_urls=options.get("keep_link_urls", True),
            keep_code_blocks=options.get("keep_code_blocks", True),
            keep_lists=options.get("keep_lists", True),
        )
    elif mode == "word":
        cleaned = _convert_markdown_to_word_text(
            text,
            keep_link_urls=options.get("keep_link_urls", True),
            keep_code_blocks=options.get("keep_code_blocks", True),
            keep_lists=options.get("keep_lists", True),
        )

    return _json(
        {"original_len": len(text), "cleaned_len": len(cleaned), "cleaned": cleaned}
    )


async def tool_settlement(request: Request):
    payload = await request.json()
    people = payload.get("people") or []
    expenses = payload.get("expenses") or []
    if not people:
        return _json({"error": "사람 목록을 입력하세요."}, status_code=400)

    result = calculate_settlement(people, expenses)
    return _json(
        {
            "summary_rows": result.summary_rows,
            "transfer_rows": result.transfer_rows,
            "errors": result.errors,
        }
    )


async def folder_sync_status(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    service = get_folder_sync_service()
    return _json(service.status())


async def folder_sync_rescan(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    service = get_folder_sync_service()
    result = service.sync_now()
    return _json({"ok": True, **asdict(result)})


async def v6_health(_request: Request):
    available, reason = parser_bridge_available()
    return _json(
        {
            "ok": True,
            "parser_bridge_available": available,
            "reason": reason,
        }
    )


async def v6_parse(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        return _json({"error": message}, status_code=401)

    payload = await request.json()
    raw_text = str(payload.get("raw_text") or payload.get("text") or "").strip()
    patient_id = str(payload.get("patient_id") or "").strip() or "patient_001"
    source = str(payload.get("source") or "emr").strip() or "emr"
    source_path = str(payload.get("source_path") or "").strip()

    if not raw_text:
        return _json({"error": "raw_text를 입력하세요."}, status_code=400)

    try:
        result = run_v6_parse(
            patient_id=patient_id,
            raw_text=raw_text,
            source=source,
            source_path=source_path,
        )
    except ParserBridgeError as exc:
        return _json({"error": str(exc)}, status_code=503)
    except Exception as exc:
        logger.exception("v6 parse failed")
        return _json({"error": str(exc)}, status_code=500)

    return _json(result)


async def v6_publish_sync(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        return _json({"error": message}, status_code=401)

    payload = await request.json()
    documents = payload.get("documents", [])
    manifest = payload.get("manifest", [])

    if not documents:
        return _json({"error": "동기화할 문서가 없습니다."}, status_code=400)

    bucket = get_bucket()
    synced_files = []

    for doc in documents:
        rel_path = doc.get("relativePath")
        content = doc.get("content", "")
        if not rel_path:
            continue

        blob_name = f"v6_sync/{rel_path}"
        blob = bucket.blob(blob_name)

        content_type = "text/plain; charset=utf-8"
        if rel_path.endswith(".csv"):
            content_type = "text/csv; charset=utf-8"
        elif rel_path.endswith(".md"):
            content_type = "text/markdown; charset=utf-8"

        blob.upload_from_string(content.encode("utf-8"), content_type=content_type)
        synced_files.append(blob_name)

    # Save manifest
    if manifest and documents:
        patient_id = documents[0].get("metadata", {}).get("patientId", "unknown")
        manifest_blob_name = (
            f"v6_sync/workspace/{patient_id}/_manifest_{secrets.token_hex(4)}.json"
        )
        manifest_blob = bucket.blob(manifest_blob_name)
        manifest_blob.upload_from_string(
            json.dumps(manifest).encode("utf-8"), content_type="application/json"
        )
        synced_files.append(manifest_blob_name)

    return _json({"ok": True, "synced_count": len(synced_files)})


async def settings_gemini_usage(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    try:
        multiplier = float(request.query_params.get("multiplier", 1.0))
        exchange_rate = float(
            request.query_params.get("exchange_rate", USD_TO_KRW_RATE)
        )
    except ValueError:
        multiplier = 1.0
        exchange_rate = USD_TO_KRW_RATE

    try:
        logs = _load_gemini_usage_logs()
    except Exception as exc:
        return _json({"error": str(exc)}, status_code=500)

    today_krw, month_krw, today_usd, month_usd = _sum_usage_costs(logs)
    total_tokens = sum(int(entry.get("total_tokens") or 0) for entry in logs)
    input_tokens = sum(int(entry.get("input_tokens") or 0) for entry in logs)
    output_tokens = sum(int(entry.get("output_tokens") or 0) for entry in logs)
    daily: dict[str, dict] = {}
    for entry in logs:
        entry_time = _parse_usage_time(entry.get("time", ""))
        day = entry_time.strftime("%Y-%m-%d") if entry_time else "unknown"
        row = daily.setdefault(
            day, {"date": day, "requests": 0, "tokens": 0, "cost_usd": 0.0}
        )
        row["requests"] += 1
        row["tokens"] += int(entry.get("total_tokens") or 0)
        from app.ai import _entry_cost_usd

        row["cost_usd"] += _entry_cost_usd(entry)

    daily_rows = sorted(daily.values(), key=lambda row: row["date"], reverse=True)[:10]
    base_multiplier = 10.0 * multiplier
    for row in daily_rows:
        adjusted_cost = row["cost_usd"] * exchange_rate * base_multiplier
        row["cost_label"] = format_krw_cost(adjusted_cost)

    today_adjusted = today_usd * exchange_rate * base_multiplier
    month_adjusted = month_usd * exchange_rate * base_multiplier

    return _json(
        {
            "model": GEMINI_MODEL,
            "request_count": len(logs),
            "today_cost_label": format_krw_cost(today_adjusted),
            "month_cost_label": format_krw_cost(month_adjusted),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "daily": daily_rows,
        }
    )


async def passkey_register_options(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    email = _request_email(request)
    try:
        return _json(passkeys.registration_options(email))
    except Exception as exc:
        return _json({"error": str(exc)}, status_code=400)


async def passkey_register_verify(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    email = _request_email(request)
    payload = await request.json()
    try:
        result = passkeys.verify_registration(email, payload)
        return _json({"ok": True, **result})
    except Exception as exc:
        logger.exception("Passkey registration error")
        return _json({"error": str(exc)}, status_code=400)


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


async def files_list(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    files = [
        {
            "name": item.name,
            "blob_name": item.blob_name,
            "size": item.size,
            "updated": item.updated.isoformat() if item.updated else "",
            "content_type": item.content_type or "",
            "download_url": create_file_download_url(item),
        }
        for item in list_uploaded_files()
    ]
    return _json({"files": files})


async def files_download(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    blob_name = request.query_params.get("blob_name")
    if not blob_name:
        return _json({"error": "blob_name is required"}, status_code=400)

    from app.storage import download_file_bytes

    content, content_type, original_name = download_file_bytes(blob_name)
    return _file_response_bytes(content, original_name or blob_name, content_type)


async def files_upload(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    form = await request.form()
    uploaded = []
    bucket = get_bucket()
    for _, upload in form.multi_items():
        if not hasattr(upload, "filename"):
            continue

        filename = str(upload.filename or "")
        ext = Path(filename).suffix.lower()
        allowed_extensions = {
            ".pdf",
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".gif",
            ".txt",
            ".md",
            ".markdown",
            ".csv",
            ".docx",
            ".xlsx",
            ".pptx",
        }
        if ext not in allowed_extensions:
            return _json(
                {"error": f"지원하지 않는 파일 형식입니다 ({ext})."}, status_code=400
            )

        content = await upload.read()
        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            return _json(
                {"error": f"{upload.filename} 파일이 50MB 제한을 초과했습니다."},
                status_code=413,
            )
        safe_original = Path(upload.filename).name.replace("\\", "_").replace("/", "_")
        name = Path(safe_original).stem or "file"
        new_filename = safe_original
        blob_name = normalize_blob_name(UPLOAD_PREFIX, new_filename)
        if bucket.blob(blob_name).exists():
            new_filename = f"{name}-{secrets.token_hex(3)}{ext}"
            blob_name = normalize_blob_name(UPLOAD_PREFIX, new_filename)
        blob = bucket.blob(blob_name)
        content_type = upload.content_type or guess_content_type(upload.filename)
        blob.metadata = {
            "original_name": safe_original,
            "uploaded_at": get_now().isoformat(),
        }
        blob.upload_from_string(content, content_type=content_type)
        uploaded.append({"name": safe_original, "blob_name": blob_name})
    list_uploaded_files_cached.clear()
    create_zip_of_files.clear()
    return _json({"uploaded": uploaded})


async def files_delete(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    payload = await request.json()
    delete_uploaded_file(payload.get("blob_name", ""))
    return _json({"ok": True})


async def files_zip(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    
    zip_path = create_zip_of_files()
    if not zip_path or not os.path.exists(zip_path):
        return _json({"error": "다운로드할 파일이 없습니다."}, status_code=404)
        
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename="jisong-cloud-files.zip",
        background=BackgroundTask(os.remove, zip_path)
    )


async def memos_list(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    return _json({"memos": load_memo_list_cached()})


async def memo_detail(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    return _json({"memo": load_single_memo_content(request.path_params["file_name"])})


async def memo_download(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    memo = load_single_memo_content(request.path_params["file_name"])
    filename = f"{memo.get('title') or 'memo'}.txt"
    return _file_response_bytes(
        (memo.get("content") or "").encode("utf-8"),
        filename,
        "text/plain; charset=utf-8",
    )


async def memo_save(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    payload = await request.json()
    save_memo_txt(
        payload.get("title", "메모"),
        payload.get("content", ""),
        payload.get("file_name") or None,
    )
    return _json({"ok": True})


async def memo_delete(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    payload = await request.json()
    delete_memo_txt(payload.get("file_name", ""))
    return _json({"ok": True})


async def memos_zip(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    memos = load_memo_list_cached()
    zip_buffer = create_zip_of_memos(memos)
    if not zip_buffer:
        return _json({"error": "다운로드할 메모가 없습니다."}, status_code=404)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="jisong-cloud-memos.zip"'
        },
    )


async def ai_analyze(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    payload = await request.json()
    prompt = (payload.get("prompt") or "").strip()
    if not prompt:
        return _json({"error": "분석할 요청을 입력하세요."}, status_code=400)
    api_key = _get_gemini_api_key()
    if not api_key:
        return _json(
            {"error": "Gemini API key가 설정되지 않았습니다."}, status_code=400
        )
    try:
        can_use, limit_message = _get_usage_limit_status()
        if not can_use:
            return _json({"error": limit_message}, status_code=429)
        selected_blob_names = set(payload.get("blob_names") or [])
        selected_memo_file_names = set(payload.get("memo_file_names") or [])
        selected_files = [
            file_info
            for file_info in list_uploaded_files()
            if file_info.blob_name in selected_blob_names
        ]
        selected_memos = [
            load_single_memo_content(file_name)
            for file_name in selected_memo_file_names
            if file_name
        ]
        result, usage_record = _run_gemini_analysis(
            api_key=api_key,
            selected_files=selected_files,
            selected_memos=selected_memos,
            extra_text=payload.get("extra_text", ""),
            question=prompt,
        )
        _record_gemini_usage(usage_record)
        return _json(
            {
                "result": _postprocess_ai_result(result),
                "usage": usage_record,
            }
        )
    except Exception as exc:
        return _json({"error": str(exc)}, status_code=500)


async def tool_markdown_pdf(request: Request):
    ok, message = _is_authorized(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    payload = await request.json()
    markdown = (payload.get("markdown") or "").strip()
    if not markdown:
        return _json({"error": "변환할 마크다운을 입력하세요."}, status_code=400)
    try:
        pdf_bytes = markdown_to_pdf_bytes(markdown)
    except Exception as exc:
        return _json({"error": str(exc)}, status_code=500)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="jisong-markdown.pdf"'},
    )


async def frontend(request: Request):
    path = request.path_params.get("path") or "index.html"
    target = (FRONTEND_DIR / path).resolve()
    if FRONTEND_DIR not in target.parents and target != FRONTEND_DIR:
        return Response("not found", status_code=404)
    if target.is_dir():
        target = target / "index.html"
    if not target.exists():
        target = FRONTEND_DIR / "index.html"
    if target == (FRONTEND_DIR / "index.html").resolve():
        response = Response(_render_frontend_html(), media_type="text/html")
        if not request.cookies.get("jisong_access_logged"):
            client_ip = get_client_ip(request.headers, _request_client_host(request))
            headers_dict = dict(request.headers)
            response.background = BackgroundTask(
                log_access_request, headers_dict, client_ip
            )
            response.set_cookie("jisong_access_logged", "1", max_age=3600 * 24)
        return response
    media_type = mimetypes.guess_type(target.name)[0]
    return FileResponse(target, media_type=media_type)


routes = [
    Route("/api/health", health, methods=["GET"]),
    Route("/api/v6/health", v6_health, methods=["GET"]),
    Route("/api/session", session, methods=["GET"]),
    Route("/api/usage/summary", usage_summary, methods=["GET"]),
    Route("/api/sync/status", folder_sync_status, methods=["GET"]),
    Route("/api/sync/rescan", folder_sync_rescan, methods=["POST"]),
    Route("/api/settings/access-logs", settings_access_logs, methods=["GET"]),
    Route(
        "/api/settings/access-logs/clear", settings_access_logs_clear, methods=["POST"]
    ),
    Route("/api/settings/password", settings_password_update, methods=["POST"]),
    Route("/api/settings/gemini-usage", settings_gemini_usage, methods=["GET"]),
    Route(
        "/api/auth/passkey/register/options", passkey_register_options, methods=["POST"]
    ),
    Route(
        "/api/auth/passkey/register/verify", passkey_register_verify, methods=["POST"]
    ),
    Route("/api/auth/passkey/login/options", passkey_login_options, methods=["POST"]),
    Route("/api/auth/passkey/login/verify", passkey_login_verify, methods=["POST"]),
    Route("/api/auth/logout", auth_logout, methods=["POST"]),
    Route("/api/auth/account/login", account_login, methods=["POST"]),
    Route("/api/files", files_list, methods=["GET"]),
    Route("/api/files", files_upload, methods=["POST"]),
    Route("/api/files/download", files_download, methods=["GET"]),
    Route("/api/files/delete", files_delete, methods=["POST"]),
    Route("/api/files/zip", files_zip, methods=["GET"]),
    Route("/api/memos", memos_list, methods=["GET"]),
    Route("/api/memos", memo_save, methods=["POST"]),
    Route("/api/memos/delete", memo_delete, methods=["POST"]),
    Route("/api/memos/zip", memos_zip, methods=["GET"]),
    Route("/api/memos/{file_name:str}/download", memo_download, methods=["GET"]),
    Route("/api/memos/{file_name:str}", memo_detail, methods=["GET"]),
    Route("/api/ai/analyze", ai_analyze, methods=["POST"]),
    Route("/api/tools/markdown-pdf", tool_markdown_pdf, methods=["POST"]),
    Route("/api/tools/text-cleaner", tool_text_cleaner, methods=["POST"]),
    Route("/api/tools/settlement", tool_settlement, methods=["POST"]),
    Route("/api/v6/parse", v6_parse, methods=["POST"]),
    Route("/api/v6/publish", v6_publish_sync, methods=["POST"]),
    Route("/", frontend, methods=["GET"]),
    Route("/{path:path}", frontend, methods=["GET"]),
]


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


@asynccontextmanager
async def lifespan(_app):
    start_folder_sync_service()
    _cleanup_expired_sessions()
    try:
        yield
    finally:
        stop_folder_sync_service()


app = Starlette(debug=False, routes=routes, lifespan=lifespan)
