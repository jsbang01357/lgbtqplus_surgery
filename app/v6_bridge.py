from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
PARSER_CORE_DIR = REPO_ROOT / "parser-core"
PARSER_CLI_PATH = PARSER_CORE_DIR / "dist" / "cli.js"


class ParserBridgeError(RuntimeError):
    pass


def parser_bridge_available() -> tuple[bool, str]:
    node_path = shutil.which("node")
    if not node_path:
        return False, "node runtime이 없습니다."
    if not PARSER_CLI_PATH.exists():
        return False, f"parser CLI build가 없습니다: {PARSER_CLI_PATH}"
    return True, ""


def run_v6_parse(*, patient_id: str, raw_text: str, source: str = "emr", source_path: str = "") -> dict[str, Any]:
    available, reason = parser_bridge_available()
    if not available:
        raise ParserBridgeError(reason)

    payload = {
        "artifact": {
            "artifactId": "api-upload",
            "patientId": patient_id,
            "source": source,
            "sourcePath": source_path,
            "rawText": raw_text,
        }
    }

    result = subprocess.run(
        ["node", str(PARSER_CLI_PATH)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
        check=False,
    )

    if result.returncode != 0:
        raise ParserBridgeError(result.stderr.strip() or "v6 parser 실행에 실패했습니다.")

    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ParserBridgeError(f"v6 parser 응답 JSON 파싱 실패: {exc}") from exc

    if not isinstance(parsed, dict) or not parsed.get("ok"):
        raise ParserBridgeError("v6 parser 응답 형식이 올바르지 않습니다.")

    return parsed
