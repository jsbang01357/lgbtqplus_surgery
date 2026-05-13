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
        title = str(row.get("항목", row.get("내용", "")) or "").strip()
        payer = str(row.get("돈낸사람", row.get("결제자", "")) or "").strip()
        raw_amount = row.get("비용", row.get("금액"))
        raw_participants = str(row.get("n빵할사람", row.get("참여자", "")) or "").strip()
        amount = _coerce_amount(raw_amount)
        participants = parse_participants(raw_participants, people)

        if not title and not payer and amount is None and not raw_participants:
            continue
        if not payer:
            errors.append(f"{row_index}행 돈낸사람은 꼭 입력해야 합니다.")
            continue
        if payer not in people:
            errors.append(f"{row_index}행 돈낸사람이 사람 목록에 없습니다: {payer}")
            continue
        if amount is None:
            errors.append(f"{row_index}행 비용은 1원 이상의 정수여야 합니다.")
            continue
        unknown = [person for person in participants if person not in people]
        if unknown:
            errors.append(f"{row_index}행 n빵할사람이 사람 목록에 없습니다: {', '.join(unknown)}")
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

    st.info("사람 목록을 입력한 뒤 지출 행을 추가하면 n빵 기준으로 누가 누구에게 얼마를 보내면 되는지 계산합니다.")

    people_raw = st.text_input(
        "사람",
        placeholder="예: 지송, 지송2, 지송3",
        key="settlement_people",
    )
    people = parse_people(people_raw)

    default_rows = pd.DataFrame(
        [
            {"돈낸사람": "", "비용": None, "n빵할사람": "", "항목": ""},
        ]
    )
    edited = st.data_editor(
        default_rows,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "돈낸사람": st.column_config.TextColumn("돈낸사람", help="사람 목록에 있는 이름. 필수"),
            "비용": st.column_config.NumberColumn("비용", min_value=1, step=100, format="%d", help="필수"),
            "n빵할사람": st.column_config.TextColumn("n빵할사람", help="비우면 전체 n빵. 여러 명은 쉼표로 구분"),
            "항목": st.column_config.TextColumn("항목", help="예: 숙소, 저녁, 택시. 생략 가능"),
        },
        key="settlement_expenses",
    )
    st.caption("n빵할사람은 비워두면 전체 n빵으로 계산합니다. 여러 명은 `, `로 구분하세요.")

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
        st.markdown("#### 사람별 잔액")
        for row in result.summary_rows:
            balance = row["잔액"]
            if balance > 0:
                st.write(
                    f"- {row['사람']}: {row['낸 금액']:,}원 냄 / {row['부담 금액']:,}원 부담 → {balance:,}원 받을 예정"
                )
            elif balance < 0:
                st.write(
                    f"- {row['사람']}: {row['낸 금액']:,}원 냄 / {row['부담 금액']:,}원 부담 → {-balance:,}원 보낼 예정"
                )
            else:
                st.write(
                    f"- {row['사람']}: {row['낸 금액']:,}원 냄 / {row['부담 금액']:,}원 부담 → 정산 완료"
                )

    st.markdown("#### 최소 송금")
    if result.transfer_rows:
        for transfer in result.transfer_rows:
            st.write(
                f"- {transfer['보내는 사람']} → {transfer['받는 사람']}: {transfer['금액']:,}원"
            )
    elif result.summary_rows and not result.errors:
        st.success("추가 송금이 필요 없습니다.")
