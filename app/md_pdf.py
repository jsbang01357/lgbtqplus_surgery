

WEASYPRINT_INSTALL_HINT = """
WeasyPrint 실행에 필요한 시스템 라이브러리를 찾지 못했습니다.

macOS 로컬 실행 환경에서는 Homebrew로 아래 패키지를 설치한 뒤 앱을 다시 시작하세요.

brew install glib pango gdk-pixbuf libffi

Cloud Run/Docker 배포 환경은 Dockerfile의 apt 패키지로 처리합니다.
""".strip()


PDF_CSS = """
@page {
    size: A4;
    margin: 22mm 18mm;
}
body {
    font-family: "Noto Sans CJK KR", "Noto Sans KR", sans-serif;
    color: #172033;
    font-size: 11pt;
    line-height: 1.65;
}
h1, h2, h3 {
    color: #14213f;
    line-height: 1.25;
    margin: 1.2em 0 0.45em;
}
h1 {
    font-size: 22pt;
    border-bottom: 2px solid #d8e2f3;
    padding-bottom: 0.25em;
}
h2 {
    font-size: 16pt;
}
h3 {
    font-size: 13pt;
}
p {
    margin: 0.45em 0;
}
code {
    font-family: "Noto Sans Mono CJK KR", monospace;
    background: #eef3fb;
    border-radius: 4px;
    padding: 0.08em 0.25em;
}
pre {
    background: #111827;
    color: #f8fafc;
    padding: 12px 14px;
    border-radius: 8px;
    overflow-wrap: break-word;
    white-space: pre-wrap;
}
pre code {
    background: transparent;
    color: inherit;
    padding: 0;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
}
th, td {
    border: 1px solid #ccd6e6;
    padding: 7px 9px;
    vertical-align: top;
}
th {
    background: #eef3fb;
}
blockquote {
    margin: 1em 0;
    padding: 0.4em 1em;
    border-left: 4px solid #86a5e7;
    color: #475569;
    background: #f6f8fc;
}
"""


def markdown_to_pdf_bytes(markdown_text: str) -> bytes:
    try:
        import markdown
        from weasyprint import CSS, HTML
    except ImportError as exc:
        raise RuntimeError("markdown 또는 weasyprint 패키지가 설치되어 있지 않습니다.") from exc
    except OSError as exc:
        raise RuntimeError(f"{WEASYPRINT_INSTALL_HINT}\n\n원본 오류: {exc}") from exc

    body = markdown.markdown(
        markdown_text,
        extensions=["tables", "fenced_code", "nl2br", "sane_lists"],
        output_format="html5",
    )
    html = f"<!doctype html><html><head><meta charset='utf-8'></head><body>{body}</body></html>"
    try:
        return HTML(string=html).write_pdf(stylesheets=[CSS(string=PDF_CSS)])
    except OSError as exc:
        raise RuntimeError(f"{WEASYPRINT_INSTALL_HINT}\n\n원본 오류: {exc}") from exc


def decode_markdown_upload(uploaded_file) -> str:
    return uploaded_file.getvalue().decode("utf-8-sig", errors="replace")
