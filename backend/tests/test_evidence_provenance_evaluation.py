from app.analysis.provenance_evaluation import (
    evaluate_evidence_provenance,
    format_evidence_provenance_report,
)


def test_evidence_provenance_evaluation_passes() -> None:
    report = evaluate_evidence_provenance()

    assert report["passed"], format_evidence_provenance_report(report)
    assert report["version"] == "8c.1"
    assert report["counts"]["cases"] >= 10
    assert report["counts"]["critical_cases"] >= 5
    assert report["counts"]["scored_requirements"] > 0
    assert report["metrics"]["job_grounding_rate"] == 1.0
    assert report["metrics"]["resume_grounding_rate"] == 1.0
    assert report["metrics"]["provenance_coverage_rate"] == 1.0
    assert report["metrics"]["strong_match_direct_evidence_rate"] == 1.0
    assert report["metrics"]["gap_required_signal_rate"] == 1.0
    assert report["metrics"]["hard_requirement_grounding_rate"] == 1.0
    assert report["metrics"]["critical_case_pass_rate"] == 1.0


def test_evidence_provenance_report_is_readable() -> None:
    report = evaluate_evidence_provenance()
    formatted = format_evidence_provenance_report(report)

    assert "Smart Fit Evidence Provenance Evaluation" in formatted
    assert "job_grounding_rate" in formatted
    assert "strong_match_direct_evidence_rate" in formatted
    assert "gap_required_signal_rate" in formatted
