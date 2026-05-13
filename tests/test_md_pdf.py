import unittest

from app.md_pdf import decode_markdown_upload


class FakeUpload:
    name = "note.md"
    size = 15

    def getvalue(self):
        return "# 제목\n\n- 항목".encode("utf-8")


class MarkdownPdfTests(unittest.TestCase):
    def test_decode_markdown_upload(self):
        self.assertEqual(decode_markdown_upload(FakeUpload()), "# 제목\n\n- 항목")


if __name__ == "__main__":
    unittest.main()

