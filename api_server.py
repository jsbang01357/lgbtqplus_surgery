import mimetypes
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from app import passkeys
from app.security import allow_google_auth_fallback, get_access_context, require_cloudflare_access
from app.storage import (
    create_zip_of_files,
    create_file_download_url,
    delete_uploaded_file,
    guess_content_type,
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
    _get_gemini_api_key,
    _get_usage_limit_status,
    _postprocess_ai_result,
    _record_gemini_usage,
    _run_gemini_analysis,
)
from app.gcs_helper import get_bucket
from app.core_utils import get_now

FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"


def _json(data, status_code=200):
    return JSONResponse(data, status_code=status_code)


def _request_email(request: Request) -> str:
    return get_access_context(request.headers).email or "local-dev@jisong.dev"


def _passkey_token(request: Request) -> str:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header.split(" ", 1)[1].strip()
    return request.cookies.get("jisong_passkey_session", "")


def _access_context_allowed(request: Request) -> tuple[bool, str]:
    access_context = get_access_context(request.headers)
    if require_cloudflare_access() and not access_context.allowed:
        return False, "Cloudflare Access 인증이 필요합니다."
    return True, ""


def _auth_state(request: Request) -> dict:
    access_context = get_access_context(request.headers)
    email = _request_email(request)
    passkey_ok = passkeys.verify_session(_passkey_token(request), email=email)
    access_ok = access_context.allowed or not require_cloudflare_access()
    google_fallback_ok = allow_google_auth_fallback() and access_context.allowed
    authorized = access_ok and (passkey_ok or google_fallback_ok)
    auth_method = ""
    if authorized:
        auth_method = "passkey" if passkey_ok else "google"
    return {
        "email": email,
        "access_context": access_context,
        "access_ok": access_ok,
        "passkey_ok": passkey_ok,
        "google_fallback_ok": google_fallback_ok,
        "authorized": authorized,
        "auth_method": auth_method,
    }


def _is_authorized(request: Request) -> tuple[bool, str]:
    state = _auth_state(request)
    if not state["access_ok"]:
        return False, "Cloudflare Access 인증이 필요합니다."
    if not state["authorized"]:
        return False, "패스키 인증이 필요합니다."
    return True, ""


async def health(_request: Request):
    return _json({"ok": True, "service": "jisong-cloud-api"})


async def session(request: Request):
    state = _auth_state(request)
    access_context = state["access_context"]
    return _json(
        {
            "cloudflare_access_required": require_cloudflare_access(),
            "google_auth_fallback_allowed": allow_google_auth_fallback(),
            "cloudflare_access": {
                "email": access_context.email,
                "has_jwt": access_context.has_jwt,
                "allowed": access_context.allowed,
            },
            "passkey_authenticated": state["passkey_ok"],
            "authorized": state["authorized"],
            "auth_method": state["auth_method"],
        }
    )


async def passkey_register_options(request: Request):
    ok, message = _access_context_allowed(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    email = _request_email(request)
    try:
        return _json(passkeys.registration_options(email))
    except Exception as exc:
        return _json({"error": str(exc)}, status_code=400)


async def passkey_register_verify(request: Request):
    ok, message = _access_context_allowed(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    email = _request_email(request)
    payload = await request.json()
    try:
        result = passkeys.verify_registration(email, payload)
        return _json({"ok": True, **result})
    except Exception as exc:
        return _json({"error": str(exc)}, status_code=400)


async def passkey_login_options(request: Request):
    ok, message = _access_context_allowed(request)
    if not ok:
        return _json({"error": message}, status_code=401)
    email = _request_email(request)
    try:
        return _json(passkeys.authentication_options(email))
    except Exception as exc:
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
        secure=True,
        samesite="lax",
    )
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
        content = await upload.read()
        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            return _json({"error": f"{upload.filename} 파일이 50MB 제한을 초과했습니다."}, status_code=413)
        name = Path(upload.filename).stem
        ext = Path(upload.filename).suffix
        new_filename = f"{name}_{get_now().strftime('%Y%m%d_%H%M%S')}{ext}"
        blob_name = normalize_blob_name(UPLOAD_PREFIX, new_filename)
        blob = bucket.blob(blob_name)
        content_type = upload.content_type or guess_content_type(upload.filename)
        blob.upload_from_string(content, content_type=content_type)
        uploaded.append({"name": new_filename, "blob_name": blob_name})
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
    zip_buffer = create_zip_of_files()
    if not zip_buffer:
        return _json({"error": "다운로드할 파일이 없습니다."}, status_code=404)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="jisong-cloud-files.zip"'},
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
        headers={"Content-Disposition": 'attachment; filename="jisong-cloud-memos.zip"'},
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
        return _json({"error": "Gemini API key가 설정되지 않았습니다."}, status_code=400)
    try:
        can_use, limit_message = _get_usage_limit_status()
        if not can_use:
            return _json({"error": limit_message}, status_code=429)
        result, usage_record = _run_gemini_analysis(
            api_key=api_key,
            selected_files=[],
            selected_memos=[],
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


async def frontend(request: Request):
    path = request.path_params.get("path") or "index.html"
    target = (FRONTEND_DIR / path).resolve()
    if FRONTEND_DIR not in target.parents and target != FRONTEND_DIR:
        return Response("not found", status_code=404)
    if target.is_dir():
        target = target / "index.html"
    if not target.exists():
        target = FRONTEND_DIR / "index.html"
    media_type = mimetypes.guess_type(target.name)[0]
    return FileResponse(target, media_type=media_type)


routes = [
    Route("/api/health", health, methods=["GET"]),
    Route("/api/session", session, methods=["GET"]),
    Route("/api/auth/passkey/register/options", passkey_register_options, methods=["POST"]),
    Route("/api/auth/passkey/register/verify", passkey_register_verify, methods=["POST"]),
    Route("/api/auth/passkey/login/options", passkey_login_options, methods=["POST"]),
    Route("/api/auth/passkey/login/verify", passkey_login_verify, methods=["POST"]),
    Route("/api/files", files_list, methods=["GET"]),
    Route("/api/files", files_upload, methods=["POST"]),
    Route("/api/files/delete", files_delete, methods=["POST"]),
    Route("/api/files/zip", files_zip, methods=["GET"]),
    Route("/api/memos", memos_list, methods=["GET"]),
    Route("/api/memos", memo_save, methods=["POST"]),
    Route("/api/memos/delete", memo_delete, methods=["POST"]),
    Route("/api/memos/zip", memos_zip, methods=["GET"]),
    Route("/api/memos/{file_name:str}", memo_detail, methods=["GET"]),
    Route("/api/ai/analyze", ai_analyze, methods=["POST"]),
    Route("/", frontend, methods=["GET"]),
    Route("/{path:path}", frontend, methods=["GET"]),
]

app = Starlette(debug=False, routes=routes)
