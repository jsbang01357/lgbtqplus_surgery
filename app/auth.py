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
    st.title("🔒 인증 필요")
    st.info("이 기능에 접근하려면 관리자 비밀번호를 입력해주세요.")
    
    # st.form을 사용하여 엔터 키 입력 시 자동 제출되도록 함
    with st.form("login_form", clear_on_submit=False):
        pwd_input = st.text_input("비밀번호", type="password", key="login_pwd_input")
        submit_button = st.form_submit_button("로그인", type="primary", use_container_width=True)
        
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
                
    # 로딩 지연 문제 해결 및 메뉴 전환 시 매번 실행되도록 고유 키(time.time) 부여
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
