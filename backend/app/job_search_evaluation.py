from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.job_search import _score_job, parse_job_search_intent
from app.job_source_registry import default_source_identifiers
from app.job_source_routing import MAX_INDUSTRY_ROUTED_SOURCES, build_source_routing_plan

DEFAULT_BENCHMARK_PATH = (
    Path(__file__).resolve().parents[1] / "evaluation" / "job_search_benchmark.json"
)


def load_job_search_benchmark(path: Path | None = None) -> dict[str, Any]:
    benchmark_path = path or DEFAULT_BENCHMARK_PATH
    with benchmark_path.open(encoding="utf-8") as benchmark_file:
        benchmark = json.load(benchmark_file)

    if benchmark.get("version") != 1:
        raise ValueError("Unsupported job-search benchmark version.")

    sections = ("intent_cases", "candidate_cases", "routing_cases")
    all_case_ids: list[str] = []
    for section in sections:
        cases = benchmark.get(section)
        if not isinstance(cases, list) or not cases:
            raise ValueError(f"Benchmark section {section!r} must be a non-empty list.")
        for case in cases:
            case_id = str(case.get("id") or "").strip()
            if not case_id:
                raise ValueError(f"Every {section} case must have an id.")
            all_case_ids.append(case_id)

    if len(all_case_ids) != len(set(all_case_ids)):
        raise ValueError("Benchmark case ids must be unique across all sections.")

    return benchmark


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 1.0


def _record_category_result(
    category_results: dict[str, list[bool]],
    category: str,
    passed: bool,
) -> None:
    category_results[category].append(passed)


def _failure(
    *,
    section: str,
    case: dict[str, Any],
    expected: Any,
    actual: Any,
) -> dict[str, Any]:
    return {
        "section": section,
        "id": case["id"],
        "category": case.get("category", "uncategorized"),
        "critical": bool(case.get("critical", False)),
        "expected": expected,
        "actual": actual,
    }


def evaluate_job_search_benchmark(
    benchmark: dict[str, Any] | None = None,
) -> dict[str, Any]:
    benchmark_data = benchmark or load_job_search_benchmark()
    failures: list[dict[str, Any]] = []
    category_results: dict[str, list[bool]] = defaultdict(list)

    intent_passes = 0
    for case in benchmark_data["intent_cases"]:
        intent = parse_job_search_intent(
            query=case["query"],
            location=case.get("location"),
            level=case.get("level"),
        )
        actual = {
            "job_function": intent.job_function,
            "industry": intent.industry,
            "level": intent.level,
            "location": intent.location,
        }
        expected = case["expected"]
        passed = actual == expected
        intent_passes += int(passed)
        _record_category_result(category_results, case.get("category", "intent"), passed)
        if not passed:
            failures.append(
                _failure(
                    section="intent",
                    case=case,
                    expected=expected,
                    actual=actual,
                )
            )

    true_positives = false_positives = true_negatives = false_negatives = 0
    for case in benchmark_data["candidate_cases"]:
        predicted_match = (
            _score_job(
                title=case["title"],
                description=case["description"],
                query=case["query"],
                level=case.get("level"),
                company=case.get("company"),
            )
            > 0
        )
        expected_match = bool(case["expected_match"])
        passed = predicted_match == expected_match
        _record_category_result(category_results, case.get("category", "candidate"), passed)

        if expected_match and predicted_match:
            true_positives += 1
        elif expected_match and not predicted_match:
            false_negatives += 1
        elif not expected_match and predicted_match:
            false_positives += 1
        else:
            true_negatives += 1

        if not passed:
            failures.append(
                _failure(
                    section="candidate",
                    case=case,
                    expected={"match": expected_match},
                    actual={"match": predicted_match},
                )
            )

    routing_passes = 0
    greenhouse_defaults = default_source_identifiers("greenhouse")
    lever_defaults = default_source_identifiers("lever")
    for case in benchmark_data["routing_cases"]:
        intent = parse_job_search_intent(
            query=case["query"],
            location=case.get("location"),
            level=case.get("level"),
        )
        plan = build_source_routing_plan(
            greenhouse_identifiers=greenhouse_defaults,
            lever_identifiers=lever_defaults,
            industry=intent.industry,
            job_function=intent.job_function,
            level=intent.level,
            location=intent.location,
        )
        selected_sources = {
            *(f"greenhouse:{identifier}" for identifier in plan.greenhouse_identifiers),
            *(f"lever:{identifier}" for identifier in plan.lever_identifiers),
        }
        included_sources = set(case.get("included_sources", []))
        excluded_sources = set(case.get("excluded_sources", []))
        max_total_sources = int(
            case.get("max_total_sources", MAX_INDUSTRY_ROUTED_SOURCES)
        )
        actual = {
            "routed": plan.routed,
            "industry": intent.industry,
            "industry_only_sources_activated": plan.industry_only_sources_activated,
            "selected_sources": sorted(selected_sources),
            "total_sources": len(selected_sources),
        }
        passed = bool(
            plan.routed == bool(case["expected_routed"])
            and intent.industry == case.get("expected_industry")
            and included_sources.issubset(selected_sources)
            and selected_sources.isdisjoint(excluded_sources)
            and plan.industry_only_sources_activated
            >= int(case.get("minimum_industry_only_sources", 0))
            and len(selected_sources) <= max_total_sources
        )
        routing_passes += int(passed)
        _record_category_result(category_results, case.get("category", "routing"), passed)
        if not passed:
            failures.append(
                _failure(
                    section="routing",
                    case=case,
                    expected={
                        "routed": bool(case["expected_routed"]),
                        "industry": case.get("expected_industry"),
                        "included_sources": sorted(included_sources),
                        "excluded_sources": sorted(excluded_sources),
                        "minimum_industry_only_sources": int(
                            case.get("minimum_industry_only_sources", 0)
                        ),
                        "max_total_sources": max_total_sources,
                    },
                    actual=actual,
                )
            )

    intent_total = len(benchmark_data["intent_cases"])
    candidate_total = len(benchmark_data["candidate_cases"])
    routing_total = len(benchmark_data["routing_cases"])
    critical_cases = sum(
        bool(case.get("critical", False))
        for section in ("intent_cases", "candidate_cases", "routing_cases")
        for case in benchmark_data[section]
    )
    critical_failures = [failure for failure in failures if failure["critical"]]

    metrics = {
        "intent_accuracy": _ratio(intent_passes, intent_total),
        "candidate_accuracy": _ratio(
            true_positives + true_negatives,
            candidate_total,
        ),
        "candidate_recall": _ratio(
            true_positives,
            true_positives + false_negatives,
        ),
        "candidate_precision": _ratio(
            true_positives,
            true_positives + false_positives,
        ),
        "negative_rejection_rate": _ratio(
            true_negatives,
            true_negatives + false_positives,
        ),
        "routing_accuracy": _ratio(routing_passes, routing_total),
        "critical_case_pass_rate": _ratio(
            critical_cases - len(critical_failures),
            critical_cases,
        ),
    }
    thresholds = {
        key: float(value)
        for key, value in benchmark_data.get("thresholds", {}).items()
    }
    threshold_failures = {
        metric: {
            "actual": metrics.get(metric),
            "required": required,
        }
        for metric, required in thresholds.items()
        if metrics.get(metric, 0.0) < required
    }

    category_accuracy = {
        category: _ratio(sum(results), len(results))
        for category, results in sorted(category_results.items())
    }
    counts = {
        "intent_cases": intent_total,
        "candidate_cases": candidate_total,
        "positive_candidate_cases": true_positives + false_negatives,
        "negative_candidate_cases": true_negatives + false_positives,
        "routing_cases": routing_total,
        "critical_cases": critical_cases,
        "failures": len(failures),
        "critical_failures": len(critical_failures),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "true_negatives": true_negatives,
        "false_negatives": false_negatives,
    }

    return {
        "benchmark_version": benchmark_data["version"],
        "passed": not critical_failures and not threshold_failures,
        "counts": counts,
        "metrics": metrics,
        "thresholds": thresholds,
        "category_accuracy": category_accuracy,
        "threshold_failures": threshold_failures,
        "failures": failures,
    }


def format_job_search_evaluation_report(report: dict[str, Any]) -> str:
    lines = [
        f"MarketLens job-search benchmark: {'PASS' if report['passed'] else 'FAIL'}",
        (
            f"Cases: {report['counts']['intent_cases']} intent, "
            f"{report['counts']['candidate_cases']} candidate, "
            f"{report['counts']['routing_cases']} routing"
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
                f"- [{failure['section']}] {failure['id']}{critical}: "
                f"expected {failure['expected']!r}, got {failure['actual']!r}"
            )
    else:
        lines.append("No benchmark case failures.")

    return "\n".join(lines)
