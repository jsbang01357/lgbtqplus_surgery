import mimetypes
from fastapi import APIRouter, Request, BackgroundTasks, Depends
from fastapi.responses import FileResponse, StreamingResponse, Response
import io

from app.api_deps import _json, FRONTEND_DIR, _render_frontend_html, _request_client_host, get_current_user
from app.storage import list_uploaded_files
from app.memo import load_single_memo_content
from app.ai import _get_gemini_api_key, _get_model_name, _get_usage_limit_status, _postprocess_ai_result, _record_gemini_usage, _run_gemini_analysis
from app.request_utils import get_client_ip
from app.md_pdf import markdown_to_pdf_bytes
from app.access_logger import log_access_request
from app.text_cleaner import _clean_ai_mode, _apply_basic_cleaning_options, _convert_markdown_to_plain_text, _convert_markdown_to_word_text
from app.settlement import calculate_settlement

router = APIRouter()

@router.post('/api/tools/text-cleaner')
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

@router.post('/api/tools/settlement')
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

@router.post('/api/ai/analyze')
async def ai_analyze(request: Request, _: bool = Depends(get_current_user)):
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

@router.post('/api/tools/markdown-pdf')
async def tool_markdown_pdf(request: Request):
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
            tasks = BackgroundTasks()
            tasks.add_task(log_access_request, headers_dict, client_ip)
            response.background = tasks
            #
                
            response.set_cookie("jisong_access_logged", "1", max_age=3600 * 24)
        return response
    media_type = mimetypes.guess_type(target.name)[0]
    return FileResponse(target, media_type=media_type)
