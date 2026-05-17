import os
import time
import streamlit as st

from app.config import get_admin_password
from app.streamlit_compat import render_inline_html

MAX_LOGIN_FAILURES = 5
LOGIN_LOCK_SECONDS = 600

# def get_admin_password(): ... (removed and moved to config.py)

def is_authenticated() -> bool:
    # Streamlit version
    try:
        import streamlit as st
        return st.session_state.get("authenticated", False)
    except Exception:
        return False


def should_require_auth_for_all_pages() -> bool:
    value = os.getenv("REQUIRE_AUTH_ALL", "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_lock_remaining_seconds() -> int:
    until_ts = int(st.session_state.get("auth_lock_until", 0) or 0)
    now_ts = int(time.time())
    return max(0, until_ts - now_ts)


def login_screen():
    st.markdown(
        """
        <div class="content-hero content-hero--auth">
            <p class="content-hero__eyebrow">Protected Area</p>
            <h1 class="content-hero__title">인증이 필요한 작업 공간입니다.</h1>
            <p class="content-hero__body">
                개인 작업 데이터를 다루는 기능이기 때문에 관리자 비밀번호 확인 후 접근할 수 있습니다.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "auth_failed_attempts" not in st.session_state:
        st.session_state.auth_failed_attempts = 0

    lock_remaining = _get_lock_remaining_seconds()
    if lock_remaining > 0:
        st.error(
            f"로그인 실패가 반복되어 잠시 잠겼습니다. {lock_remaining}초 후 다시 시도해주세요."
        )

    with st.form("login_form", clear_on_submit=False):
        pwd_input = st.text_input("비밀번호", type="password", key="login_pwd_input")
        submit_button = st.form_submit_button(
            "로그인",
            type="primary",
            use_container_width=True,
        )

        if submit_button:
            correct_pwd = get_admin_password()
            if lock_remaining > 0:
                st.error("잠금 시간이 끝난 뒤 다시 시도해주세요.")
            elif not correct_pwd:
                st.error("관리자 비밀번호가 설정되지 않았습니다.")
            elif pwd_input == correct_pwd:
                st.session_state.authenticated = True
                st.session_state.auth_failed_attempts = 0
                st.session_state.auth_lock_until = 0
                st.toast("✅ 인증되었습니다.")
                st.rerun()
            else:
                st.session_state.auth_failed_attempts += 1
                remain = MAX_LOGIN_FAILURES - st.session_state.auth_failed_attempts
                if remain <= 0:
                    st.session_state.auth_lock_until = int(time.time()) + LOGIN_LOCK_SECONDS
                    st.session_state.auth_failed_attempts = 0
                    st.error("❌ 비밀번호가 올바르지 않아 로그인 시도가 잠겼습니다.")
                else:
                    st.error(f"❌ 비밀번호가 올바르지 않습니다. 남은 시도: {remain}회")

    render_inline_html(
        f"""
        <script>
        // unique execution: {time.time()}
        function focusInput() {{
            var docs = [document];
            try {{
                if (window.parent && window.parent !== window) {{
                    docs.push(window.parent.document);
                }}
            }} catch (e) {{}}
            for (var i = 0; i < docs.length; i++) {{
                var input = docs[i].querySelector('input[type="password"]');
                if (input) {{ input.focus(); return true; }}
            }}
            return false;
        }}
        if (!focusInput()) {{
            var attempts = 0;
            var interval = setInterval(function() {{
                attempts += 1;
                if (focusInput() || attempts >= 20) {{
                    clearInterval(interval);
                }}
            }}, 100);
        }}
        </script>
        """,
        height=0,
        width=0,
    )
