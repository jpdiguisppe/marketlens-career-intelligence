from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

from app.analysis import analyze_smart_fit
from app.analysis.personalized_coaching import (
    PersonalizedCoachingError,
    PersonalizedCoachingPlan,
    apply_personalized_coaching,
    validate_personalized_coaching,
)

_BENCHMARK_PATH = (
    Path(__file__).resolve().parents[2]
    / "evaluation"
    / "personalized_coaching_benchmark.json"
)


def load_personalized_coaching_benchmark() -> dict[str, Any]:
    return json.loads(_BENCHMARK_PATH.read_text(encoding="utf-8"))


def _rejection_check(
    *,
    name: str,
    payload: dict[str, Any],
    analysis,
) -> dict[str, Any]:
    try:
        plan = PersonalizedCoachingPlan.model_validate(payload)
        validate_personalized_coaching(plan, analysis)
    except PersonalizedCoachingError as exc:
        return {
            "name": name,
            "passed": True,
            "error_code": exc.code,
        }
    return {
        "name": name,
        "passed": False,
        "error_code": None,
    }


def _mutated_plan(
    baseline: dict[str, Any],
    mutation: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    payload = deepcopy(baseline)
    mutation(payload)
    return payload


def evaluate_personalized_coaching() -> dict[str, Any]:
    benchmark = load_personalized_coaching_benchmark()
    analysis = analyze_smart_fit(
        resume_text=benchmark["resume_text"],
        job_description=benchmark["job_description"],
        use_model_assisted=False,
    )
    baseline = benchmark["valid_plan"]
    checks: list[dict[str, Any]] = []

    try:
        valid_plan = PersonalizedCoachingPlan.model_validate(baseline)
        validate_personalized_coaching(valid_plan, analysis)
        valid_plan_passed = True
    except (PersonalizedCoachingError, ValueError):
        valid_plan_passed = False
    checks.append(
        {
            "name": "valid_grounded_plan",
            "passed": valid_plan_passed,
            "error_code": None,
        }
    )

    checks.append(
        _rejection_check(
            name="unknown_reference_rejected",
            payload=_mutated_plan(
                baseline,
                lambda payload: payload["action_items"][0].update(
                    {
                        "reference": "Kubernetes",
                        "job_evidence": "Kubernetes is required.",
                    }
                ),
            ),
            analysis=analysis,
        )
    )
    checks.append(
        _rejection_check(
            name="invented_resume_evidence_rejected",
            payload=_mutated_plan(
                baseline,
                lambda payload: payload["action_items"][2].update(
                    {
                        "resume_evidence": [
                            "Deployed Docker containers to production."
                        ]
                    }
                ),
            ),
            analysis=analysis,
        )
    )
    checks.append(
        _rejection_check(
            name="status_basis_mismatch_rejected",
            payload=_mutated_plan(
                baseline,
                lambda payload: payload["action_items"][1].update(
                    {
                        "basis": "experience_learning_gap",
                        "action_type": "learning_focus",
                    }
                ),
            ),
            analysis=analysis,
        )
    )
    checks.append(
        _rejection_check(
            name="changed_job_quote_rejected",
            payload=_mutated_plan(
                baseline,
                lambda payload: payload["action_items"][0].update(
                    {"job_evidence": "Ten years of Python are required."}
                ),
            ),
            analysis=analysis,
        )
    )
    checks.append(
        _rejection_check(
            name="hiring_prediction_rejected",
            payload=_mutated_plan(
                baseline,
                lambda payload: payload.update(
                    {
                        "application_guidance": (
                            "This change gives a 90% chance of an interview and guarantees success."
                        )
                    }
                ),
            ),
            analysis=analysis,
        )
    )

    fallback = apply_personalized_coaching(
        analysis,
        use_model_assisted=False,
    )
    immutable_fields_preserved = all(
        [
            fallback.fit_summary == analysis.fit_summary,
            fallback.requirement_assessments == analysis.requirement_assessments,
            fallback.hard_requirements == analysis.hard_requirements,
            fallback.provenance_version == analysis.provenance_version,
            fallback.grounding_warnings == analysis.grounding_warnings,
        ]
    )
    deterministic_fallback_complete = all(
        [
            fallback.coaching_engine == "deterministic",
            fallback.coaching_status == "not_requested",
            fallback.coaching_actions == analysis.coaching_actions,
            fallback.report_summary == analysis.report_summary,
        ]
    )
    checks.extend(
        [
            {
                "name": "immutable_analysis_preserved",
                "passed": immutable_fields_preserved,
                "error_code": None,
            },
            {
                "name": "deterministic_fallback_complete",
                "passed": deterministic_fallback_complete,
                "error_code": None,
            },
        ]
    )

    by_name = {check["name"]: check for check in checks}
    metrics = {
        "valid_plan_acceptance_rate": float(
            by_name["valid_grounded_plan"]["passed"]
        ),
        "unsupported_reference_rejection_rate": float(
            by_name["unknown_reference_rejected"]["passed"]
        ),
        "invented_evidence_rejection_rate": float(
            by_name["invented_resume_evidence_rejected"]["passed"]
        ),
        "status_basis_rejection_rate": float(
            by_name["status_basis_mismatch_rejected"]["passed"]
        ),
        "job_quote_rejection_rate": float(
            by_name["changed_job_quote_rejected"]["passed"]
        ),
        "unsupported_prediction_rejection_rate": float(
            by_name["hiring_prediction_rejected"]["passed"]
        ),
        "immutable_analysis_preservation_rate": float(
            by_name["immutable_analysis_preserved"]["passed"]
        ),
        "deterministic_fallback_completeness_rate": float(
            by_name["deterministic_fallback_complete"]["passed"]
        ),
    }
    failures = [check for check in checks if not check["passed"]]
    passed = not failures and all(value == 1.0 for value in metrics.values())

    return {
        "version": benchmark["version"],
        "passed": passed,
        "counts": {
            "checks": len(checks),
            "critical_rejection_checks": 5,
            "grounded_actions": len(baseline["action_items"]),
        },
        "metrics": metrics,
        "checks": checks,
        "failures": failures,
    }


def format_personalized_coaching_report(report: dict[str, Any]) -> str:
    lines = [
        f"Personalized Coaching Evaluation {report['version']}",
        f"Passed: {report['passed']}",
        "",
        "Counts:",
    ]
    for name, value in report["counts"].items():
        lines.append(f"- {name}: {value}")
    lines.append("")
    lines.append("Metrics:")
    for name, value in report["metrics"].items():
        lines.append(f"- {name}: {value:.1%}")
    if report["failures"]:
        lines.append("")
        lines.append("Failures:")
        for failure in report["failures"]:
            lines.append(f"- {failure['name']}")
    return "\n".join(lines)


__all__ = [
    "evaluate_personalized_coaching",
    "format_personalized_coaching_report",
    "load_personalized_coaching_benchmark",
]
