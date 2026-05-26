import io
import json
import logging
import re
import zipfile
from datetime import datetime
from pathlib import PurePosixPath
from xml.etree import ElementTree



from app.core_utils import get_now, ttl_cache
from app.config import get_gemini_api_key, get_config
from app.gcs_helper import get_bucket
from app.storage import download_file_bytes


logger = logging.getLogger(__name__)

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
MAX_USAGE_LOGS = 50
GEMINI_DAILY_LIMIT_KRW = 5000
GEMINI_MONTHLY_LIMIT_KRW = 15000


def _get_float_config(env_name: str, secret_name: str, default: float) -> float:
    try:
        return float(get_config(env_name, str(default)))
    except (TypeError, ValueError):
        return default


GEMINI_INPUT_PRICE_PER_1M = _get_float_config(
    "GEMINI_INPUT_PRICE_PER_1M", "input_price_per_1m", 0.50
)
GEMINI_OUTPUT_PRICE_PER_1M = _get_float_config(
    "GEMINI_OUTPUT_PRICE_PER_1M", "output_price_per_1m", 3.00
)
USD_TO_KRW_RATE = _get_float_config("USD_TO_KRW_RATE", "usd_to_krw_rate", 1478)


MEDICAL_ABBREVIATIONS = {
    "HTN": "Hypertension",
    "DM": "Diabetes Mellitus",
    "CKD": "Chronic Kidney Disease",
    "CHF": "Congestive Heart Failure",
    "COPD": "Chronic Obstructive Pulmonary Disease",
    "CABG": "Coronary Artery Bypass Graft",
    "MI": "Myocardial Infarction",
    "CPR": "Cardiopulmonary Resuscitation",
}
PERSON_NAME_LABEL_RE = re.compile(
    r"(?P<label>(?:환자명|성명|이름)\s*[:：]\s*)(?P<name>[가-힣]{2,4})"
)
PERSON_NAME_CONTEXT_RE = re.compile(r"(?P<name>[가-힣]{2,4})(?=\s*(?:님|씨|환자))")

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
                "각 질문에 대해 교수님께서 하실 만한 예상 답변도 함께 적어줘.",
            ]
        ),
    },
    {
        "label": "국시 핵심 개념",
        "prompt": "국시 대비 관점에서 중요한 개념을 우선순위로 설명하고, 자주 출제되는 함정 포인트를 같이 정리해줘.",
    },
    {
        "label": "자료 요약",
        "prompt": "\n".join(
            [
                "선택한 자료의 내용을 한글로 요약해줘.",
                "자료의 핵심 주제, 주요 내용, 중요한 수치나 결론을 정리해줘.",
                "특히 내가 국시대비를 위해 꼭 알아야 할 내용이 있다면 더 공부해볼 키워드와 설명을 정리해줘",
            ]
        ),
    },
]


def _get_gemini_api_key() -> str:
    return get_gemini_api_key()


def _get_model_name() -> str:
    return get_config("GEMINI_MODEL", "gemini-3-flash-preview")


GEMINI_MODEL = _get_model_name()


def _is_supported_file(filename: str) -> bool:
    return PurePosixPath(filename).suffix.lower() in SUPPORTED_EXTENSIONS


def _is_office_text_file(filename: str) -> bool:
    return PurePosixPath(filename).suffix.lower() in OFFICE_TEXT_EXTENSIONS


def _file_label(file_info) -> str:
    size_mb = file_info.size / (1024 * 1024)
    return f"{file_info.name} ({size_mb:.1f} MB)"


def _memo_label(memo_info: dict) -> str:
    updated_at = (
        memo_info.get("updated_at") or memo_info.get("created_at") or "시간 정보 없음"
    )
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
                targets = [
                    name
                    for name in names
                    if name.startswith("word/") and name.endswith(".xml")
                ]
            elif ext == ".pptx":
                targets = sorted(
                    name
                    for name in names
                    if name.startswith("ppt/slides/slide") and name.endswith(".xml")
                )
            elif ext == ".xlsx":
                targets = [
                    name
                    for name in names
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
            file_parts.append(
                f"파일명: {file_info.name}\n내용: 텍스트를 추출하지 못했습니다."
            )
            continue
        file_parts.append(f"파일명: {file_info.name}\n내용:\n{text}")
    return "\n\n---\n\n".join(file_parts)


def _get_text_file_context(selected_files) -> str:
    file_parts = []
    for file_info in selected_files:
        ext = PurePosixPath(file_info.name).suffix.lower()
        if ext not in {".txt", ".md", ".markdown", ".csv"}:
            continue
        data = download_file_bytes(file_info.blob_name)
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("utf-8", errors="replace")
        file_parts.append(f"파일명: {file_info.name}\n내용:\n{text}")
    return "\n\n---\n\n".join(file_parts)


def _build_analysis_prompt(
    selected_files,
    selected_memos: list[dict],
    extra_text: str,
    question: str,
    include_text_files: bool = False,
) -> str:
    prompt_parts = [
        "너는 개인 클라우드에 저장된 문서와 텍스트를 분석하는 한국어 비서야.",
        "나는 의과대학 본과 4학년 학생이야. 주로 병원 실습 관련 내용을 다룰거야.",
        "답변은 읽기 좋게 제목, 핵심 요약, 세부 내용, 정리 순서로 정리해줘.",
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

    if include_text_files:
        text_file_context = _get_text_file_context(selected_files)
        if text_file_context:
            prompt_parts.append(f"선택한 텍스트 파일:\n{text_file_context}")

    return "\n\n".join(prompt_parts)




def _mask_person_names(text: str) -> str:
    def replace_label_match(match: re.Match) -> str:
        return f"{match.group('label')}[이름 비공개]"

    masked = PERSON_NAME_LABEL_RE.sub(replace_label_match, text)
    return PERSON_NAME_CONTEXT_RE.sub("[이름 비공개]", masked)


def _expand_medical_abbreviations_once(text: str) -> str:
    expanded = text
    for abbreviation, full_name in MEDICAL_ABBREVIATIONS.items():
        pattern = re.compile(rf"\b{re.escape(abbreviation)}\b(?!\s*\()", re.IGNORECASE)

        def replace_once(match: re.Match) -> str:
            original = match.group(0)
            return f"{original} ({full_name})"

        expanded = pattern.sub(replace_once, expanded, count=1)
    return expanded


def _postprocess_ai_result(result: str) -> str:
    return _expand_medical_abbreviations_once(_mask_person_names(result))



def _format_chat_history_markdown(history: list[dict]) -> str:
    parts = []
    for index, item in enumerate(history, start=1):
        question = str(item.get("q", "")).strip() or "(질문 없음)"
        answer = str(item.get("a", "")).strip() or "(답변 없음)"
        parts.append(f"## 대화 {index}\n\n**Q.** {question}\n\n**A.**\n\n{answer}")
    return "\n\n---\n\n".join(parts)



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


@ttl_cache(seconds=30)
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
        
    krw = _entry_cost_krw(usage_record)
    bucket = get_bucket()
    
    # 1. Update tiny summary file safely (Fast)
    for _ in range(5):
        summary_blob = bucket.blob("logs/usage_summary.json")
        try:
            if summary_blob.exists():
                summary_blob.reload()
                gen = summary_blob.generation
                summary = json.loads(summary_blob.download_as_text())
            else:
                gen = 0
                now = get_now()
                logs = _load_gemini_usage_logs()
                tk, mk, _, _ = _sum_usage_costs(logs)
                summary = {"today_krw": tk, "month_krw": mk, "today": now.strftime("%Y-%m-%d"), "month": now.strftime("%Y-%m")}
                
            now_date = get_now().strftime("%Y-%m-%d")
            now_month = get_now().strftime("%Y-%m")
            
            if summary.get("today") != now_date:
                summary["today"] = now_date
                summary["today_krw"] = 0
            if summary.get("month") != now_month:
                summary["month"] = now_month
                summary["month_krw"] = 0
                
            summary["today_krw"] += krw
            summary["month_krw"] += krw
            
            summary_blob.upload_from_string(json.dumps(summary), content_type="application/json", if_generation_match=gen)
            break
        except Exception:
            continue

    # 2. Update recent UI log (Shrink to MAX_USAGE_LOGS)
    for _ in range(3):
        logs, generation = _read_gemini_usage_blob()
        logs.insert(0, usage_record)
        try:
            _save_gemini_usage_logs(logs, generation)
            _load_gemini_usage_logs.clear()
            return
        except Exception:
            continue
    logger.warning("Gemini 사용량 최근 로그 UI 업데이트를 건너뛰었습니다 (동시성 충돌).")


def _parse_usage_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _entry_cost_usd(entry: dict) -> float:
    if "estimated_cost_usd" in entry:
        return float(entry.get("estimated_cost_usd") or 0)
    # Fallback for old logs
    if "estimated_cost_krw" in entry:
        return float(entry.get("estimated_cost_krw") or 0) / USD_TO_KRW_RATE
    return 0.0


def _entry_cost_krw(entry: dict) -> float:
    if "estimated_cost_krw" in entry:
        return float(entry.get("estimated_cost_krw") or 0)
    return _entry_cost_usd(entry) * USD_TO_KRW_RATE


def _sum_usage_costs(logs: list[dict]) -> tuple[float, float, float, float]:
    now = get_now()
    today_key = now.strftime("%Y-%m-%d")
    month_key = now.strftime("%Y-%m")
    today_krw = 0.0
    month_krw = 0.0
    today_usd = 0.0
    month_usd = 0.0

    for entry in logs:
        entry_time = _parse_usage_time(entry.get("time", ""))
        if entry_time is None:
            continue
        usd = _entry_cost_usd(entry)
        krw = usd * USD_TO_KRW_RATE
        if entry_time.strftime("%Y-%m") == month_key:
            month_krw += krw
            month_usd += usd
        if entry_time.strftime("%Y-%m-%d") == today_key:
            today_krw += krw
            today_usd += usd
    return today_krw, month_krw, today_usd, month_usd


def format_krw_cost(cost: float) -> str:
    rounded = int(float(cost or 0) + 0.5)
    return f"₩{rounded:,}"


def _get_usage_summary_cache() -> dict:
    bucket = get_bucket()
    blob = bucket.blob("logs/usage_summary.json")
    if blob.exists():
        try:
            return json.loads(blob.download_as_text())
        except Exception:
            pass
    # Fallback to computing from existing logs if summary missing
    logs = _load_gemini_usage_logs()
    tk, mk, _, _ = _sum_usage_costs(logs)
    return {"today_krw": tk, "month_krw": mk}


def get_monthly_gemini_cost_label() -> str:
    summary = _get_usage_summary_cache()
    return format_krw_cost(summary.get("month_krw", 0))


def _get_usage_limit_status() -> tuple[bool, str]:
    summary = _get_usage_summary_cache()
    today_krw = summary.get("today_krw", 0)
    month_krw = summary.get("month_krw", 0)

    if today_krw >= GEMINI_DAILY_LIMIT_KRW:
        return (
            False,
            "오늘 Gemini 예상 비용이 "
            f"{format_krw_cost(today_krw)}로 일일 한도 "
            f"{format_krw_cost(GEMINI_DAILY_LIMIT_KRW)}를 넘었습니다.",
        )

    if month_krw >= GEMINI_MONTHLY_LIMIT_KRW:
        return (
            False,
            "이번 달 Gemini 예상 비용이 "
            f"{format_krw_cost(month_krw)}로 월 한도 "
            f"{format_krw_cost(GEMINI_MONTHLY_LIMIT_KRW)}를 넘었습니다.",
        )

    return True, ""


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

    prompt = _build_analysis_prompt(
        selected_files=selected_files,
        selected_memos=selected_memos,
        extra_text=extra_text,
        question=question,
    )

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

        contents = [prompt, *uploaded_files]
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
        )
        return response.text or "분석 결과가 비어 있습니다.", _extract_usage_record(
            response
        )
    finally:
        for uploaded in uploaded_files:
            try:
                client.files.delete(name=uploaded.name)
            except Exception:
                pass

