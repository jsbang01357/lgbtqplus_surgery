from dataclasses import dataclass
from typing import Iterable


@dataclass
class SettlementResult:
    summary_rows: list[dict]
    transfer_rows: list[dict]
    errors: list[str]


def parse_people(raw_people: str) -> list[str]:
    normalized = raw_people.replace(",", "\n")
    people = []
    seen = set()
    for part in normalized.splitlines():
        name = part.strip()
        if not name or name in seen:
            continue
        people.append(name)
        seen.add(name)
    return people


def parse_participants(raw_value: str, people: list[str]) -> list[str]:
    value = str(raw_value or "").strip()
    if not value or value == "전체":
        return people[:]

    normalized = value.replace(",", "\n")
    participants = []
    seen = set()
    for part in normalized.splitlines():
        name = part.strip()
        if not name or name in seen:
            continue
        participants.append(name)
        seen.add(name)
    return participants


def _coerce_amount(value) -> int | None:
    if value is None:
        return None
    try:
        amount = int(str(value).replace(",", "").strip())
    except ValueError:
        return None
    return amount if amount > 0 else None


def _split_evenly(amount: int, participants: list[str]) -> dict[str, int]:
    base = amount // len(participants)
    remainder = amount % len(participants)
    shares = {}
    for idx, person in enumerate(participants):
        shares[person] = base + (1 if idx < remainder else 0)
    return shares


def calculate_settlement(people: list[str], expense_rows: Iterable[dict]) -> SettlementResult:
    errors = []
    paid = {person: 0 for person in people}
    owed = {person: 0 for person in people}

    if not people:
        return SettlementResult([], [], ["사람 목록을 먼저 입력해주세요."])

    for row_index, row in enumerate(expense_rows, start=1):
        title = str(row.get("내용", "") or "").strip()
        payer = str(row.get("결제자", "") or "").strip()
        amount = _coerce_amount(row.get("금액"))
        participants = parse_participants(str(row.get("참여자", "") or ""), people)

        if not title and not payer and amount is None and not str(row.get("참여자", "") or "").strip():
            continue
        if payer not in people:
            errors.append(f"{row_index}행 결제자가 사람 목록에 없습니다: {payer or '(비어 있음)'}")
            continue
        if amount is None:
            errors.append(f"{row_index}행 금액은 1원 이상의 정수여야 합니다.")
            continue
        unknown = [person for person in participants if person not in people]
        if unknown:
            errors.append(f"{row_index}행 참여자가 사람 목록에 없습니다: {', '.join(unknown)}")
            continue
        if not participants:
            errors.append(f"{row_index}행 참여자가 비어 있습니다.")
            continue

        paid[payer] += amount
        for person, share in _split_evenly(amount, participants).items():
            owed[person] += share

    balances = {person: paid[person] - owed[person] for person in people}
    debtors = [[person, -amount] for person, amount in balances.items() if amount < 0]
    creditors = [[person, amount] for person, amount in balances.items() if amount > 0]
    debtors.sort(key=lambda item: item[1], reverse=True)
    creditors.sort(key=lambda item: item[1], reverse=True)

    transfer_rows = []
    debtor_idx = 0
    creditor_idx = 0
    while debtor_idx < len(debtors) and creditor_idx < len(creditors):
        debtor, debt = debtors[debtor_idx]
        creditor, credit = creditors[creditor_idx]
        amount = min(debt, credit)
        if amount > 0:
            transfer_rows.append({"보내는 사람": debtor, "받는 사람": creditor, "금액": amount})
        debtors[debtor_idx][1] -= amount
        creditors[creditor_idx][1] -= amount
        if debtors[debtor_idx][1] == 0:
            debtor_idx += 1
        if creditors[creditor_idx][1] == 0:
            creditor_idx += 1

    summary_rows = [
        {
            "사람": person,
            "낸 금액": paid[person],
            "부담 금액": owed[person],
            "잔액": balances[person],
        }
        for person in people
    ]
    return SettlementResult(summary_rows, transfer_rows, errors)


def render_settlement_tool():
    import pandas as pd
    import streamlit as st

    st.info("사람별 지출 항목을 입력하면 균등 분할 기준으로 최소 송금 목록을 계산합니다.")

    people_raw = st.text_area(
        "사람 목록",
        height=120,
        placeholder="예: 지송, 민수, 영희\n또는 한 줄에 한 명씩 입력",
        key="settlement_people",
    )
    people = parse_people(people_raw)

    default_rows = pd.DataFrame(
        [
            {"내용": "", "결제자": "", "금액": None, "참여자": "전체"},
        ]
    )
    edited = st.data_editor(
        default_rows,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "내용": st.column_config.TextColumn("내용", help="예: 숙소, 저녁, 택시"),
            "결제자": st.column_config.TextColumn("결제자", help="사람 목록에 있는 이름"),
            "금액": st.column_config.NumberColumn("금액", min_value=1, step=100, format="%d"),
            "참여자": st.column_config.TextColumn("참여자", help="전체 또는 이름, 이름"),
        },
        key="settlement_expenses",
    )

    if st.button("정산 계산하기", type="primary", use_container_width=True):
        rows = edited.to_dict("records")
        result = calculate_settlement(people, rows)
        st.session_state.settlement_result = result

    result = st.session_state.get("settlement_result")
    if not result:
        return

    if result.errors:
        for error in result.errors:
            st.warning(error)

    if result.summary_rows:
        st.markdown("#### 사람별 정산")
        st.dataframe(pd.DataFrame(result.summary_rows), use_container_width=True, hide_index=True)

    st.markdown("#### 최소 송금")
    if result.transfer_rows:
        st.dataframe(pd.DataFrame(result.transfer_rows), use_container_width=True, hide_index=True)
        for transfer in result.transfer_rows:
            st.write(
                f"{transfer['보내는 사람']} → {transfer['받는 사람']}: {transfer['금액']:,}원"
            )
    elif result.summary_rows and not result.errors:
        st.success("추가 송금이 필요 없습니다.")
