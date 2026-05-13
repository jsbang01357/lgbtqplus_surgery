import os
import time
import streamlit as st
import streamlit.components.v1 as components


def get_admin_password() -> str:
    # 1) Cloud Run / 환경변수 우선
    env_pwd = os.getenv("ADMIN_PASSWORD")
    if env_pwd:
        return env_pwd

    # 2) 로컬 Streamlit secrets fallback
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

    # 3) 아무것도 없으면 빈 문자열
    return ""

def is_authenticated() -> bool:
    return st.session_state.get("authenticated", False)


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

    with st.form("login_form", clear_on_submit=False):
        pwd_input = st.text_input("비밀번호", type="password", key="login_pwd_input")
        submit_button = st.form_submit_button(
            "로그인",
            type="primary",
            use_container_width=True,
        )

        if submit_button:
            correct_pwd = get_admin_password()

            if not correct_pwd:
                st.error("관리자 비밀번호가 설정되지 않았습니다.")
            elif pwd_input == correct_pwd:
                st.session_state.authenticated = True
                st.toast("✅ 인증되었습니다.")
                st.rerun()
            else:
                st.error("❌ 비밀번호가 올바르지 않습니다.")

    components.html(
        f"""
        <script>
        // unique execution: {time.time()}
        function focusInput() {{
            var doc = window.parent.document;
            var input = doc.querySelector('input[type="password"]');
            if (input) {{
                input.focus();
                return true;
            }}
            return false;
        }}

        if (!focusInput()) {{
            var interval = setInterval(function() {{
                if (focusInput()) {{
                    clearInterval(interval);
                }}
            }}, 100);
            
            setTimeout(function() {{
                clearInterval(interval);
            }}, 2000);
        }}
        </script>
        """,
        height=0,
        width=0,
    )
