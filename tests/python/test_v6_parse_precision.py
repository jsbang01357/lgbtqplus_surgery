import unittest

from app.v6_bridge import parser_bridge_available, run_v6_parse


class V6ParsePrecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        available, reason = parser_bridge_available()
        if not available:
            raise unittest.SkipTest(reason)

    def test_mixed_blob_splits_into_note_lab_and_imaging(self):
        sample = """Progress Note
2026-05-16
Subjective
Patient feels better today.
Assessment
Hyperglycemia improving.
Plan
Continue monitoring.
[Chemistry]
Glucose  145  mg/dL  70~99
CRP  3.2  mg/dL  0~0.5
CT Abdomen
Findings: mild fatty liver.
Impression: no acute abnormality.
"""
        result = run_v6_parse(patient_id="patient_001", raw_text=sample)
        kinds = [document["kind"] for document in result["documents"]]
        relative_paths = [entry["relativePath"] for entry in result["manifest"]]

        self.assertEqual(kinds, ["note", "lab", "imaging"])
        self.assertEqual(
            relative_paths,
            [
                "workspace/patient_001/notes/2026-05-16_progress_note.md",
                "workspace/patient_001/labs/2026-05-16_chemistry.csv",
                "workspace/patient_001/imaging/2026-05-16_ct_abdomen.md",
            ],
        )

    def test_lab_panel_is_not_split_into_multiple_documents(self):
        sample = """[Chemistry]
Glucose  145  mg/dL  70~99
CRP  3.2  mg/dL  0~0.5
HbA1c  7.4  %  4.0~6.0
"""
        result = run_v6_parse(patient_id="patient_001", raw_text=sample)

        self.assertEqual(len(result["documents"]), 1)
        self.assertEqual(result["documents"][0]["kind"], "lab")
        self.assertEqual(result["documents"][0]["extra"]["rowCount"], 3)


if __name__ == "__main__":
    unittest.main()
