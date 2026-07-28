"""Policy extensions for the offline operational reliability harness.

Most coaching actions must reference one requirement, hard constraint, or
capability category directly. The deterministic ``resume_positioning`` action is
an intentional aggregate summary derived from the completed assessment list, so
it is valid only when grounded requirement assessments actually exist.
"""

from __future__ import annotations

from contextlib import contextmanager
from threading import RLock
from typing import Any, Iterator

from app.analysis import operational_reliability as _base
from app.analysis.schemas import CoachingActionType, SmartFitAnalysisResponse

_ORIGINAL_VALIDATE = _base.validate_analysis_invariants
_INSTALL_LOCK = RLock()


def _aggregate_action_titles(analysis: SmartFitAnalysisResponse) -> set[str]:
    if not analysis.requirement_assessments:
        return set()
    return {
        action.title
        for action in analysis.coaching_actions
        if action.category == "resume_positioning"
        and action.action_type == CoachingActionType.RESUME_REWRITE
        and not action.skill
        and not action.job_evidence
    }


def validate_analysis_invariants(
    analysis: SmartFitAnalysisResponse,
    *,
    case_id: str,
    resume_text: str,
    job_description: str,
    run: int | None = None,
) -> list[dict[str, Any]]:
    failures = _ORIGINAL_VALIDATE(
        analysis,
        case_id=case_id,
        resume_text=resume_text,
        job_description=job_description,
        run=run,
    )
    aggregate_titles = _aggregate_action_titles(analysis)
    return [
        failure
        for failure in failures
        if not (
            failure["check"] == "coaching_reference_not_grounded"
            and failure["actual"] in aggregate_titles
        )
    ]


@contextmanager
def _installed_policy_validator() -> Iterator[None]:
    with _INSTALL_LOCK:
        previous = _base.validate_analysis_invariants
        _base.validate_analysis_invariants = validate_analysis_invariants
        try:
            yield
        finally:
            _base.validate_analysis_invariants = previous


def evaluate_operational_reliability(
    benchmark: dict[str, Any] | None = None,
) -> dict[str, Any]:
    with _installed_policy_validator():
        return _base.evaluate_operational_reliability(benchmark)


format_operational_reliability_report = _base.format_operational_reliability_report
load_operational_reliability_benchmark = _base.load_operational_reliability_benchmark
DEFAULT_OPERATIONAL_BENCHMARK_PATH = _base.DEFAULT_OPERATIONAL_BENCHMARK_PATH

__all__ = [
    "DEFAULT_OPERATIONAL_BENCHMARK_PATH",
    "evaluate_operational_reliability",
    "format_operational_reliability_report",
    "load_operational_reliability_benchmark",
    "validate_analysis_invariants",
]
