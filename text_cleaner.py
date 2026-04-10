import streamlit as st
import re
from custom_copy_btn import copy_to_clipboard

def _render_result(clean_input, cleaned):
    """정리 결과를 화면에 출력합니다."""
    st.markdown("---")
    st.subheader("✨ 정리된 결과")

    orig_len = len(clean_input)
    clean_len = len(cleaned)
    removed = orig_len - clean_len
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.metric("원본 글자수", f"{orig_len}자")
    with col_s2:
        st.metric("정리 후 글자수", f"{clean_len}자")
    with col_s3:
        st.metric("제거된 글자수", f"{removed}자")

    st.text_area("결과 (아래 버튼으로 복사 가능)", value=cleaned, height=250, key="clean_result_area")
    copy_to_clipboard(text=cleaned, before_copy_label="📋 결과 복사하기", after_copy_label="✅ 복사 완료", key="copy_clean_result")


def render_text_cleaner():
    """텍스트 클리너 메인 UI"""
    st.subheader("🧹 텍스트 클리너")
    st.info("입력한 텍스트에서 불필요한 서식을 제거하고 깔끔하게 정리합니다.")

    st.markdown("**정리 옵션**")
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        opt_tab = st.checkbox("탭 문자 제거", value=True)
        opt_multi_space = st.checkbox("연속 공백 → 단일 공백", value=True)
        opt_empty_lines = st.checkbox("연속 빈 줄 → 한 줄로", value=True)
        opt_trim_lines = st.checkbox("각 줄 앞뒤 공백 제거", value=True)
    with col_opt2:
        opt_line_numbers = st.checkbox("줄번호 제거 (예: 1. 또는 1) )", value=False)
        opt_urls = st.checkbox("URL 제거", value=False)
        opt_special_chars = st.checkbox("특수문자 제거 (글자/숫자/공백만 남김)", value=False)
        opt_merge_lines = st.checkbox("모든 줄바꿈 제거 (한 문단으로)", value=False)

    st.markdown("---")
    clean_input = st.text_area("정리할 텍스트를 입력하세요", height=250, placeholder="여기에 내용을 붙여넣으세요...")

    if st.button("깨끗하게 정리하기", type="primary", use_container_width=True):
        if clean_input:
            cleaned = clean_input

            if opt_tab:
                cleaned = cleaned.replace("\t", " ")
            if opt_trim_lines:
                cleaned = "\n".join(line.strip() for line in cleaned.splitlines())
            if opt_multi_space:
                cleaned = "\n".join(
                    " ".join(line.split()) for line in cleaned.splitlines()
                )
            if opt_empty_lines:
                cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
            if opt_line_numbers:
                cleaned = re.sub(r'^\d+[\.\)]\s*', '', cleaned, flags=re.MULTILINE)
            if opt_urls:
                cleaned = re.sub(r'https?://\S+', '', cleaned)
            if opt_special_chars:
                cleaned = re.sub(r'[^\w\s가-힣]', '', cleaned)
            if opt_merge_lines:
                cleaned = " ".join(cleaned.splitlines())
                cleaned = " ".join(cleaned.split())

            cleaned = cleaned.strip()
            _render_result(clean_input, cleaned)
        else:
            st.warning("텍스트를 입력해주세요.")
