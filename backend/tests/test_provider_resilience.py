from __future__ import annotations

import json

from app.analysis.failure_status import fallback_failed_status, safe_failure_code
from app.analysis.provider_resilience import (
    COACHING_FAILURES,
    EXTRACTION_FAILURES,
    evaluate_provider_resilience,
)


def test_provider_resilience_matrix_passes_and_preserves_output() -> None:
    report = evaluate_provider_resilience()

    assert report["passed"] is True, report["failures"]
    assert report["counts"]["cases"] == 15
    assert report["counts"]["passed"] == 15
    assert report["counts"]["preserved"] == 15
    assert report["metrics"]["case_pass_rate"] == 1.0
    assert report["metrics"]["deterministic_preservation_rate"] == 1.0


def test_provider_resilience_matrix_covers_required_failure_codes() -> None:
    report = evaluate_provider_resilience()
    model_statuses = {case["model_status"] for case in report["cases"]}
    coaching_statuses = {case["coaching_status"] for case in report["cases"]}

    for _, code in EXTRACTION_FAILURES:
        assert f"fallback_failed: {code}" in model_statuses
    for _, code in COACHING_FAILURES:
        assert f"fallback_failed: {code}" in coaching_statuses


def test_provider_resilience_report_excludes_documents_secrets_and_provider_bodies() -> None:
    report_text = json.dumps(evaluate_provider_resilience())

    assert "Built a Python FastAPI service" not in report_text
    assert "Python and SQL are required" not in report_text
    assert "synthetic-test-key" not in report_text
    assert "rate_limit" not in report_text
    assert "Unknown Provider Reference" not in report_text


def test_failure_status_allows_only_bounded_machine_codes() -> None:
    assert safe_failure_code("provider_timeout", fallback="provider_error") == "provider_timeout"
    assert fallback_failed_status(
        "coaching_http_429",
        fallback="coaching_provider_error",
    ) == "fallback_failed: coaching_http_429"

    assert safe_failure_code(
        "provider_timeout resume text should never be here",
        fallback="provider_error",
    ) == "provider_error"
    assert safe_failure_code(
        "../../secret",
        fallback="provider_error",
    ) == "provider_error"
    assert safe_failure_code("", fallback="provider_error") == "provider_error"
