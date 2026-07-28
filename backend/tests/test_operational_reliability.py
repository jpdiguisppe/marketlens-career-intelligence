from __future__ import annotations

import json

from app.analysis import analyze_smart_fit
from app.analysis.operational_reliability_policy import (
    evaluate_operational_reliability,
    load_operational_reliability_benchmark,
    validate_analysis_invariants,
)


RESUME_TEXT = """PROJECTS
Built a Python FastAPI service backed by PostgreSQL.
SKILLS
Python, SQL, FastAPI, PostgreSQL
"""

JOB_TEXT = """Backend Engineer
REQUIRED QUALIFICATIONS
Python and SQL are required.
PREFERRED QUALIFICATIONS
Docker is preferred.
RESPONSIBILITIES
Build reliable backend APIs.
"""


def test_operational_benchmark_has_required_coverage() -> None:
    benchmark = load_operational_reliability_benchmark()

    assert benchmark["runs_per_case"] >= 3
    assert len(benchmark["cases"]) >= 12
    assert len({case["sector"] for case in benchmark["cases"]}) >= 9
    assert sum(
        bool(case["check_disabled_provider_fallback"])
        for case in benchmark["cases"]
    ) >= 6


def test_operational_reliability_evaluation_passes_without_provider_calls() -> None:
    report = evaluate_operational_reliability()

    assert report["passed"] is True, report["failures"]
    assert report["metrics"]["case_pass_rate"] == 1.0
    assert report["metrics"]["stable_run_rate"] == 1.0
    assert report["metrics"]["invariant_pass_rate"] == 1.0
    assert report["metrics"]["fallback_preservation_rate"] == 1.0
    assert report["counts"]["failures"] == 0


def test_operational_report_never_contains_fixture_documents() -> None:
    report_text = json.dumps(evaluate_operational_reliability())

    assert "Built a Python FastAPI service backed by PostgreSQL" not in report_text
    assert "Active Secret clearance required" not in report_text
    assert "Docker experience is required" not in report_text


def test_invariant_checker_detects_duplicate_and_unsupported_output() -> None:
    analysis = analyze_smart_fit(
        resume_text=RESUME_TEXT,
        job_description=JOB_TEXT,
        use_model_assisted=False,
    )
    first_assessment = analysis.requirement_assessments[0]
    corrupted = analysis.model_copy(
        update={
            "requirement_assessments": [
                *analysis.requirement_assessments,
                first_assessment,
            ],
            "strong_matches": [*analysis.strong_matches, "Docker"],
        }
    )

    failures = validate_analysis_invariants(
        corrupted,
        case_id="corrupted-output",
        resume_text=RESUME_TEXT,
        job_description=JOB_TEXT,
    )
    checks = {failure["check"] for failure in failures}

    assert "duplicate_requirement_label" in checks
    assert "duplicate_grounded_requirement_identity" in checks
    assert "unsupported_or_missing_strong_match" in checks


def test_repeated_runs_return_one_complete_fingerprint_per_case() -> None:
    report = evaluate_operational_reliability()

    for case in report["cases"]:
        assert case["stable"] is True
        assert len(case["fingerprint"]) == 64
        assert case["latency_ms"]["minimum"] >= 0
        assert case["latency_ms"]["maximum"] >= case["latency_ms"]["minimum"]
        if case["fallback"] is not None:
            assert case["fallback"]["preserved"] is True
            assert case["fallback"]["analysis_status"].startswith("fallback_")
            assert case["fallback"]["coaching_status"].startswith("fallback_")
