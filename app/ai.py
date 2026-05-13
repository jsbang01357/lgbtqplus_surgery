import io
import json
import os
import zipfile
from datetime import datetime
from pathlib import PurePosixPath
from xml.etree import ElementTree

import streamlit as st
from google.api_core.exceptions import PreconditionFailed

from app.core_utils import get_now
from app.gcs_helper import get_bucket
from app.md_pdf import markdown_to_pdf_bytes
from app.memo import load_memo_list_cached, load_single_memo_content, save_memo_txt
from app.storage import download_file_bytes, list_uploaded_files
from components.custom_copy_btn import copy_to_clipboard


SUPPORTED_EXTENSIONS = {
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
GEMINI_UPLOAD_EXTENSIONS = SUPPORTED_EXTENSIONS - {".docx", ".xlsx", ".pptx"}
OFFICE_TEXT_EXTENSIONS = {".docx", ".xlsx", ".pptx"}

GEMINI_USAGE_LOG_BLOB = "logs/gemini_usage.json"
MAX_USAGE_LOGS = 1000


def _get_config_value(env_name: str, secret_name: str, default):
    env_value = os.getenv(env_name)
    if env_value not in (None, ""):
        return env_value

    try:
        value = st.secrets["gemini"].get(secret_name)
        if value not in (None, ""):
            return value
    except Exception:
        pass

    return default


def _get_float_config(env_name: str, secret_name: str, default: float) -> float:
    try:
        return float(_get_config_value(env_name, secret_name, default))
    except (TypeError, ValueError):
        return default


GEMINI_MODEL = str(_get_config_value("GEMINI_MODEL", "model", "gemini-3-flash-preview"))
GEMINI_INPUT_PRICE_PER_1M = _get_float_config("GEMINI_INPUT_PRICE_PER_1M", "input_price_per_1m", 0.50)
GEMINI_OUTPUT_PRICE_PER_1M = _get_float_config("GEMINI_OUTPUT_PRICE_PER_1M", "output_price_per_1m", 3.00)
USD_TO_KRW_RATE = _get_float_config("USD_TO_KRW_RATE", "usd_to_krw_rate", 1478)


PROMPT_PRESETS = [
    {
        "label": "SOAP 1분 발표",
        "prompt": "\n".join(
            [
                "선택한 자료의 특정 환자를 교수님 앞에서 1분 안에 발표할 수 있게 SOAP 형식으로 정리해줘.",
                "S/O/A/P를 명확히 나누고, 발표용 말투로 자연스럽게 이어지는 스크립트도 함께 써줘.",
                "핵심 문제, 중요한 수치 변화, 현재 판단, 오늘의 계획이 빠지지 않게 해줘.",
            ]
        ),
    },
    {
        "label": "예상 Q&A",
        "prompt": "\n".join(
            [
                "선택한 자료의 특정 환자에 대해 교수님이 물어볼 가능성이 높은 질문과 모범 답변을 만들어줘.",
                "진단 근거, 감별진단, 검사 해석, 치료 계획, follow-up 포인트를 포함해줘.",
                "질문은 날카로운 순서로 10개 정도, 답변은 실제 구두 답변처럼 짧고 정확하게 써줘.",
            ]
        ),
    },
    {
        "label": "교수님께 질문",
        "prompt": "\n".join(
            [
                "선택한 자료의 특정 환자에 대해 교수님께 물어보면 좋은 질문을 뽑아줘.",
                "단순 확인 질문보다 임상 판단, 치료 방향, 놓치기 쉬운 risk, 다음 decision point에 관한 질문을 우선해줘.",
                "각 질문마다 교수님의 답변도 적어줘.",
            ]
        ),
    },
    {
        "label": "자료 요약",
        "prompt": "\n".join(
            [
                "선택한 자료의 내용을 한글로 요약해줘.",
                "자료의 핵심 주제, 주요 내용, 중요한 수치나 결론을 3~5문장으로 간결하게 정리해줘.",
            ]
        ),
    },
]


def _get_gemini_api_key() -> str:
    env_key = os.getenv("GEMINI_API_KEY")
    if env_key:
        return env_key

    try:
        key = st.secrets["gemini"]["api_key"]
        if key:
            return key
    except Exception:
        pass

    return ""


def _is_supported_file(filename: str) -> bool:
    return PurePosixPath(filename).suffix.lower() in SUPPORTED_EXTENSIONS


def _is_office_text_file(filename: str) -> bool:
    return PurePosixPath(filename).suffix.lower() in OFFICE_TEXT_EXTENSIONS


def _file_label(file_info) -> str:
    size_mb = file_info.size / (1024 * 1024)
    return f"{file_info.name} ({size_mb:.1f} MB)"


def _memo_label(memo_info: dict) -> str:
    updated_at = memo_info.get("updated_at") or memo_info.get("created_at") or "시간 정보 없음"
    title = memo_info.get("title") or memo_info["file_name"]
    return f"{title} · {updated_at} · {memo_info['file_name']}"


def _format_memo_context(selected_memos: list[dict]) -> str:
    memo_parts = []
    for memo in selected_memos:
        content = memo.get("content", "").strip()
        if not content:
            continue
        memo_parts.append(
            "\n".join(
                [
                    f"제목: {memo.get('title') or memo.get('file_name', '제목 없음')}",
                    f"작성: {memo.get('created_at') or '시간 정보 없음'}",
                    f"수정: {memo.get('updated_at') or '시간 정보 없음'}",
                    "내용:",
                    content,
                ]
            )
        )
    return "\n\n---\n\n".join(memo_parts)


def _extract_xml_text(zip_file: zipfile.ZipFile, path: str) -> str:
    try:
        root = ElementTree.fromstring(zip_file.read(path))
    except Exception:
        return ""
    return "\n".join(part.strip() for part in root.itertext() if part.strip())


def _extract_office_text(filename: str, data: bytes) -> str:
    ext = PurePosixPath(filename).suffix.lower()
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            if ext == ".docx":
                targets = [name for name in names if name.startswith("word/") and name.endswith(".xml")]
            elif ext == ".pptx":
                targets = sorted(
                    name for name in names
                    if name.startswith("ppt/slides/slide") and name.endswith(".xml")
                )
            elif ext == ".xlsx":
                targets = [
                    name for name in names
                    if name == "xl/sharedStrings.xml"
                    or (name.startswith("xl/worksheets/") and name.endswith(".xml"))
                ]
            else:
                return ""

            text_parts = [_extract_xml_text(zf, target) for target in targets]
    except zipfile.BadZipFile:
        return ""
    return "\n\n".join(part for part in text_parts if part).strip()


def _format_office_context(selected_files) -> str:
    file_parts = []
    for file_info in selected_files:
        if not _is_office_text_file(file_info.name):
            continue
        data = download_file_bytes(file_info.blob_name)
        text = _extract_office_text(file_info.name, data)
        if not text:
            file_parts.append(f"파일명: {file_info.name}\n내용: 텍스트를 추출하지 못했습니다.")
            continue
        file_parts.append(f"파일명: {file_info.name}\n내용:\n{text}")
    return "\n\n---\n\n".join(file_parts)


def _append_question_preset(prompt: str):
    current = st.session_state.get("ai_question", "").strip()
    st.session_state.ai_question = f"{current}\n\n{prompt}".strip() if current else prompt


def _remove_question_preset(prompt: str):
    current = st.session_state.get("ai_question", "")
    updated = current.replace(f"\n\n{prompt}", "").replace(prompt, "", 1).strip()
    st.session_state.ai_question = updated


def _toggle_question_preset(preset: dict):
    active_labels = set(st.session_state.get("ai_active_prompt_presets", []))
    label = preset["label"]
    if label in active_labels:
        active_labels.remove(label)
        _remove_question_preset(preset["prompt"])
    else:
        active_labels.add(label)
        _append_question_preset(preset["prompt"])
    st.session_state.ai_active_prompt_presets = sorted(active_labels)


def _result_download_filename(extension: str) -> str:
    timestamp = get_now().strftime("%Y%m%d_%H%M")
    return f"ai_analysis_{timestamp}.{extension}"


def _get_ai_result_pdf_bytes(result: str) -> bytes | None:
    if st.session_state.get("ai_result_pdf_source") != result:
        st.session_state.ai_result_pdf_source = result
        st.session_state.ai_result_pdf_bytes = None
        st.session_state.ai_result_pdf_error = ""
        try:
            st.session_state.ai_result_pdf_bytes = markdown_to_pdf_bytes(result)
        except RuntimeError as exc:
            st.session_state.ai_result_pdf_error = str(exc)
    return st.session_state.get("ai_result_pdf_bytes")


def _read_gemini_usage_blob() -> tuple[list[dict], int | None]:
    bucket = get_bucket()
    blob = bucket.blob(GEMINI_USAGE_LOG_BLOB)
    if not blob.exists():
        return [], None

    blob.reload()
    generation = int(blob.generation) if blob.generation is not None else None
    try:
        data = json.loads(blob.download_as_text(encoding="utf-8"))
    except Exception:
        return [], generation
    return data if isinstance(data, list) else [], generation


@st.cache_data(ttl=30)
def _load_gemini_usage_logs() -> list[dict]:
    logs, _ = _read_gemini_usage_blob()
    return logs


def _save_gemini_usage_logs(logs: list[dict], generation: int | None):
    bucket = get_bucket()
    blob = bucket.blob(GEMINI_USAGE_LOG_BLOB)
    match_generation = generation if generation is not None else 0
    blob.upload_from_string(
        json.dumps(logs[:MAX_USAGE_LOGS], ensure_ascii=False, indent=2),
        content_type="application/json; charset=utf-8",
        if_generation_match=match_generation,
    )


def _usage_value(usage_metadata, name: str) -> int:
    if usage_metadata is None:
        return 0
    value = getattr(usage_metadata, name, 0)
    if value is None and hasattr(usage_metadata, "get"):
        value = usage_metadata.get(name, 0)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _extract_usage_record(response) -> dict:
    usage = getattr(response, "usage_metadata", None)
    input_tokens = _usage_value(usage, "prompt_token_count")
    candidate_tokens = _usage_value(usage, "candidates_token_count")
    thoughts_tokens = _usage_value(usage, "thoughts_token_count")
    total_tokens = _usage_value(usage, "total_token_count")

    output_tokens = candidate_tokens + thoughts_tokens
    if output_tokens == 0 and total_tokens > input_tokens:
        output_tokens = total_tokens - input_tokens

    estimated_cost = (
        input_tokens * GEMINI_INPUT_PRICE_PER_1M
        + output_tokens * GEMINI_OUTPUT_PRICE_PER_1M
    ) / 1_000_000
    estimated_cost_krw = estimated_cost * USD_TO_KRW_RATE
    return {
        "time": get_now().isoformat(),
        "model": GEMINI_MODEL,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens or input_tokens + output_tokens,
        "estimated_cost_usd": estimated_cost,
        "estimated_cost_krw": estimated_cost_krw,
    }


def _record_gemini_usage(usage_record: dict):
    if not usage_record.get("input_tokens") and not usage_record.get("output_tokens"):
        return
    for _ in range(3):
        logs, generation = _read_gemini_usage_blob()
        logs.insert(0, usage_record)
        try:
            _save_gemini_usage_logs(logs, generation)
            _load_gemini_usage_logs.clear()
            return
        except PreconditionFailed:
            continue
    raise RuntimeError("Gemini 사용량 로그가 동시에 수정되어 저장하지 못했습니다.")


def _parse_usage_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _entry_cost_krw(entry: dict) -> float:
    if "estimated_cost_krw" in entry:
        return float(entry.get("estimated_cost_krw") or 0)
    return float(entry.get("estimated_cost_usd") or 0) * USD_TO_KRW_RATE


def _sum_usage_costs(logs: list[dict]) -> tuple[float, float]:
    now = get_now()
    today_key = now.strftime("%Y-%m-%d")
    month_key = now.strftime("%Y-%m")
    today_total = 0.0
    month_total = 0.0

    for entry in logs:
        entry_time = _parse_usage_time(entry.get("time", ""))
        if entry_time is None:
            continue
        cost = _entry_cost_krw(entry)
        if entry_time.strftime("%Y-%m") == month_key:
            month_total += cost
        if entry_time.strftime("%Y-%m-%d") == today_key:
            today_total += cost
    return today_total, month_total


def format_krw_cost(cost: float) -> str:
    rounded = int(float(cost or 0) + 0.5)
    return f"₩{rounded:,}"


def get_monthly_gemini_cost_label() -> str:
    logs = _load_gemini_usage_logs()
    _, month_total = _sum_usage_costs(logs)
    return format_krw_cost(month_total)


def _render_usage_cost_summary():
    try:
        logs = _load_gemini_usage_logs()
    except Exception as exc:
        st.caption(f"Gemini 예상 비용 로그를 불러오지 못했습니다: {exc}")
        return

    today_total, month_total = _sum_usage_costs(logs)
    col_today, col_month, col_model = st.columns(3)
    with col_today:
        st.metric("오늘 예상 Gemini 비용", format_krw_cost(today_total))
    with col_month:
        st.metric("이번 달 예상 Gemini 비용", format_krw_cost(month_total))
    with col_model:
        st.metric("모델", GEMINI_MODEL)
    st.caption(
        "Gemini 응답의 usage metadata와 Gemini 3 Flash Preview 유료 Standard 단가"
        f"($0.50/1M input, $3.00/1M output, 1 USD = {USD_TO_KRW_RATE:,} KRW)로 계산한 앱 내부 추정치입니다."
    )


def _run_gemini_analysis(
    api_key: str,
    selected_files,
    selected_memos: list[dict],
    extra_text: str,
    question: str,
) -> tuple[str, dict]:
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("google-genai 패키지가 설치되어 있지 않습니다.") from exc

    client = genai.Client(api_key=api_key)
    uploaded_files = []

    prompt_parts = [
        "너는 개인 클라우드에 저장된 문서와 텍스트를 분석하는 한국어 비서야.",
        "답변은 읽기 좋게 제목, 핵심 요약, 세부 내용, 다음 행동 제안 순서로 정리해줘.",
    ]
    if question.strip():
        prompt_parts.append(f"사용자 질문:\n{question.strip()}")
    else:
        prompt_parts.append("사용자 질문이 없으면 선택한 자료의 핵심 내용을 요약해줘.")
    if extra_text.strip():
        prompt_parts.append(f"추가 텍스트:\n{extra_text.strip()}")
    memo_context = _format_memo_context(selected_memos)
    if memo_context:
        prompt_parts.append(f"선택한 메모:\n{memo_context}")
    office_context = _format_office_context(selected_files)
    if office_context:
        prompt_parts.append(f"선택한 Office 파일에서 추출한 텍스트:\n{office_context}")

    try:
        for file_info in selected_files:
            if _is_office_text_file(file_info.name):
                continue
            data = download_file_bytes(file_info.blob_name)
            file_io = io.BytesIO(data)
            file_io.name = file_info.name
            uploaded = client.files.upload(
                file=file_io,
                config={
                    "mime_type": file_info.content_type or "application/octet-stream",
                    "display_name": file_info.name,
                },
            )
            uploaded_files.append(uploaded)

        contents = ["\n\n".join(prompt_parts), *uploaded_files]
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
        )
        return response.text or "분석 결과가 비어 있습니다.", _extract_usage_record(response)
    finally:
        for uploaded in uploaded_files:
            try:
                client.files.delete(name=uploaded.name)
            except Exception:
                pass


def render_ai():
    st.markdown(
        """
        <div class="section-block">
            <p class="section-block__eyebrow">AI</p>
            <h2 class="section-block__title">Gemini 파일 및 텍스트 분석</h2>
            <p class="section-block__body">
                웹하드 파일, 메모장 텍스트, 직접 입력한 텍스트를 함께 분석하고 결과를 메모로 남길 수 있습니다.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    api_key = _get_gemini_api_key()
    if not api_key:
        st.warning("Gemini API key가 설정되지 않았습니다. GEMINI_API_KEY 또는 st.secrets['gemini']['api_key']를 설정해주세요.")

    _render_usage_cost_summary()

    files = list_uploaded_files()
    supported_files = [file_info for file_info in files if _is_supported_file(file_info.name)]
    unsupported_count = len(files) - len(supported_files)

    if unsupported_count:
        st.caption(
            "PDF, 이미지, TXT, MD, CSV, DOCX, XLSX, PPTX 파일만 분석 대상으로 표시합니다. "
            f"제외된 파일: {unsupported_count}개"
        )

    file_options = {_file_label(file_info): file_info for file_info in supported_files}
    selected_labels = st.multiselect(
        "분석할 웹하드 파일 선택 (최대 5개)",
        options=list(file_options.keys()),
        max_selections=5,
        key="ai_selected_files",
    )
    selected_files = [file_options[label] for label in selected_labels]

    memos = load_memo_list_cached()
    memo_options = {_memo_label(memo_info): memo_info for memo_info in memos}
    selected_memo_labels = st.multiselect(
        "분석할 메모 선택 (최대 5개)",
        options=list(memo_options.keys()),
        max_selections=5,
        key="ai_selected_memos",
    )
    selected_memos = [
        load_single_memo_content(memo_options[label]["file_name"])
        for label in selected_memo_labels
    ]

    extra_text = st.text_area(
        "추가 텍스트",
        height=180,
        placeholder="파일이나 메모 외에 함께 분석할 텍스트가 있으면 붙여넣으세요.",
        key="ai_extra_text",
    )

    if "ai_question" not in st.session_state:
        st.session_state.ai_question = ""
    if "ai_active_prompt_presets" not in st.session_state:
        st.session_state.ai_active_prompt_presets = []

    st.markdown(
        """
        <div class="section-block section-block--spacious">
            <p class="section-block__eyebrow">Preset</p>
            <h3 class="section-block__title">자주 쓰는 요청</h3>
            <p class="section-block__body">
                버튼을 누르면 아래 질문 입력칸에 프롬프트가 추가됩니다.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    for row_start in range(0, len(PROMPT_PRESETS), 2):
        columns = st.columns(2)
        for column, preset in zip(columns, PROMPT_PRESETS[row_start : row_start + 2]):
            is_active = preset["label"] in st.session_state.ai_active_prompt_presets
            with column:
                if st.button(
                    preset["label"],
                    key=f"ai_prompt_preset_{row_start}_{preset['label']}",
                    type="primary" if is_active else "secondary",
                    use_container_width=True,
                ):
                    _toggle_question_preset(preset)
                    st.rerun()

    question = st.text_area(
        "질문 / 요청",
        height=140,
        placeholder="프리셋 버튼을 누르거나 직접 요청을 입력하세요.",
        key="ai_question",
    )

    can_analyze = bool(
        api_key and (selected_files or selected_memos or extra_text.strip() or question.strip())
    )
    if st.button("분석하기", type="primary", use_container_width=True, disabled=not can_analyze):
        with st.spinner("Gemini가 자료를 분석하는 중입니다..."):
            try:
                result_text, usage_record = _run_gemini_analysis(
                    api_key=api_key,
                    selected_files=selected_files,
                    selected_memos=selected_memos,
                    extra_text=extra_text,
                    question=question,
                )
                try:
                    _record_gemini_usage(usage_record)
                except Exception as usage_exc:
                    st.warning(f"분석은 완료됐지만 비용 로그 저장에 실패했습니다: {usage_exc}")
                st.session_state.ai_result = result_text
                st.session_state.ai_last_usage = usage_record
                st.session_state.ai_result_title = f"AI 분석 {get_now().strftime('%Y-%m-%d %H:%M')}"
                st.toast("✅ 분석이 완료되었습니다.")
                st.rerun()
            except Exception as exc:
                st.error(f"분석 중 오류가 발생했습니다: {exc}")

    result = st.session_state.get("ai_result")
    if not result:
        return

    st.markdown(
        """
        <div class="section-block section-block--spacious">
            <p class="section-block__eyebrow">Result</p>
            <h3 class="section-block__title">분석 결과</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(result)

    memo_title = st.text_input(
        "메모 저장 제목",
        value=st.session_state.get("ai_result_title", "AI 분석 결과"),
        key="ai_result_memo_title",
    )
    if st.button("메모로 저장", use_container_width=True, key="ai_save_to_memo"):
        save_memo_txt(memo_title.strip() or "AI 분석 결과", result)
        st.toast("✅ AI 분석 결과를 메모로 저장했습니다.")

    st.markdown(
        """
        <div class="section-block section-block--spacious">
            <p class="section-block__eyebrow">Export</p>
            <h3 class="section-block__title">결과 내보내기</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col_copy, col_md, col_pdf = st.columns(3)
    with col_copy:
        copy_to_clipboard(
            result,
            before_copy_label="복사",
            after_copy_label="복사됨",
            key="ai_result_copy",
        )
    with col_md:
        st.download_button(
            "MD 다운로드",
            data=result.encode("utf-8"),
            file_name=_result_download_filename("md"),
            mime="text/markdown",
            use_container_width=True,
        )
    with col_pdf:
        if st.session_state.get("ai_result_pdf_source") != result:
            st.session_state.ai_result_pdf_source = result
            st.session_state.ai_result_pdf_bytes = None
            st.session_state.ai_result_pdf_error = ""
        if st.session_state.get("ai_result_pdf_bytes"):
            st.download_button(
                "PDF 다운로드",
                data=st.session_state.ai_result_pdf_bytes,
                file_name=_result_download_filename("pdf"),
                mime="application/pdf",
                use_container_width=True,
            )
        elif st.button("PDF 준비하기", use_container_width=True, key="ai_prepare_pdf"):
            with st.spinner("PDF를 만드는 중입니다..."):
                _get_ai_result_pdf_bytes(result)
            st.rerun()
        else:
            st.button("PDF 다운로드", disabled=True, use_container_width=True)
    if st.session_state.get("ai_result_pdf_error"):
        st.warning(f"PDF 생성 준비 중 오류가 발생했습니다: {st.session_state.ai_result_pdf_error}")
