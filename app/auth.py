import os
import time
import streamlit as st

from app.streamlit_compat import render_inline_html

MAX_LOGIN_FAILURES = 5
LOGIN_LOCK_SECONDS = 600


def get_admin_password() -> str:
    # Cloud Run / environment variable first.
    env_pwd = os.getenv("ADMIN_PASSWORD")
    if env_pwd:
        return env_pwd

    # Local Streamlit secrets fallback.
    try:
        admin_section = st.secrets["admin"]
        if "admin_password" in admin_section and admin_section["admin_password"]:
            return admin_section["admin_password"]
    except Exception:
        pass

    try:
        root_pwd = st.secrets["admin_password"]
        if root_pwd:
            return root_pwd
    except Exception:
        pass
    return ""


def is_authenticated() -> bool:
    return st.session_state.get("authenticated", False)


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
            var doc = window.parent.document;
            var input = doc.querySelector('input[type="password"]');
            if (input) {{ input.focus(); return true; }}
            return false;
        }}
        if (!focusInput()) {{
            var interval = setInterval(function() {{ if (focusInput()) {{ clearInterval(interval); }} }}, 100);
            setTimeout(function() {{ clearInterval(interval); }}, 2000);
        }}
        </script>
        """,
        height=0,
        width=0,
    )
