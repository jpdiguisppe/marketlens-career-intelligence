import json
import re
from pathlib import Path
from typing import Any

import pytest

from app.analysis.service import analyze_smart_fit

FIXTURES = Path(__file__).parent / "fixtures"
EVALUATION_CASES_PATH = FIXTURES / "smart_fit_evaluation_cases.json"

EMAIL_PATTERN = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")


def _load_cases() -> list[dict[str, Any]]:
    return json.loads(EVALUATION_CASES_PATH.read_text(encoding="utf-8"))


EVALUATION_CASES = _load_cases()


def _assert_includes(actual: set[str], expected: list[str], label: str) -> None:
    missing = set(expected) - actual
    assert not missing, f"Missing expected {label}: {sorted(missing)}"


@pytest.mark.parametrize("case", EVALUATION_CASES, ids=lambda case: case["id"])
def test_smart_fit_evaluation_case(case: dict[str, Any]) -> None:
    analysis = analyze_smart_fit(
        resume_text=case["resume_text"],
        job_description=case["job_description"],
    )

    assert analysis.fit_summary.band.value in case["allowed_bands"]

    if "min_score" in case:
        assert analysis.fit_summary.score >= case["min_score"]
    if "max_score" in case:
        assert analysis.fit_summary.score <= case["max_score"]

    requirement_skills = {assessment.skill for assessment in analysis.requirement_assessments}
    strong_matches = set(analysis.strong_matches)
    under_sold = set(analysis.under_sold_experience)
    important_gaps = set(analysis.important_gaps)
    lower_priority = set(analysis.lower_priority_items)

    _assert_includes(
        requirement_skills,
        case.get("expected_requirement_skills_include", []),
        "requirement skills",
    )
    _assert_includes(
        strong_matches,
        case.get("expected_strong_matches_include", []),
        "strong matches",
    )
    _assert_includes(
        under_sold,
        case.get("expected_under_sold_include", []),
        "under-sold experience",
    )
    _assert_includes(
        important_gaps,
        case.get("expected_important_gaps_include", []),
        "important gaps",
    )
    _assert_includes(
        lower_priority,
        case.get("expected_lower_priority_include", []),
        "lower-priority items",
    )

    hard_requirements = {
        requirement.category: requirement.status.value
        for requirement in analysis.hard_requirements
    }
    for category, expected_status in case.get("expected_hard_requirements", {}).items():
        assert hard_requirements.get(category) == expected_status

    headline = analysis.fit_summary.headline.lower()
    for phrase in case.get("headline_includes", []):
        assert phrase.lower() in headline
    for phrase in case.get("headline_excludes", []):
        assert phrase.lower() not in headline


def test_smart_fit_evaluation_cases_are_synthetic_and_sanitized() -> None:
    case_ids: set[str] = set()

    for case in EVALUATION_CASES:
        assert case["source"] == "synthetic"
        assert case["id"] not in case_ids
        case_ids.add(case["id"])

        combined_text = f'{case["resume_text"]}\n{case["job_description"]}'
        assert not EMAIL_PATTERN.search(combined_text)
        assert not PHONE_PATTERN.search(combined_text)
        assert "linkedin.com" not in combined_text.lower()
        assert "github.com" not in combined_text.lower()
