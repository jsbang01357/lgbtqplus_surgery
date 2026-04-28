import json
import random
from pathlib import Path

import pandas as pd
import streamlit as st

from app.access_logger import clear_access_logs, get_access_logs
from app.auth import get_admin_password, is_authenticated, login_screen
from app.text_cleaner import render_text_cleaner

BASE_DIR = Path(__file__).resolve().parent.parent
MENU_JSON_PATH = BASE_DIR / "data" / "menu_list.json"

TOOLS = [
    {
        "id": "text_cleaner",
        "label": "텍스트 클리너",
        "icon": "🧹",
        "summary": "마크다운과 복붙 텍스트를 읽기 좋은 형태로 다듬습니다.",
    },
    {
        "id": "counter",
        "label": "글자수 카운터",
        "icon": "📝",
        "summary": "글자 수, 단어 수, 예상 문서 분량을 빠르게 계산합니다.",
    },
    {
        "id": "menu_picker",
        "label": "오늘 뭐 먹지?",
        "icon": "🍴",
        "summary": "고민할 때 바로 결정을 내려주는 랜덤 메뉴 추천기입니다.",
    },
    {
        "id": "access_logs",
        "label": "접속 기록 관리",
        "icon": "🔐",
        "summary": "최근 접속 기록을 확인하고 정리합니다.",
    },
]
TOOL_INDEX = {tool["id"]: tool for tool in TOOLS}


def init_tools():
    """도구 모음 초기화 로직"""
    if not MENU_JSON_PATH.exists():
        default_menu = [
            "김치찌개",
            "제육볶음",
            "돈가스",
            "초밥",
            "짜장면",
            "삼겹살",
            "치킨",
            "햄버거",
            "파스타",
            "샌드위치",
        ]
        MENU_JSON_PATH.write_text(
            json.dumps(default_menu, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )


def _select_tool(tool_id: str):
    if st.session_state.get("selected_tool_id") == tool_id:
        return
    st.session_state.selected_tool_id = tool_id
    st.rerun()



def _render_tool_picker():
    if "selected_tool_id" not in st.session_state:
        st.session_state.selected_tool_id = TOOLS[0]["id"]

    st.markdown(
        """
        <div class="section-block section-block--spacious">
            <p class="section-block__eyebrow">Tools</p>
            <h2 class="section-block__title">도구 선택</h2>
            <p class="section-block__body">
                지금 하려는 작업에 맞는 도구를 고르면 바로 아래에서 실행할 수 있습니다.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    columns = st.columns(len(TOOLS))
    for column, tool in zip(columns, TOOLS):
        button_type = (
            "primary" if st.session_state.selected_tool_id == tool["id"] else "secondary"
        )
        with column:
            if st.button(
                f"{tool['icon']} {tool['label']}",
                key=f"tool_pick_{tool['id']}",
                type=button_type,
                use_container_width=True,
            ):
                _select_tool(tool["id"])
        column.caption(tool["summary"])

    return TOOL_INDEX[st.session_state.selected_tool_id]


def _render_tool_header(tool):
    st.markdown(
        f"""
        <div class="section-block section-block--spacious">
            <div class="tool-chip">{tool["icon"]} {tool["label"]}</div>
            <h2 class="section-block__title">{tool["label"]}</h2>
            <p class="section-block__body">{tool["summary"]}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_counter_tool():
    st.info("텍스트를 넣으면 단어 수, 글자 수, 예상 A4 분량을 정리해서 보여줍니다.")

    input_text = st.text_area(
        "분석할 텍스트를 입력하세요",
        height=300,
        placeholder="여기에 내용을 붙여넣으세요...",
        key="tool_counter_input",
    )

    if st.button("분석하기", type="primary", use_container_width=True):
        if input_text:
            char_count_with_spaces = len(input_text)
            char_count_without_spaces = len(
                input_text.replace(" ", "").replace("\n", "").replace("\r", "")
            )
            word_count = len(input_text.split())
            a4_pages = char_count_with_spaces / 1500

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("단어 수", f"{word_count}개")
            with col2:
                st.metric("글자 수 (공백 포함)", f"{char_count_with_spaces}자")
            with col3:
                st.metric("글자 수 (공백 제외)", f"{char_count_without_spaces}자")
            with col4:
                st.metric("예상 A4 분량", f"{a4_pages:.2f}쪽")

            st.caption("공백 포함 1,500자를 A4 1쪽으로 계산했습니다.")
        else:
            st.warning("텍스트를 입력해주세요.")


def _render_menu_picker_tool():
    st.info("고민을 오래 끌지 않도록 등록된 메뉴 중 하나를 바로 골라드립니다.")

    if st.button("메뉴 추천받기", type="primary", use_container_width=True):
        if MENU_JSON_PATH.exists():
            try:
                menu_list = json.loads(MENU_JSON_PATH.read_text(encoding="utf-8"))
                selected_menu = random.choice(menu_list)
                st.success(f"오늘의 메뉴는 **{selected_menu}** 어떠세요?")
                st.caption("조금 더 단단한 결정이 필요하면 한 번 더 눌러도 됩니다.")
            except Exception as exc:
                st.error(f"메뉴를 불러오는 중 오류가 발생했습니다: {exc}")
        else:
            st.error("menu_list.json 파일이 없습니다.")


def _render_access_logs_tool():
    if not is_authenticated():
        login_screen()
        return

    st.info("최근 500개의 접속 기록을 표로 확인하고, 필요하면 관리자 비밀번호로 초기화할 수 있습니다.")

    logs = get_access_logs()
    if not logs:
        st.write("접속 기록이 없습니다.")
        return

    df = pd.DataFrame(logs)
    df.columns = ["접속 시간", "IP 주소", "브라우저 정보"]
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown(
        """
        <div class="section-block section-block--spacious section-block--danger">
            <p class="section-block__eyebrow">Danger Zone</p>
            <h3 class="section-block__title">로그 초기화</h3>
            <p class="section-block__body">
                전체 기록을 지우기 전에 관리자 비밀번호를 한 번 더 확인합니다.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_pwd, col_del = st.columns([3, 1], vertical_alignment="bottom")
    with col_pwd:
        pwd_input = st.text_input(
            "관리자 비밀번호를 다시 입력하세요",
            type="password",
            key="admin_pwd_check",
        )

    with col_del:
        if st.button(
            "전체 로그 삭제",
            type="primary",
            use_container_width=True,
            key="danger_clear_logs",
        ):
            correct_pwd = get_admin_password()

            if not correct_pwd:
                st.error("관리자 비밀번호가 설정되지 않았습니다.")
            elif pwd_input == correct_pwd:
                clear_access_logs()
                st.toast("✅ 모든 접속 기록이 삭제되었습니다.")
                st.rerun()
            else:
                st.error("❌ 비밀번호가 올바르지 않습니다.")


def render_tools():
    """도구모음 UI 메인 렌더링"""
    init_tools()
    selected_tool = _render_tool_picker()
    _render_tool_header(selected_tool)

    if selected_tool["id"] == "text_cleaner":
        render_text_cleaner()
    elif selected_tool["id"] == "counter":
        _render_counter_tool()
    elif selected_tool["id"] == "menu_picker":
        _render_menu_picker_tool()
    elif selected_tool["id"] == "access_logs":
        _render_access_logs_tool()
