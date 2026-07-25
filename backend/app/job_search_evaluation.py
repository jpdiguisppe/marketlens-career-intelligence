from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.job_search import (
    _location_score_bonus,
    _matches_location,
    _score_job,
    parse_job_search_intent,
)
from app.job_source_registry import default_source_identifiers
from app.job_source_routing import MAX_INDUSTRY_ROUTED_SOURCES, build_source_routing_plan

DEFAULT_BENCHMARK_PATH = (
    Path(__file__).resolve().parents[1] / "evaluation" / "job_search_benchmark.json"
)
CORRECTNESS_BENCHMARK_PATH = (
    Path(__file__).resolve().parents[1]
    / "evaluation"
    / "job_search_correctness_cases.json"
)
BENCHMARK_SECTIONS = (
    "intent_cases",
    "candidate_cases",
    "location_cases",
    "ranking_cases",
    "routing_cases",
)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as benchmark_file:
        benchmark = json.load(benchmark_file)
    if benchmark.get("version") != 1:
        raise ValueError(f"Unsupported job-search benchmark version in {path.name}.")
    return benchmark


def _merge_benchmarks(
    base: dict[str, Any],
    supplemental: dict[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(base)
    merged["thresholds"] = dict(base.get("thresholds", {}))
    for section in BENCHMARK_SECTIONS:
        merged[section] = list(base.get(section, []))

    if supplemental is None:
        return merged

    merged["thresholds"].update(supplemental.get("thresholds", {}))
    for section in BENCHMARK_SECTIONS:
        merged[section].extend(supplemental.get(section, []))
    return merged


def load_job_search_benchmark(path: Path | None = None) -> dict[str, Any]:
    benchmark_path = path or DEFAULT_BENCHMARK_PATH
    base = _load_json(benchmark_path)
    supplemental = None
    if path is None and CORRECTNESS_BENCHMARK_PATH.exists():
        supplemental = _load_json(CORRECTNESS_BENCHMARK_PATH)

    benchmark = _merge_benchmarks(base, supplemental)

    required_sections = ("intent_cases", "candidate_cases", "routing_cases")
    all_case_ids: list[str] = []
    for section in BENCHMARK_SECTIONS:
        cases = benchmark.get(section)
        if not isinstance(cases, list):
            raise ValueError(f"Benchmark section {section!r} must be a list.")
        if section in required_sections and not cases:
            raise ValueError(f"Benchmark section {section!r} must be non-empty.")
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


def _candidate_match(case: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    role_score = _score_job(
        title=case["title"],
        description=case["description"],
        query=case["query"],
        level=case.get("level"),
        company=case.get("company"),
    )
    has_location_constraint = "location" in case or "job_location" in case
    location_match = (
        _matches_location(case.get("job_location"), case.get("location"))
        if has_location_constraint
        else True
    )
    predicted_match = role_score > 0 and location_match
    return predicted_match, {
        "match": predicted_match,
        "role_score": role_score,
        "location_match": location_match,
    }


def _ranking_result(case: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    scored: list[tuple[int, str]] = []
    for candidate in case["candidates"]:
        role_score = _score_job(
            title=candidate["title"],
            description=candidate["description"],
            query=case["query"],
            level=case.get("level"),
            company=candidate.get("company"),
        )
        requested_location = case.get("location")
        job_location = candidate.get("job_location")
        if requested_location is not None and not _matches_location(
            job_location,
            requested_location,
        ):
            total_score = -1
        else:
            total_score = role_score + _location_score_bonus(
                job_location,
                requested_location,
            )
        scored.append((total_score, candidate["id"]))

    ranked_ids = [
        candidate_id
        for _, candidate_id in sorted(
            scored,
            key=lambda item: (-item[0], item[1]),
        )
    ]
    expected_best = case["expected_best"]
    return bool(ranked_ids and ranked_ids[0] == expected_best), {
        "best": ranked_ids[0] if ranked_ids else None,
        "ranked_ids": ranked_ids,
        "scores": {candidate_id: score for score, candidate_id in scored},
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
        predicted_match, actual = _candidate_match(case)
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
                    actual=actual,
                )
            )

    location_passes = 0
    for case in benchmark_data["location_cases"]:
        actual_match = _matches_location(
            case.get("job_location"),
            case.get("requested_location"),
        )
        expected_match = bool(case["expected_match"])
        passed = actual_match == expected_match
        location_passes += int(passed)
        _record_category_result(category_results, case.get("category", "location"), passed)
        if not passed:
            failures.append(
                _failure(
                    section="location",
                    case=case,
                    expected={"match": expected_match},
                    actual={"match": actual_match},
                )
            )

    ranking_passes = 0
    for case in benchmark_data["ranking_cases"]:
        passed, actual = _ranking_result(case)
        ranking_passes += int(passed)
        _record_category_result(category_results, case.get("category", "ranking"), passed)
        if not passed:
            failures.append(
                _failure(
                    section="ranking",
                    case=case,
                    expected={"best": case["expected_best"]},
                    actual=actual,
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
    location_total = len(benchmark_data["location_cases"])
    ranking_total = len(benchmark_data["ranking_cases"])
    routing_total = len(benchmark_data["routing_cases"])
    critical_cases = sum(
        bool(case.get("critical", False))
        for section in BENCHMARK_SECTIONS
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
        "location_accuracy": _ratio(location_passes, location_total),
        "ranking_accuracy": _ratio(ranking_passes, ranking_total),
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
        "location_cases": location_total,
        "ranking_cases": ranking_total,
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
            f"{report['counts']['location_cases']} location, "
            f"{report['counts']['ranking_cases']} ranking, "
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
