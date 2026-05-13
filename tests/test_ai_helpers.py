import io
import unittest
import zipfile

from app.ai import _extract_office_text, format_krw_cost


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


if __name__ == "__main__":
    unittest.main()
