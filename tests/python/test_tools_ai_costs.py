import unittest

from app.tools import _build_ai_cost_rows


class AiCostToolTests(unittest.TestCase):
    def test_build_ai_cost_rows_groups_by_date(self):
        logs = [
            {
                "time": "2026-05-14T09:00:00+09:00",
                "model": "gemini-test",
                "input_tokens": 100,
                "output_tokens": 20,
                "total_tokens": 120,
                "estimated_cost_krw": 1.2,
                "estimated_cost_usd": 0.001,
            },
            {
                "time": "2026-05-14T10:00:00+09:00",
                "model": "gemini-test",
                "input_tokens": 50,
                "output_tokens": 30,
                "total_tokens": 80,
                "estimated_cost_krw": 2.3,
                "estimated_cost_usd": 0.002,
            },
            {
                "time": "2026-05-13T10:00:00+09:00",
                "model": "gemini-test",
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "estimated_cost_krw": 0.5,
                "estimated_cost_usd": 0.0005,
            },
            {"time": "not-a-date", "estimated_cost_krw": 1000},
        ]

        daily_rows, detail_rows = _build_ai_cost_rows(logs)

        self.assertEqual(
            daily_rows,
            [
                {
                    "날짜": "2026-05-13",
                    "요청 수": 1,
                    "입력 토큰": 10,
                    "출력 토큰": 5,
                    "전체 토큰": 15,
                    "예상 비용(KRW)": 0.5,
                },
                {
                    "날짜": "2026-05-14",
                    "요청 수": 2,
                    "입력 토큰": 150,
                    "출력 토큰": 50,
                    "전체 토큰": 200,
                    "예상 비용(KRW)": 3.5,
                },
            ],
        )
        self.assertEqual(len(detail_rows), 3)
        self.assertEqual(detail_rows[0]["시간"], "2026-05-14 10:00")


if __name__ == "__main__":
    unittest.main()
