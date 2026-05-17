import streamlit as st
import re


def _render_result(clean_input, cleaned):
    """정리 결과를 화면에 출력합니다."""
    st.markdown("---")
    st.subheader("✨ 정리된 결과")

    orig_len = len(clean_input)
    clean_len = len(cleaned)
    changed = clean_len - orig_len
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.metric("원본 글자수", f"{orig_len}자")
    with col_s2:
        st.metric("정리 후 글자수", f"{clean_len}자")
    with col_s3:
        st.metric("글자수 변화", f"{changed:+}자")

    st.text_area(
        "결과 (아래 버튼으로 복사 가능)",
        value=cleaned,
        height=250,
        key="clean_result_area",
    )


def _clean_ai_mode(text: str, convert_numbered_lists: bool = False) -> str:
    """AI 답변/복붙 텍스트를 Markdown 친화적으로 정리"""
    if not text:
        return text

    cleaned = text

    # 줄바꿈 통일
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

    # 탭 제거
    cleaned = cleaned.replace("\t", " ")

    # 구분선 제거: --- / ⸻ / *** / ___ / em dash 류
    cleaned = re.sub(
        r"^[ \t]*([\-—–_=*]{3,}|⸻)[ \t]*$",
        "",
        cleaned,
        flags=re.MULTILINE,
    )

    # 불릿 기호 통일: • · ● ○ ◦ ▪ ■ □ ◆ ◇ ‣ ⁃ * - – —
    cleaned = re.sub(
        r"^[ \t]*([•·●○◦▪■□◆◇‣⁃\*\-–—])[ \t]+",
        "- ",
        cleaned,
        flags=re.MULTILINE,
    )

    # "-    내용" 같은 것 정리
    cleaned = re.sub(r"^[ \t]*-\s*", "- ", cleaned, flags=re.MULTILINE)

    # 번호 리스트도 전부 - 로 바꾸고 싶을 때 옵션
    if convert_numbered_lists:
        cleaned = re.sub(r"^[ \t]*\d+[.)][ \t]+", "- ", cleaned, flags=re.MULTILINE)

    # 줄 끝 공백 제거
    cleaned = re.sub(r"[ \t]+$", "", cleaned, flags=re.MULTILINE)

    # 빈 줄 과다 정리 (3줄 이상 -> 2줄)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()


def _normalize_text(text: str) -> str:
    """공통 줄바꿈과 탭 문자를 정리합니다."""
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")


def _strip_markdown_inline(text: str, keep_link_urls: bool) -> str:
    """인라인 Markdown 문법을 읽기 좋은 텍스트로 바꿉니다."""
    if keep_link_urls:
        text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r"\1 (\2)", text)
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    else:
        text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)
    text = re.sub(r"(\*|_)(.*?)\1", r"\2", text)
    text = re.sub(r"~~(.*?)~~", r"\1", text)
    return text


def _convert_markdown_text(
    text: str,
    *,
    word_style: bool,
    keep_link_urls: bool,
    keep_code_blocks: bool,
    keep_lists: bool,
) -> str:
    """Markdown을 복사하기 좋은 plain text 또는 Word용 텍스트로 변환합니다."""
    if not text:
        return text

    normalized = _normalize_text(text)
    code_blocks = []

    def replace_code_block(match):
        code = match.group(2).strip("\n")
        if not keep_code_blocks:
            return ""

        placeholder = f"%%CODEBLOCK{len(code_blocks)}%%"
        code_blocks.append(code)
        return placeholder

    normalized = re.sub(
        r"```([^\n`]*)\n?(.*?)```",
        replace_code_block,
        normalized,
        flags=re.DOTALL,
    )

    lines = []
    for raw_line in normalized.splitlines():
        line = raw_line.strip()

        if not line:
            lines.append("")
            continue

        if re.fullmatch(r"([\-*_])\1{2,}", line):
            lines.append("")
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            heading = _strip_markdown_inline(
                heading_match.group(2).strip(),
                keep_link_urls,
            )
            if word_style and lines and lines[-1] != "":
                lines.append("")
            lines.append(heading)
            if word_style:
                lines.append("")
            continue

        line = re.sub(r"^>\s?", "", line)

        unordered_match = re.match(r"^[-*+]\s+(.+)$", line)
        ordered_match = re.match(r"^(\d+)[.)]\s+(.+)$", line)
        task_match = re.match(r"^[-*+]\s+\[[ xX]\]\s+(.+)$", line)

        if task_match:
            item = _strip_markdown_inline(task_match.group(1).strip(), keep_link_urls)
            lines.append(f"- {item}" if keep_lists else item)
            continue

        if unordered_match:
            item = _strip_markdown_inline(
                unordered_match.group(1).strip(), keep_link_urls
            )
            lines.append(f"- {item}" if keep_lists else item)
            continue

        if ordered_match:
            item = _strip_markdown_inline(
                ordered_match.group(2).strip(), keep_link_urls
            )
            lines.append(f"{ordered_match.group(1)}. {item}" if keep_lists else item)
            continue

        line = _strip_markdown_inline(line, keep_link_urls)
        lines.append(line)

    converted = "\n".join(lines)

    for index, code in enumerate(code_blocks):
        converted = converted.replace(f"%%CODEBLOCK{index}%%", code)

    converted = re.sub(r"[ \t]+$", "", converted, flags=re.MULTILINE)
    converted = re.sub(r"\n{3,}", "\n\n", converted)
    return converted.strip()


def _convert_markdown_to_plain_text(
    text: str,
    *,
    keep_link_urls: bool = True,
    keep_code_blocks: bool = True,
    keep_lists: bool = True,
) -> str:
    return _convert_markdown_text(
        text,
        word_style=False,
        keep_link_urls=keep_link_urls,
        keep_code_blocks=keep_code_blocks,
        keep_lists=keep_lists,
    )


def _convert_markdown_to_word_text(
    text: str,
    *,
    keep_link_urls: bool = True,
    keep_code_blocks: bool = True,
    keep_lists: bool = True,
) -> str:
    return _convert_markdown_text(
        text,
        word_style=True,
        keep_link_urls=keep_link_urls,
        keep_code_blocks=keep_code_blocks,
        keep_lists=keep_lists,
    )


def _apply_basic_cleaning_options(
    text: str,
    *,
    opt_tab: bool,
    opt_multi_space: bool,
    opt_empty_lines: bool,
    opt_trim_lines: bool,
    opt_line_numbers: bool,
    opt_urls: bool,
    opt_special_chars: bool,
    opt_merge_lines: bool,
) -> str:
    cleaned = text

    if opt_tab:
        cleaned = cleaned.replace("\t", " ")

    if opt_trim_lines:
        cleaned = "\n".join(line.strip() for line in cleaned.splitlines())

    if opt_multi_space:
        cleaned = "\n".join(" ".join(line.split()) for line in cleaned.splitlines())

    if opt_empty_lines:
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    if opt_line_numbers:
        cleaned = re.sub(r"^\d+[\.\)]\s*", "", cleaned, flags=re.MULTILINE)

    if opt_urls:
        cleaned = re.sub(r"https?://\S+", "", cleaned)

    if opt_special_chars:
        cleaned = re.sub(r"[^\w\s가-힣\-]", "", cleaned)

    if opt_merge_lines:
        cleaned = " ".join(cleaned.splitlines())
        cleaned = " ".join(cleaned.split())

    return cleaned.strip()


def render_text_cleaner():
    """텍스트 클리너 메인 UI"""

    st.markdown("**출력 형식**")

    output_mode = st.radio(
        "출력 형식",
        ["기본 정리", "Markdown → Plain Text", "Markdown → Word용 텍스트"],
        index=2,
        horizontal=False,
        label_visibility="collapsed",
    )

    if output_mode == "기본 정리":
        st.caption(
            "• 기존 방식으로 공백, 불릿, 구분선, 특수문자 옵션을 직접 조합합니다."
        )
    elif output_mode == "Markdown → Plain Text":
        st.caption("• 마크다운 기호를 제거하고 일반 텍스트로 읽기 좋게 바꿉니다.")
    else:
        st.caption(
            "• 제목 앞뒤 여백과 목록 구조를 살려 Word에 붙여넣기 좋은 텍스트로 바꿉니다."
        )

    # 세부 옵션들을 익스팬더로 숨김
    with st.expander("🛠️ 상세 옵션 설정"):
        if output_mode == "기본 정리":
            ai_mode = st.checkbox(
                "AI mode (불릿 정리, 구분선 제거, 불필요한 공백 최적화)",
                value=True,
            )
            if ai_mode:
                st.caption(
                    "• AI 답변이나 복붙 텍스트의 특수 불릿과 구분선을 깔끔하게 정리합니다."
                )

            col_opt1, col_opt2 = st.columns(2)
            with col_opt1:
                opt_tab = st.checkbox("탭 문자 제거", value=True)
                opt_multi_space = st.checkbox("연속 공백 → 단일 공백", value=True)
                opt_empty_lines = st.checkbox("연속 빈 줄 → 한 줄로", value=True)
                opt_trim_lines = st.checkbox("각 줄 앞뒤 공백 제거", value=True)
            with col_opt2:
                opt_line_numbers = st.checkbox(
                    "줄번호 제거 (예: 1. 또는 1) )", value=False
                )
                opt_urls = st.checkbox("URL 제거", value=False)
                opt_special_chars = st.checkbox(
                    "특수문자 제거 (글자/숫자/공백만 남김)", value=False
                )
                opt_merge_lines = st.checkbox(
                    "모든 줄바꿈 제거 (한 문단으로)", value=False
                )

            st.markdown("---")
            opt_ai_numbered_to_dash = st.checkbox(
                "AI mode: 번호 리스트도 '- '로 변환 (예: 1. 제목 → - 제목)",
                value=False,
            )
        else:
            keep_link_urls = st.checkbox("링크 URL 유지", value=True)
            keep_code_blocks = st.checkbox("코드블록 내용 유지", value=True)
            keep_lists = st.checkbox("목록 기호와 번호 유지", value=True)

            opt_tab = True
            opt_multi_space = False
            opt_empty_lines = True
            opt_trim_lines = True
            opt_line_numbers = False
            opt_urls = False
            opt_special_chars = False
            opt_merge_lines = False
            ai_mode = False
            opt_ai_numbered_to_dash = False

    st.markdown("---")
    clean_input = st.text_area(
        "변환할 텍스트를 입력하세요",
        height=250,
        placeholder="여기에 마크다운이나 복붙 텍스트를 붙여넣으세요...",
    )

    if st.button("깨끗하게 정리하기", type="primary", use_container_width=True):
        if clean_input:
            if output_mode == "기본 정리":
                cleaned = clean_input
                if ai_mode:
                    cleaned = _clean_ai_mode(
                        cleaned,
                        convert_numbered_lists=opt_ai_numbered_to_dash,
                    )
                cleaned = _apply_basic_cleaning_options(
                    cleaned,
                    opt_tab=opt_tab,
                    opt_multi_space=opt_multi_space,
                    opt_empty_lines=opt_empty_lines,
                    opt_trim_lines=opt_trim_lines,
                    opt_line_numbers=opt_line_numbers,
                    opt_urls=opt_urls,
                    opt_special_chars=opt_special_chars,
                    opt_merge_lines=opt_merge_lines,
                )
            elif output_mode == "Markdown → Plain Text":
                cleaned = _convert_markdown_to_plain_text(
                    clean_input,
                    keep_link_urls=keep_link_urls,
                    keep_code_blocks=keep_code_blocks,
                    keep_lists=keep_lists,
                )
            else:
                cleaned = _convert_markdown_to_word_text(
                    clean_input,
                    keep_link_urls=keep_link_urls,
                    keep_code_blocks=keep_code_blocks,
                    keep_lists=keep_lists,
                )

            _render_result(clean_input, cleaned)
        else:
            st.warning("텍스트를 입력해주세요.")
