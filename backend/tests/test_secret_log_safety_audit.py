from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "run_secret_log_safety_audit.py"
)
_MODULE_NAME = "secret_log_safety_audit"
_SPEC = importlib.util.spec_from_file_location(_MODULE_NAME, SCRIPT_PATH)
assert _SPEC and _SPEC.loader
_AUDIT = importlib.util.module_from_spec(_SPEC)
sys.modules[_MODULE_NAME] = _AUDIT
_SPEC.loader.exec_module(_AUDIT)


def test_tracked_tree_has_no_high_confidence_secrets_or_secret_files() -> None:
    report = _AUDIT.evaluate_secret_log_safety(include_history=False)

    assert report["passed"] is True, report["findings"]
    assert report["finding_count"] == 0
    assert report["tracked_files_scanned"] > 0


def test_scanner_reports_metadata_without_returning_secret_value() -> None:
    secret = "sk-" + "Z" * 28
    findings = _AUDIT._scan_lines(
        [f"OPENAI_API_KEY={secret}"],
        scope="unit_test",
        location="synthetic.txt",
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule == "openai_api_key"
    assert secret not in repr(finding)
    assert finding.location == "synthetic.txt"
    assert finding.line == 1
