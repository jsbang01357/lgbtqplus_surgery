import unittest

from app.settlement import calculate_settlement, parse_people


class SettlementTests(unittest.TestCase):
    def test_itemized_partial_and_all_participants(self):
        people = ["지송", "민수", "영희"]
        rows = [
            {"항목": "저녁", "돈낸사람": "지송", "비용": 30000, "n빵할사람": ""},
            {"항목": "택시", "돈낸사람": "민수", "비용": 12000, "n빵할사람": "지송, 민수"},
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
        rows = [{"항목": "간식", "돈낸사람": "A", "비용": 10000, "n빵할사람": ""}]

        result = calculate_settlement(people, rows)

        self.assertEqual(result.errors, [])
        self.assertEqual([row["부담 금액"] for row in result.summary_rows], [3334, 3333, 3333])

    def test_invalid_rows_are_reported(self):
        people = parse_people("A, B")
        rows = [
            {"항목": "숙소", "돈낸사람": "C", "비용": 20000, "n빵할사람": ""},
            {"항목": "밥", "돈낸사람": "A", "비용": -1, "n빵할사람": "A"},
            {"항목": "카페", "돈낸사람": "A", "비용": 5000, "n빵할사람": "A, C"},
        ]

        result = calculate_settlement(people, rows)

        self.assertEqual(len(result.errors), 3)
        self.assertIn("돈낸사람이 사람 목록에 없습니다", result.errors[0])
        self.assertIn("비용은 1원 이상의 정수", result.errors[1])
        self.assertIn("n빵할사람이 사람 목록에 없습니다", result.errors[2])

    def test_item_is_optional_but_payer_and_amount_are_required(self):
        people = parse_people("A, B")
        rows = [
            {"돈낸사람": "", "비용": 1000, "n빵할사람": "A", "항목": ""},
            {"돈낸사람": "A", "비용": None, "n빵할사람": "", "항목": ""},
            {"돈낸사람": "A", "비용": 2000, "n빵할사람": "", "항목": ""},
        ]

        result = calculate_settlement(people, rows)

        self.assertEqual(len(result.errors), 2)
        self.assertIn("돈낸사람은 꼭 입력", result.errors[0])
        self.assertIn("비용은 1원 이상의 정수", result.errors[1])
        self.assertEqual(
            result.summary_rows,
            [
                {"사람": "A", "낸 금액": 2000, "부담 금액": 1000, "잔액": 1000},
                {"사람": "B", "낸 금액": 0, "부담 금액": 1000, "잔액": -1000},
            ],
        )

    def test_empty_people_is_error(self):
        result = calculate_settlement([], [{"항목": "밥", "돈낸사람": "A", "비용": 1000, "n빵할사람": ""}])

        self.assertEqual(result.errors, ["사람 목록을 먼저 입력해주세요."])
        self.assertEqual(result.summary_rows, [])
        self.assertEqual(result.transfer_rows, [])


if __name__ == "__main__":
    unittest.main()
