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
