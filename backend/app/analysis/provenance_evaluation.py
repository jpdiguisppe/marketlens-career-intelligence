from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.analysis.evaluation import load_smart_fit_benchmark
from app.analysis.role_aware_stable import analyze_smart_fit
from app.analysis.schemas import EvidenceStatus, RequirementType


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 1.0


def _failure(
    *,
    case: dict[str, Any],
    check: str,
    expected: Any,
    actual: Any,
) -> dict[str, Any]:
    return {
        "id": case["id"],
        "sector": case["sector"],
        "critical": bool(case.get("critical", False)),
        "check": check,
        "expected": expected,
        "actual": actual,
    }


def evaluate_evidence_provenance() -> dict[str, Any]:
    benchmark = load_smart_fit_benchmark()
    counters = defaultdict(int)
    failures: list[dict[str, Any]] = []
    sector_results: dict[str, list[bool]] = defaultdict(list)

    for case in benchmark["cases"]:
        case_failure_count = len(failures)
        analysis = analyze_smart_fit(
            resume_text=case["resume_text"],
            job_description=case["job_description"],
            use_model_assisted=bool(case.get("use_model_assisted", False)),
        )

        if analysis.provenance_version != "8c.1":
            failures.append(
                _failure(
                    case=case,
                    check="provenance_version",
                    expected="8c.1",
                    actual=analysis.provenance_version,
                )
            )

        for assessment in analysis.requirement_assessments:
            if assessment.weight <= 0:
                continue

            counters["job_grounding_total"] += 1
            job_grounded = bool(
                assessment.job_provenance
                and assessment.job_provenance.grounded
                and assessment.job_provenance.quote == assessment.job_evidence
            )
            counters["job_grounding_pass"] += int(job_grounded)
            if not job_grounded:
                failures.append(
                    _failure(
                        case=case,
                        check=f"job_grounding:{assessment.skill}",
                        expected=True,
                        actual=assessment.job_provenance.model_dump()
                        if assessment.job_provenance
                        else None,
                    )
                )

            counters["provenance_total"] += 1
            provenance_complete = bool(
                assessment.job_provenance
                and assessment.conclusion_source.value
                in {"deterministic", "model_assisted", "merged"}
            )
            counters["provenance_pass"] += int(provenance_complete)
            if not provenance_complete:
                failures.append(
                    _failure(
                        case=case,
                        check=f"provenance_complete:{assessment.skill}",
                        expected=True,
                        actual=False,
                    )
                )

            if assessment.status != EvidenceStatus.MISSING:
                counters["resume_grounding_total"] += 1
                resume_grounded = bool(
                    assessment.resume_provenance
                    and all(
                        citation.grounded
                        and citation.document_kind.value == "resume"
                        for citation in assessment.resume_provenance
                    )
                )
                counters["resume_grounding_pass"] += int(resume_grounded)
                if not resume_grounded:
                    failures.append(
                        _failure(
                            case=case,
                            check=f"resume_grounding:{assessment.skill}",
                            expected=True,
                            actual=[
                                citation.model_dump()
                                for citation in assessment.resume_provenance
                            ],
                        )
                    )

            if assessment.status in {
                EvidenceStatus.DEMONSTRATED,
                EvidenceStatus.EXPLICIT,
            }:
                counters["strong_match_total"] += 1
                direct_grounded = bool(
                    assessment.resume_provenance
                    and assessment.resume_evidence
                    and all(
                        citation.grounded
                        for citation in assessment.resume_provenance
                    )
                )
                counters["strong_match_pass"] += int(direct_grounded)
                if not direct_grounded:
                    failures.append(
                        _failure(
                            case=case,
                            check=f"strong_match_direct_evidence:{assessment.skill}",
                            expected=True,
                            actual=False,
                        )
                    )

            if (
                assessment.status == EvidenceStatus.MISSING
                and assessment.weight >= 0.75
            ):
                counters["gap_basis_total"] += 1
                gap_grounded = bool(
                    assessment.job_provenance
                    and assessment.job_provenance.grounded
                    and assessment.requirement_type
                    in {
                        RequirementType.REQUIRED_QUALIFICATION,
                        RequirementType.CORE_RESPONSIBILITY,
                    }
                )
                counters["gap_basis_pass"] += int(gap_grounded)
                if not gap_grounded:
                    failures.append(
                        _failure(
                            case=case,
                            check=f"gap_required_signal:{assessment.skill}",
                            expected=True,
                            actual={
                                "requirement_type": assessment.requirement_type.value,
                                "grounded": assessment.job_provenance.grounded
                                if assessment.job_provenance
                                else False,
                            },
                        )
                    )

        for requirement in analysis.hard_requirements:
            counters["hard_grounding_total"] += 1
            counters["hard_grounding_pass"] += int(requirement.grounded)
            if not requirement.grounded:
                failures.append(
                    _failure(
                        case=case,
                        check=f"hard_requirement_grounding:{requirement.category}",
                        expected=True,
                        actual=False,
                    )
                )

        if analysis.grounding_warnings:
            failures.append(
                _failure(
                    case=case,
                    check="grounding_warnings",
                    expected=[],
                    actual=analysis.grounding_warnings,
                )
            )

        case_passed = len(failures) == case_failure_count
        counters["case_pass"] += int(case_passed)
        sector_results[case["sector"]].append(case_passed)

    critical_ids = {
        case["id"] for case in benchmark["cases"] if case.get("critical", False)
    }
    critical_failures = [
        failure for failure in failures if failure["id"] in critical_ids
    ]

    metrics = {
        "job_grounding_rate": _ratio(
            counters["job_grounding_pass"], counters["job_grounding_total"]
        ),
        "resume_grounding_rate": _ratio(
            counters["resume_grounding_pass"], counters["resume_grounding_total"]
        ),
        "provenance_coverage_rate": _ratio(
            counters["provenance_pass"], counters["provenance_total"]
        ),
        "strong_match_direct_evidence_rate": _ratio(
            counters["strong_match_pass"], counters["strong_match_total"]
        ),
        "gap_required_signal_rate": _ratio(
            counters["gap_basis_pass"], counters["gap_basis_total"]
        ),
        "hard_requirement_grounding_rate": _ratio(
            counters["hard_grounding_pass"], counters["hard_grounding_total"]
        ),
        "critical_case_pass_rate": _ratio(
            len(critical_ids) - len({failure["id"] for failure in critical_failures}),
            len(critical_ids),
        ),
        "case_pass_rate": _ratio(
            counters["case_pass"], len(benchmark["cases"])
        ),
    }

    passed = not failures and all(value == 1.0 for value in metrics.values())
    return {
        "version": "8c.1",
        "passed": passed,
        "counts": {
            "cases": len(benchmark["cases"]),
            "sectors": len(sector_results),
            "critical_cases": len(critical_ids),
            "scored_requirements": counters["job_grounding_total"],
            "non_missing_evidence": counters["resume_grounding_total"],
            "strong_matches": counters["strong_match_total"],
            "high_priority_gaps": counters["gap_basis_total"],
            "hard_requirements": counters["hard_grounding_total"],
        },
        "metrics": metrics,
        "sector_pass_rates": {
            sector: _ratio(sum(results), len(results))
            for sector, results in sorted(sector_results.items())
        },
        "failures": failures,
    }


def format_evidence_provenance_report(report: dict[str, Any]) -> str:
    lines = [
        "Smart Fit Evidence Provenance Evaluation",
        f"version: {report['version']}",
        f"status: {'PASS' if report['passed'] else 'FAIL'}",
        "",
        "Counts:",
    ]
    lines.extend(
        f"- {name}: {value}" for name, value in report["counts"].items()
    )
    lines.append("")
    lines.append("Metrics:")
    lines.extend(
        f"- {name}: {value:.3f}" for name, value in report["metrics"].items()
    )
    if report["failures"]:
        lines.append("")
        lines.append("Failures:")
        for failure in report["failures"]:
            lines.append(
                f"- {failure['id']} [{failure['check']}]: "
                f"expected {failure['expected']!r}, got {failure['actual']!r}"
            )
    return "\n".join(lines)
