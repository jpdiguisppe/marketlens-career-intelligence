from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.analysis.role_aware_stable import analyze_smart_fit

DEFAULT_BENCHMARK_PATH = (
    Path(__file__).resolve().parents[2] / "evaluation" / "smart_fit_benchmark.json"
)


def _normalized(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 1.0


def _failure(
    *, case: dict[str, Any], check: str, expected: Any, actual: Any
) -> dict[str, Any]:
    return {
        "id": case["id"],
        "sector": case["sector"],
        "critical": bool(case.get("critical", False)),
        "check": check,
        "expected": expected,
        "actual": actual,
    }


def load_smart_fit_benchmark(path: Path | None = None) -> dict[str, Any]:
    benchmark_path = path or DEFAULT_BENCHMARK_PATH
    with benchmark_path.open(encoding="utf-8") as benchmark_file:
        benchmark = json.load(benchmark_file)

    if benchmark.get("version") != 1:
        raise ValueError("Unsupported Smart Fit benchmark version.")

    cases = benchmark.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Smart Fit benchmark cases must be a non-empty list.")

    case_ids: list[str] = []
    sectors: set[str] = set()
    critical_cases = 0
    for case in cases:
        case_id = str(case.get("id") or "").strip()
        sector = str(case.get("sector") or "").strip()
        if not case_id:
            raise ValueError("Every Smart Fit benchmark case must have an id.")
        if not sector:
            raise ValueError(f"Smart Fit benchmark case {case_id!r} must have a sector.")
        if not str(case.get("resume_text") or "").strip():
            raise ValueError(f"Smart Fit benchmark case {case_id!r} must include resume_text.")
        if not str(case.get("job_description") or "").strip():
            raise ValueError(f"Smart Fit benchmark case {case_id!r} must include job_description.")
        if not isinstance(case.get("expected"), dict):
            raise ValueError(f"Smart Fit benchmark case {case_id!r} must include expected output.")
        case_ids.append(case_id)
        sectors.add(sector)
        critical_cases += int(bool(case.get("critical", False)))

    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Smart Fit benchmark case ids must be unique.")

    minimums = benchmark.get("minimums", {})
    required_cases = int(minimums.get("cases", 1))
    required_sectors = int(minimums.get("sectors", 1))
    required_critical = int(minimums.get("critical_cases", 0))
    if len(cases) < required_cases:
        raise ValueError(
            f"Smart Fit benchmark must contain at least {required_cases} cases; found {len(cases)}."
        )
    if len(sectors) < required_sectors:
        raise ValueError(
            f"Smart Fit benchmark must cover at least {required_sectors} sectors; found {len(sectors)}."
        )
    if critical_cases < required_critical:
        raise ValueError(
            f"Smart Fit benchmark must contain at least {required_critical} critical cases; found {critical_cases}."
        )

    return benchmark


def evaluate_smart_fit_benchmark(
    benchmark: dict[str, Any] | None = None,
) -> dict[str, Any]:
    benchmark_data = benchmark or load_smart_fit_benchmark()
    failures: list[dict[str, Any]] = []
    sector_results: dict[str, list[bool]] = defaultdict(list)

    counters = defaultdict(int)

    for case in benchmark_data["cases"]:
        expected = case["expected"]
        analysis = analyze_smart_fit(
            resume_text=case["resume_text"],
            job_description=case["job_description"],
            use_model_assisted=bool(case.get("use_model_assisted", False)),
        )
        case_failure_count = len(failures)

        actual_requirements = {
            _normalized(item.skill): item for item in analysis.requirement_assessments
        }
        expected_requirements = {
            _normalized(item["skill"]): item
            for item in expected.get("requirements", [])
        }
        actual_keys = set(actual_requirements)
        expected_keys = set(expected_requirements)
        counters["requirement_tp"] += len(actual_keys & expected_keys)
        counters["requirement_fp"] += len(actual_keys - expected_keys)
        counters["requirement_fn"] += len(expected_keys - actual_keys)
        if actual_keys != expected_keys:
            failures.append(
                _failure(
                    case=case,
                    check="requirements",
                    expected=sorted(item["skill"] for item in expected_requirements.values()),
                    actual=sorted(item.skill for item in actual_requirements.values()),
                )
            )

        for skill_key, expected_requirement in expected_requirements.items():
            counters["requirement_type_total"] += 1
            actual_requirement = actual_requirements.get(skill_key)
            actual_type = actual_requirement.requirement_type.value if actual_requirement else None
            passed = actual_type == expected_requirement["type"]
            counters["requirement_type_pass"] += int(passed)
            if not passed:
                failures.append(
                    _failure(
                        case=case,
                        check=f"requirement_type:{expected_requirement['skill']}",
                        expected=expected_requirement["type"],
                        actual=actual_type,
                    )
                )

        for evidence in expected.get("evidence", []):
            actual_assessment = actual_requirements.get(_normalized(evidence["skill"]))
            actual_status = actual_assessment.status.value if actual_assessment else None
            allowed_statuses = set(evidence["allowed_statuses"])
            counters["evidence_status_total"] += 1
            passed = actual_status in allowed_statuses
            counters["evidence_status_pass"] += int(passed)
            if not passed:
                failures.append(
                    _failure(
                        case=case,
                        check=f"evidence_status:{evidence['skill']}",
                        expected=sorted(allowed_statuses),
                        actual=actual_status,
                    )
                )

            if evidence.get("require_resume_evidence", False):
                counters["evidence_link_total"] += 1
                links = actual_assessment.resume_evidence if actual_assessment else []
                link_passed = bool(links)
                counters["evidence_link_pass"] += int(link_passed)
                if not link_passed:
                    failures.append(
                        _failure(
                            case=case,
                            check=f"evidence_link:{evidence['skill']}",
                            expected="at least one resume evidence fragment",
                            actual=links,
                        )
                    )

        actual_gaps = {
            *(_normalized(value) for value in analysis.important_gaps),
            *(_normalized(group.title) for group in analysis.gap_groups),
            *(
                _normalized(skill)
                for group in analysis.gap_groups
                for skill in group.skills
            ),
        }
        for expected_gap in expected.get("gaps", []):
            counters["gap_total"] += 1
            passed = _normalized(expected_gap) in actual_gaps
            counters["gap_pass"] += int(passed)
            if not passed:
                failures.append(
                    _failure(
                        case=case,
                        check=f"gap_present:{expected_gap}",
                        expected=True,
                        actual=sorted(actual_gaps),
                    )
                )

        for forbidden_gap in expected.get("forbidden_gaps", []):
            counters["forbidden_gap_total"] += 1
            passed = _normalized(forbidden_gap) not in actual_gaps
            counters["forbidden_gap_pass"] += int(passed)
            if not passed:
                failures.append(
                    _failure(
                        case=case,
                        check=f"gap_absent:{forbidden_gap}",
                        expected=False,
                        actual=True,
                    )
                )

        actual_strengths = {
            *(_normalized(value) for value in analysis.strong_matches),
            *(
                _normalized(item.skill)
                for item in analysis.requirement_assessments
                if item.status.value in {"demonstrated", "explicit"}
            ),
        }
        for forbidden_strength in expected.get("forbidden_strengths", []):
            counters["unsupported_strength_total"] += 1
            passed = _normalized(forbidden_strength) not in actual_strengths
            counters["unsupported_strength_pass"] += int(passed)
            if not passed:
                failures.append(
                    _failure(
                        case=case,
                        check=f"unsupported_strength:{forbidden_strength}",
                        expected=False,
                        actual=True,
                    )
                )

        actual_hard = {
            _normalized(item.category): item for item in analysis.hard_requirements
        }
        for expected_hard in expected.get("hard_requirements", []):
            counters["hard_requirement_total"] += 1
            actual_item = actual_hard.get(_normalized(expected_hard["category"]))
            actual_status = actual_item.status.value if actual_item else None
            passed = actual_status == expected_hard["status"]
            counters["hard_requirement_pass"] += int(passed)
            if not passed:
                failures.append(
                    _failure(
                        case=case,
                        check=f"hard_requirement:{expected_hard['category']}",
                        expected=expected_hard["status"],
                        actual=actual_status,
                    )
                )

        expected_engine = expected.get("analysis_engine")
        expected_status_prefix = expected.get("model_assisted_status_prefix")
        if expected_engine is not None or expected_status_prefix is not None:
            counters["fallback_total"] += 1
            passed = (
                (expected_engine is None or analysis.analysis_engine == expected_engine)
                and (
                    expected_status_prefix is None
                    or analysis.model_assisted_status.startswith(expected_status_prefix)
                )
            )
            counters["fallback_pass"] += int(passed)
            if not passed:
                failures.append(
                    _failure(
                        case=case,
                        check="engine_and_fallback",
                        expected={
                            "analysis_engine": expected_engine,
                            "model_assisted_status_prefix": expected_status_prefix,
                        },
                        actual={
                            "analysis_engine": analysis.analysis_engine,
                            "model_assisted_status": analysis.model_assisted_status,
                        },
                    )
                )

        if "fit_score_min" in expected or "fit_score_max" in expected:
            counters["fit_score_total"] += 1
            minimum = int(expected.get("fit_score_min", 0))
            maximum = int(expected.get("fit_score_max", 100))
            passed = minimum <= analysis.fit_summary.score <= maximum
            counters["fit_score_pass"] += int(passed)
            if not passed:
                failures.append(
                    _failure(
                        case=case,
                        check="fit_score_range",
                        expected={"minimum": minimum, "maximum": maximum},
                        actual=analysis.fit_summary.score,
                    )
                )

        case_passed = len(failures) == case_failure_count
        counters["case_pass"] += int(case_passed)
        sector_results[case["sector"]].append(case_passed)

    cases = benchmark_data["cases"]
    critical_ids = {case["id"] for case in cases if case.get("critical", False)}
    critical_failures = [failure for failure in failures if failure["id"] in critical_ids]

    metrics = {
        "requirement_recall": _ratio(
            counters["requirement_tp"],
            counters["requirement_tp"] + counters["requirement_fn"],
        ),
        "requirement_precision": _ratio(
            counters["requirement_tp"],
            counters["requirement_tp"] + counters["requirement_fp"],
        ),
        "requirement_type_accuracy": _ratio(
            counters["requirement_type_pass"], counters["requirement_type_total"]
        ),
        "evidence_status_accuracy": _ratio(
            counters["evidence_status_pass"], counters["evidence_status_total"]
        ),
        "evidence_link_rate": _ratio(
            counters["evidence_link_pass"], counters["evidence_link_total"]
        ),
        "gap_recall": _ratio(counters["gap_pass"], counters["gap_total"]),
        "false_gap_rejection_rate": _ratio(
            counters["forbidden_gap_pass"], counters["forbidden_gap_total"]
        ),
        "unsupported_strength_rejection_rate": _ratio(
            counters["unsupported_strength_pass"],
            counters["unsupported_strength_total"],
        ),
        "hard_requirement_accuracy": _ratio(
            counters["hard_requirement_pass"], counters["hard_requirement_total"]
        ),
        "fallback_accuracy": _ratio(
            counters["fallback_pass"], counters["fallback_total"]
        ),
        "fit_score_range_accuracy": _ratio(
            counters["fit_score_pass"], counters["fit_score_total"]
        ),
        "case_pass_rate": _ratio(counters["case_pass"], len(cases)),
        "critical_case_pass_rate": _ratio(
            len(critical_ids) - len({failure["id"] for failure in critical_failures}),
            len(critical_ids),
        ),
    }
    thresholds = {
        key: float(value) for key, value in benchmark_data.get("thresholds", {}).items()
    }
    threshold_failures = {
        metric: {"actual": metrics.get(metric), "required": required}
        for metric, required in thresholds.items()
        if metrics.get(metric, 0.0) < required
    }

    return {
        "benchmark_version": benchmark_data["version"],
        "passed": not critical_failures and not threshold_failures,
        "counts": {
            "cases": len(cases),
            "sectors": len(sector_results),
            "critical_cases": len(critical_ids),
            "failures": len(failures),
            "critical_failures": len(critical_failures),
            "expected_requirements": counters["requirement_tp"] + counters["requirement_fn"],
            "actual_requirements": counters["requirement_tp"] + counters["requirement_fp"],
            "evidence_checks": counters["evidence_status_total"],
            "expected_gaps": counters["gap_total"],
            "forbidden_strength_checks": counters["unsupported_strength_total"],
            "hard_requirement_checks": counters["hard_requirement_total"],
            "fallback_checks": counters["fallback_total"],
        },
        "metrics": metrics,
        "thresholds": thresholds,
        "sector_accuracy": {
            sector: _ratio(sum(results), len(results))
            for sector, results in sorted(sector_results.items())
        },
        "threshold_failures": threshold_failures,
        "failures": failures,
    }


def format_smart_fit_evaluation_report(report: dict[str, Any]) -> str:
    lines = [
        f"MarketLens Smart Fit benchmark: {'PASS' if report['passed'] else 'FAIL'}",
        (
            f"Cases: {report['counts']['cases']} across "
            f"{report['counts']['sectors']} sectors; "
            f"{report['counts']['critical_cases']} critical"
        ),
    ]
    for metric, value in report["metrics"].items():
        required = report["thresholds"].get(metric)
        threshold_text = f" (required {required:.1%})" if required is not None else ""
        lines.append(f"- {metric}: {value:.1%}{threshold_text}")

    if report["failures"]:
        lines.append("Failures:")
        for failure in report["failures"]:
            critical = " CRITICAL" if failure["critical"] else ""
            lines.append(
                f"- [{failure['sector']}] {failure['id']} / "
                f"{failure['check']}{critical}: expected "
                f"{failure['expected']!r}, got {failure['actual']!r}"
            )
    else:
        lines.append("No benchmark case failures.")

    return "\n".join(lines)
