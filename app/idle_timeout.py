import streamlit as st
import streamlit.components.v1 as components


IDLE_TIMEOUT_SECONDS = 10 * 60


def inject_idle_timeout(timeout_seconds: int = IDLE_TIMEOUT_SECONDS):
    timeout_ms = int(timeout_seconds * 1000)
    components.html(
        f"""
        <script>
        (function () {{
            var timeoutMs = {timeout_ms};
            var timer = null;
            var closed = false;

            function showFallback() {{
                var doc = window.parent.document;
                if (doc.getElementById("idle-timeout-overlay")) {{
                    return;
                }}
                var overlay = doc.createElement("div");
                overlay.id = "idle-timeout-overlay";
                overlay.style.position = "fixed";
                overlay.style.inset = "0";
                overlay.style.zIndex = "2147483647";
                overlay.style.background = "#0f172a";
                overlay.style.color = "#f8fafc";
                overlay.style.display = "flex";
                overlay.style.alignItems = "center";
                overlay.style.justifyContent = "center";
                overlay.style.padding = "24px";
                overlay.style.textAlign = "center";
                overlay.style.fontFamily = "system-ui, -apple-system, BlinkMacSystemFont, sans-serif";
                overlay.innerHTML = '<div><h1 style="font-size:28px;margin:0 0 12px 0;">비활성 상태로 종료를 시도했습니다.</h1><p style="font-size:16px;line-height:1.6;margin:0;color:#cbd5e1;">브라우저 정책상 자동으로 닫히지 않을 수 있습니다.<br>비용 절약을 위해 이 창을 닫아주세요.</p></div>';
                doc.body.appendChild(overlay);
            }}

            function expire() {{
                if (closed) {{
                    return;
                }}
                closed = true;
                try {{
                    window.parent.close();
                }} catch (err) {{}}
                window.setTimeout(function () {{
                    try {{
                        if (!window.parent.closed) {{
                            showFallback();
                        }}
                    }} catch (err) {{
                        showFallback();
                    }}
                }}, 350);
            }}

            function resetTimer() {{
                if (closed) {{
                    return;
                }}
                if (timer) {{
                    window.clearTimeout(timer);
                }}
                timer = window.setTimeout(expire, timeoutMs);
            }}

            ["mousemove", "keydown", "scroll", "touchstart", "click"].forEach(function (eventName) {{
                window.parent.document.addEventListener(eventName, resetTimer, true);
            }});
            resetTimer();
        }})();
        </script>
        """,
        height=0,
        width=0,
    )

