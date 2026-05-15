import json
import random
from datetime import timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from app.access_logger import clear_access_logs, get_access_logs
from app.ai import (
    _entry_cost_krw,
    _load_gemini_usage_logs,
    _parse_usage_time,
    format_krw_cost,
)
from app.auth import get_admin_password, is_authenticated, login_screen
from app.core_utils import get_now
from app.gcs_helper import get_bucket
from app.md_pdf import render_md_pdf_tool
from app.settlement import render_settlement_tool
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
        "id": "md_pdf",
        "label": "MD to PDF",
        "icon": "📄",
        "summary": "Markdown을 한글 서식이 살아 있는 PDF로 변환합니다.",
    },
    {
        "id": "counter",
        "label": "글자수 카운터",
        "icon": "📝",
        "summary": "글자 수, 단어 수, 예상 문서 분량을 빠르게 계산합니다.",
    },
    {
        "id": "settlement",
        "label": "정산 계산기",
        "icon": "💸",
        "summary": "항목별 지출을 입력해 최소 송금 목록을 계산합니다.",
    },
    {
        "id": "ai_costs",
        "label": "AI 예상비용",
        "icon": "📊",
        "summary": "Gemini 사용량과 예상 비용을 날짜별로 확인합니다.",
    },
    {
        "id": "storage_status",
        "label": "저장소 상태",
        "icon": "🗄️",
        "summary": "GCS 버킷 상태와 저장된 객체 수를 확인합니다.",
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

    for row_start in range(0, len(TOOLS), 2):
        row_tools = TOOLS[row_start : row_start + 2]
        row_columns = st.columns(len(row_tools))
        for column, tool in zip(row_columns, row_tools):
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
                st.caption(tool["summary"])

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

            row1_col1, row1_col2 = st.columns(2)
            with row1_col1:
                st.metric("단어 수", f"{word_count}개")
            with row1_col2:
                st.metric("글자 수 (공백 포함)", f"{char_count_with_spaces}자")

            row2_col1, row2_col2 = st.columns(2)
            with row2_col1:
                st.metric("글자 수 (공백 제외)", f"{char_count_without_spaces}자")
            with row2_col2:
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


def _build_ai_cost_rows(logs: list[dict]) -> tuple[list[dict], list[dict]]:
    detail_rows = []
    daily_totals: dict[str, dict] = {}

    for entry in logs:
        entry_time = _parse_usage_time(entry.get("time", ""))
        if entry_time is None:
            continue

        cost_krw = _entry_cost_krw(entry)
        input_tokens = int(entry.get("input_tokens") or 0)
        output_tokens = int(entry.get("output_tokens") or 0)
        total_tokens = int(entry.get("total_tokens") or input_tokens + output_tokens)
        date_key = entry_time.strftime("%Y-%m-%d")

        detail_rows.append(
            {
                "시간": entry_time.strftime("%Y-%m-%d %H:%M"),
                "날짜": date_key,
                "모델": entry.get("model", ""),
                "입력 토큰": input_tokens,
                "출력 토큰": output_tokens,
                "전체 토큰": total_tokens,
                "예상 비용(KRW)": round(cost_krw, 2),
                "예상 비용(USD)": float(entry.get("estimated_cost_usd") or 0),
            }
        )

        daily = daily_totals.setdefault(
            date_key,
            {
                "날짜": date_key,
                "요청 수": 0,
                "입력 토큰": 0,
                "출력 토큰": 0,
                "전체 토큰": 0,
                "예상 비용(KRW)": 0.0,
            },
        )
        daily["요청 수"] += 1
        daily["입력 토큰"] += input_tokens
        daily["출력 토큰"] += output_tokens
        daily["전체 토큰"] += total_tokens
        daily["예상 비용(KRW)"] += cost_krw

    daily_rows = sorted(daily_totals.values(), key=lambda row: row["날짜"])
    detail_rows.sort(key=lambda row: row["시간"], reverse=True)
    for row in daily_rows:
        row["예상 비용(KRW)"] = round(row["예상 비용(KRW)"], 2)
    return daily_rows, detail_rows


def _render_ai_costs_tool():
    st.info("Gemini usage 로그를 기준으로 앱 내부 예상 비용을 날짜별로 분석합니다.")

    try:
        logs = _load_gemini_usage_logs()
    except Exception as exc:
        st.error(f"Gemini 사용량 로그를 불러오지 못했습니다: {exc}")
        return

    if not logs:
        st.write("Gemini 사용량 로그가 없습니다.")
        return

    period = st.radio(
        "분석 범위",
        options=["최근 7일", "최근 30일", "전체"],
        index=1,
        horizontal=True,
        key="ai_cost_period",
    )
    cutoff = None
    if period == "최근 7일":
        cutoff = get_now() - timedelta(days=7)
    elif period == "최근 30일":
        cutoff = get_now() - timedelta(days=30)

    filtered_logs = []
    for entry in logs:
        entry_time = _parse_usage_time(entry.get("time", ""))
        if entry_time is None:
            continue
        if cutoff is not None and entry_time < cutoff:
            continue
        filtered_logs.append(entry)

    daily_rows, detail_rows = _build_ai_cost_rows(filtered_logs)
    if not daily_rows:
        st.write("선택한 기간의 Gemini 사용량 로그가 없습니다.")
        return

    total_cost = sum(row["예상 비용(KRW)"] for row in daily_rows)
    total_requests = sum(row["요청 수"] for row in daily_rows)
    total_tokens = sum(row["전체 토큰"] for row in daily_rows)
    avg_cost = total_cost / total_requests if total_requests else 0

    col_cost, col_requests, col_tokens, col_avg = st.columns(4)
    with col_cost:
        st.metric("총 예상 비용", format_krw_cost(total_cost))
    with col_requests:
        st.metric("요청 수", f"{total_requests:,}회")
    with col_tokens:
        st.metric("전체 토큰", f"{total_tokens:,}")
    with col_avg:
        st.metric("요청당 평균", format_krw_cost(avg_cost))

    daily_df = pd.DataFrame(daily_rows)
    chart_df = daily_df.set_index("날짜")[["예상 비용(KRW)"]]
    st.bar_chart(chart_df, use_container_width=True)

    detail_df = pd.DataFrame(detail_rows)
    csv_col_daily, csv_col_detail = st.columns(2)
    with csv_col_daily:
        csv_bytes = daily_df.to_csv(index=False, encoding="utf-8-sig").encode(
            "utf-8-sig"
        )
        st.download_button(
            "날짜별 비용 CSV 다운로드",
            data=csv_bytes,
            file_name=f"ai_costs_daily_{get_now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with csv_col_detail:
        detail_csv_bytes = detail_df.to_csv(index=False, encoding="utf-8-sig").encode(
            "utf-8-sig"
        )
        st.download_button(
            "상세 로그 CSV 다운로드",
            data=detail_csv_bytes,
            file_name=f"ai_costs_detail_{get_now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.dataframe(daily_df, use_container_width=True, hide_index=True)

    with st.expander("상세 로그 보기"):
        st.dataframe(detail_df, use_container_width=True, hide_index=True)


def _render_storage_status_tool():
    if not is_authenticated():
        login_screen()
        return

    st.info("현재 Cloud Run 앱이 직접 사용하는 GCS 버킷 상태를 확인합니다.")
    bucket = get_bucket()
    st.metric("Backend", "GCS")
    try:
        remote_count = sum(1 for blob in bucket.list_blobs() if not blob.name.endswith("/"))
        st.metric("GCS 파일", f"{remote_count:,}개")
    except Exception as exc:
        st.warning(f"GCS 파일 수를 확인하지 못했습니다: {exc}")


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
    elif selected_tool["id"] == "md_pdf":
        render_md_pdf_tool()
    elif selected_tool["id"] == "settlement":
        render_settlement_tool()
    elif selected_tool["id"] == "ai_costs":
        _render_ai_costs_tool()
    elif selected_tool["id"] == "storage_status":
        _render_storage_status_tool()
    elif selected_tool["id"] == "menu_picker":
        _render_menu_picker_tool()
    elif selected_tool["id"] == "access_logs":
        _render_access_logs_tool()
