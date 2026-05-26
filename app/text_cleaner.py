
import re



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


