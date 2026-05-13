import io
import os
from pathlib import PurePosixPath

import streamlit as st

from app.core_utils import get_now
from app.memo import load_memo_list_cached, load_single_memo_content, save_memo_txt
from app.storage import download_file_bytes, list_uploaded_files


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
}


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
                "각 질문마다 왜 좋은 질문인지 한 줄로 설명해줘.",
            ]
        ),
    },
    {
        "label": "문제목록/계획",
        "prompt": "\n".join(
            [
                "선택한 자료를 바탕으로 이 환자의 active problem list를 우선순위대로 정리해줘.",
                "각 problem마다 근거, 현재 상태, 오늘 확인할 것, plan을 간결하게 써줘.",
                "불확실하거나 자료가 부족한 부분은 추정하지 말고 추가 확인 필요로 표시해줘.",
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


def _append_question_preset(prompt: str):
    current = st.session_state.get("ai_question", "").strip()
    st.session_state.ai_question = f"{current}\n\n{prompt}".strip() if current else prompt


def _run_gemini_analysis(
    api_key: str,
    selected_files,
    selected_memos: list[dict],
    extra_text: str,
    question: str,
) -> str:
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

    try:
        for file_info in selected_files:
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
            model="gemini-2.5-flash",
            contents=contents,
        )
        return response.text or "분석 결과가 비어 있습니다."
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

    files = list_uploaded_files()
    supported_files = [file_info for file_info in files if _is_supported_file(file_info.name)]
    unsupported_count = len(files) - len(supported_files)

    if unsupported_count:
        st.caption(f"PDF, 이미지, TXT, MD, CSV만 v1 분석 대상으로 표시합니다. 제외된 파일: {unsupported_count}개")

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
            with column:
                if st.button(
                    preset["label"],
                    key=f"ai_prompt_preset_{row_start}_{preset['label']}",
                    use_container_width=True,
                ):
                    _append_question_preset(preset["prompt"])

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
                st.session_state.ai_result = _run_gemini_analysis(
                    api_key=api_key,
                    selected_files=selected_files,
                    selected_memos=selected_memos,
                    extra_text=extra_text,
                    question=question,
                )
                st.session_state.ai_result_title = f"AI 분석 {get_now().strftime('%Y-%m-%d %H:%M')}"
                st.toast("✅ 분석이 완료되었습니다.")
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
