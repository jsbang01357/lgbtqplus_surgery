import os
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
                
    # 자동 포커싱을 위한 자바스크립트 주입 (로딩 지연 문제 해결을 위해 Polling 방식 적용)
    components.html(
        """
        <script>
        function focusInput() {
            var doc = window.parent.document;
            var input = doc.querySelector('input[type="password"]');
            if (input) {
                input.focus();
                return true;
            }
            return false;
        }

        // DOM이 완전히 렌더링될 때까지 100ms 간격으로 여러 번 시도
        if (!focusInput()) {
            var interval = setInterval(function() {
                if (focusInput()) {
                    clearInterval(interval);
                }
            }, 100);
            
            // 3초 후에는 시도 중단
            setTimeout(function() {
                clearInterval(interval);
            }, 3000);
        }
        </script>
        """,
        height=0,
        width=0,
    )
