import unittest

from app.settlement import calculate_settlement, parse_people


class SettlementTests(unittest.TestCase):
    def test_itemized_partial_and_all_participants(self):
        people = ["지송", "민수", "영희"]
        rows = [
            {"내용": "저녁", "결제자": "지송", "금액": 30000, "참여자": "전체"},
            {"내용": "택시", "결제자": "민수", "금액": 12000, "참여자": "지송, 민수"},
        ]

        result = calculate_settlement(people, rows)

        self.assertEqual(result.errors, [])
        self.assertEqual(
            result.summary_rows,
            [
                {"사람": "지송", "낸 금액": 30000, "부담 금액": 16000, "잔액": 14000},
                {"사람": "민수", "낸 금액": 12000, "부담 금액": 16000, "잔액": -4000},
                {"사람": "영희", "낸 금액": 0, "부담 금액": 10000, "잔액": -10000},
            ],
        )
        self.assertEqual(
            result.transfer_rows,
            [
                {"보내는 사람": "영희", "받는 사람": "지송", "금액": 10000},
                {"보내는 사람": "민수", "받는 사람": "지송", "금액": 4000},
            ],
        )

    def test_remainder_is_assigned_deterministically(self):
        people = ["A", "B", "C"]
        rows = [{"내용": "간식", "결제자": "A", "금액": 10000, "참여자": "전체"}]

        result = calculate_settlement(people, rows)

        self.assertEqual(result.errors, [])
        self.assertEqual([row["부담 금액"] for row in result.summary_rows], [3334, 3333, 3333])

    def test_invalid_rows_are_reported(self):
        people = parse_people("A, B")
        rows = [
            {"내용": "숙소", "결제자": "C", "금액": 20000, "참여자": "전체"},
            {"내용": "밥", "결제자": "A", "금액": -1, "참여자": "A"},
            {"내용": "카페", "결제자": "A", "금액": 5000, "참여자": "A, C"},
        ]

        result = calculate_settlement(people, rows)

        self.assertEqual(len(result.errors), 3)
        self.assertIn("결제자가 사람 목록에 없습니다", result.errors[0])
        self.assertIn("금액은 1원 이상의 정수", result.errors[1])
        self.assertIn("참여자가 사람 목록에 없습니다", result.errors[2])

    def test_empty_people_is_error(self):
        result = calculate_settlement([], [{"내용": "밥", "결제자": "A", "금액": 1000, "참여자": "전체"}])

        self.assertEqual(result.errors, ["사람 목록을 먼저 입력해주세요."])
        self.assertEqual(result.summary_rows, [])
        self.assertEqual(result.transfer_rows, [])


if __name__ == "__main__":
    unittest.main()

