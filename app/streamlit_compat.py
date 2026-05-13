import streamlit as st


def render_inline_html(source: str, *, height: int = 0, width: int = 0) -> None:
    try:
        import streamlit.components.v1 as components

        html_renderer = getattr(components, "html", None)
        if callable(html_renderer):
            html_renderer(source, height=height, width=width)
            return
    except Exception:
        pass

    html_renderer = getattr(st, "html", None)
    if callable(html_renderer):
        html_renderer(source)
        return

    iframe_renderer = getattr(st, "iframe", None)
    if callable(iframe_renderer) and source.strip().startswith(("http://", "https://")):
        iframe_renderer(source, height=height, width=width)

