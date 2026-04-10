import streamlit as st
import os
import json
import random
from text_cleaner import render_text_cleaner

MENU_LIST_FILE = "menu_list.json"

def init_tools():
    """도구 모음 초기화 로직"""
    if not os.path.exists(MENU_LIST_FILE):
        default_menu = ["김치찌개", "제육볶음", "돈가스", "초밥", "짜장면", "삼겹살", "치킨", "햄버거", "파스타", "샌드위치"]
        with open(MENU_LIST_FILE, "w", encoding="utf-8") as f:
            json.dump(default_menu, f, ensure_ascii=False, indent=4)

def render_tools():
    """도구모음 UI 메인 렌더링"""
    st.title("🛠️ 도구모음")
    init_tools()

    selected_tool = st.selectbox(
        "사용할 도구를 선택하세요", 
        ["🧹 텍스트 클리너", "📝 글자수 카운터", "🍴 오늘 뭐 먹지?"]
    )
    st.markdown("---")

    if selected_tool == "🧹 텍스트 클리너":
        render_text_cleaner()

    elif selected_tool == "📝 글자수 카운터":
        st.subheader("📝 글자수 카운터")
        st.info("텍스트를 입력하면 단어수, 글자수, 예상 A4 페이지 수를 계산합니다.")
        
        input_text = st.text_area("분석할 텍스트를 입력하세요", height=300, placeholder="여기에 내용을 붙여넣으세요...")
        
        if st.button("분석하기", type="primary", use_container_width=True):
            if input_text:
                char_count_with_spaces = len(input_text)
                char_count_without_spaces = len(input_text.replace(" ", "").replace("\n", "").replace("\r", ""))
                word_count = len(input_text.split())
                a4_pages = char_count_with_spaces / 1500
                
                st.markdown("---")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("단어 수", f"{word_count}개")
                with col2:
                    st.metric("글자 수 (공백 포함)", f"{char_count_with_spaces}자")
                with col3:
                    st.metric("글자 수 (공백 제외)", f"{char_count_without_spaces}자")
                with col4:
                    st.metric("예상 A4 분량", f"{a4_pages:.2f}쪽")
                st.caption("※ A4 분량은 공백 포함 1,500자를 1쪽으로 계산한 결과입니다.")
            else:
                st.warning("텍스트를 입력해주세요.")

    elif selected_tool == "🍴 오늘 뭐 먹지?":
        st.subheader("🍴 오늘 뭐 먹지?")
        st.info("결정하기 힘들 때, 랜덤으로 메뉴를 추천해 드립니다!")
        
        if st.button("🎲 메뉴 추천받기", use_container_width=True):
            if os.path.exists(MENU_LIST_FILE):
                try:
                    with open(MENU_LIST_FILE, "r", encoding="utf-8") as f:
                        menu_list = json.load(f)
                    selected_menu = random.choice(menu_list)
                    st.balloons()
                    st.success(f"오늘의 추천 메뉴는 바로... **{selected_menu}** 입니다! 맛있게 드세요! 😋")
                except Exception as e:
                    st.error(f"메뉴를 불러오는 중 오류가 발생했습니다: {e}")
            else:
                st.error("menu_list.json 파일이 없습니다.")
