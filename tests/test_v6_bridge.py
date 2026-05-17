import unittest
from unittest.mock import MagicMock, patch

from app.v6_bridge import ParserBridgeError, parser_bridge_available, run_v6_parse


class V6BridgeTests(unittest.TestCase):
    def test_bridge_reports_missing_node(self):
        with patch("app.v6_bridge.shutil.which", return_value=None):
            ok, reason = parser_bridge_available()
        self.assertFalse(ok)
        self.assertIn("node runtime", reason)

    def test_run_v6_parse_raises_on_nonzero_exit(self):
        with patch("app.v6_bridge.parser_bridge_available", return_value=(True, "")):
            with patch("app.v6_bridge.subprocess.run", return_value=MagicMock(returncode=1, stderr="boom", stdout="")):
                with self.assertRaises(ParserBridgeError):
                    run_v6_parse(patient_id="patient_001", raw_text="sample")

    def test_run_v6_parse_returns_parsed_json(self):
        stdout = '{"ok": true, "documents": [{"kind": "unknown"}], "manifest": []}'
        with patch("app.v6_bridge.parser_bridge_available", return_value=(True, "")):
            with patch("app.v6_bridge.subprocess.run", return_value=MagicMock(returncode=0, stderr="", stdout=stdout)):
                result = run_v6_parse(patient_id="patient_001", raw_text="sample")
        self.assertTrue(result["ok"])
        self.assertEqual(result["documents"][0]["kind"], "unknown")


if __name__ == "__main__":
    unittest.main()
