import io
import unittest
import zipfile

from app.ai import (
    _extract_office_text,
    _format_chat_history_markdown,
    _postprocess_ai_result,
    format_krw_cost,
)


def _make_zip(entries: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, text in entries.items():
            zf.writestr(path, text)
    return buffer.getvalue()


class AiHelperTests(unittest.TestCase):
    def test_extract_pptx_text(self):
        data = _make_zip(
            {
                "ppt/slides/slide1.xml": "<slide><text>첫 슬라이드</text></slide>",
                "ppt/slides/slide2.xml": "<slide><text>둘째 슬라이드</text></slide>",
            }
        )

        self.assertIn("첫 슬라이드", _extract_office_text("deck.pptx", data))
        self.assertIn("둘째 슬라이드", _extract_office_text("deck.pptx", data))

    def test_extract_docx_text(self):
        data = _make_zip({"word/document.xml": "<document><text>문서 본문</text></document>"})

        self.assertEqual(_extract_office_text("note.docx", data), "문서 본문")

    def test_krw_cost_rounding(self):
        self.assertEqual(format_krw_cost(0.49), "₩0")
        self.assertEqual(format_krw_cost(0.5), "₩1")

    def test_postprocess_masks_names_and_expands_abbreviation_once(self):
        result = _postprocess_ai_result("환자명: 홍길동\n홍길동 환자는 HTN, HTN 병력이 있습니다.")

        self.assertNotIn("홍길동", result)
        self.assertIn("환자명: [이름 비공개]", result)
        self.assertEqual(result.count("HTN (Hypertension)"), 1)
        self.assertIn("HTN 병력", result)

    def test_format_chat_history_markdown(self):
        markdown = _format_chat_history_markdown(
            [{"q": "다음 계획?", "a": "추적 관찰"}, {"q": "", "a": "요약"}]
        )

        self.assertIn("## 대화 1", markdown)
        self.assertIn("**Q.** 다음 계획?", markdown)
        self.assertIn("**Q.** (질문 없음)", markdown)


if __name__ == "__main__":
    unittest.main()
