"""Independent Milestone 8.1I occupation interpretation and title benchmark."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from . import occupation_catalog_runtime as occupation_runtime

DEFAULT_BENCHMARK_PATH = (
    Path(__file__).resolve().parents[1]
    / "evaluation"
    / "held_out_occupation_benchmark.json"
)
DEFAULT_ALTERNATE_QUERY_PATH = (
    Path(__file__).resolve().parents[1]
    / "evaluation"
    / "held_out_occupation_alternate_queries.json"
)

_RECOGNIZED_KINDS = frozenset(
    {"canonical", "modifier", "typo", "alternate", "safe_acronym"}
)


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 1.0


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as benchmark_file:
        data = json.load(benchmark_file)
    if data.get("version") != 1:
        raise ValueError(f"Unsupported held-out benchmark version in {path.name}.")
    return data


def load_held_out_occupation_benchmark(
    benchmark_path: Path | None = None,
    alternate_query_path: Path | None = None,
) -> dict[str, Any]:
    benchmark = _load_json(benchmark_path or DEFAULT_BENCHMARK_PATH)
    alternate = _load_json(alternate_query_path or DEFAULT_ALTERNATE_QUERY_PATH)

    required_lists = (
        "required_major_groups",
        "seeds",
        "ambiguous_acronyms",
        "safe_acronym_cases",
        "unknown_queries",
    )
    for field in required_lists:
        if not isinstance(benchmark.get(field), list) or not benchmark[field]:
            raise ValueError(f"Held-out benchmark field {field!r} must be non-empty.")
    if not isinstance(alternate.get("cases"), list) or not alternate["cases"]:
        raise ValueError("Held-out alternate-title cases must be non-empty.")

    merged = dict(benchmark)
    merged["alternate_query_cases"] = list(alternate["cases"])
    merged["thresholds"] = dict(benchmark.get("thresholds", {}))
    merged["thresholds"].setdefault("alternate_accuracy", 1.0)
    merged["thresholds"].setdefault("title_accuracy", 1.0)
    return merged


def expand_held_out_query_cases(benchmark: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    for seed in benchmark["seeds"]:
        expected = {
            "status": "recognized",
            "concept_key": seed["concept_key"],
            "soc_major_group": seed["soc_major_group"],
        }
        shared = {
            "career_sphere": seed["career_sphere"],
            "expected": expected,
        }
        cases.extend(
            [
                {
                    "id": f"{seed['id']}-canonical",
                    "kind": "canonical",
                    "query": seed["canonical_query"],
                    **shared,
                },
                {
                    "id": f"{seed['id']}-modifier",
                    "kind": "modifier",
                    "query": f"entry level {seed['canonical_query']} jobs",
                    **shared,
                },
                {
                    "id": f"{seed['id']}-typo",
                    "kind": "typo",
                    "query": seed["typo_query"],
                    **shared,
                },
            ]
        )

    for alternate in benchmark["alternate_query_cases"]:
        cases.append(
            {
                "id": alternate["id"],
                "kind": "alternate",
                "query": alternate["query"],
                "career_sphere": alternate["career_sphere"],
                "expected": {
                    "status": "recognized",
                    "concept_key": alternate["concept_key"],
                    "soc_major_group": alternate["soc_major_group"],
                },
            }
        )

    for acronym in benchmark["ambiguous_acronyms"]:
        uppercase = str(acronym).upper()
        for suffix, query in (("bare", uppercase), ("jobs", f"{uppercase} jobs")):
            cases.append(
                {
                    "id": f"ambiguous-{acronym}-{suffix}",
                    "kind": "ambiguous",
                    "query": query,
                    "career_sphere": "cross-sector ambiguity",
                    "expected": {"status": "ambiguous"},
                }
            )

    for safe in benchmark["safe_acronym_cases"]:
        cases.append(
            {
                "id": safe["id"],
                "kind": "safe_acronym",
                "query": safe["query"],
                "career_sphere": safe["career_sphere"],
                "expected": {
                    "status": "recognized",
                    "concept_key": safe["concept_key"],
                    "soc_major_group": safe["soc_major_group"],
                },
            }
        )

    for unknown in benchmark["unknown_queries"]:
        cases.append(
            {
                "id": unknown["id"],
                "kind": "unknown",
                "query": unknown["query"],
                "career_sphere": "unknown",
                "expected": {"status": "unrecognized"},
            }
        )

    case_ids = [case["id"] for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Held-out query case ids must be unique.")
    return cases


def _query_case_passed(case: dict[str, Any], actual: dict[str, Any]) -> bool:
    expected = case["expected"]
    if actual["status"] != expected["status"]:
        return False
    if expected["status"] == "recognized":
        return bool(
            actual["concept_key"] == expected["concept_key"]
            and actual["soc_major_group"] == expected["soc_major_group"]
        )
    if expected["status"] == "ambiguous":
        return bool(actual["suggestions"])
    return True


def _failure(
    *,
    section: str,
    case_id: str,
    kind: str,
    expected: Any,
    actual: Any,
) -> dict[str, Any]:
    return {
        "section": section,
        "id": case_id,
        "kind": kind,
        "expected": expected,
        "actual": actual,
    }


def evaluate_held_out_occupation_benchmark(
    benchmark: dict[str, Any] | None = None,
) -> dict[str, Any]:
    benchmark_data = benchmark or load_held_out_occupation_benchmark()
    query_cases = expand_held_out_query_cases(benchmark_data)
    failures: list[dict[str, Any]] = []
    kind_passes: dict[str, int] = defaultdict(int)
    kind_totals: dict[str, int] = defaultdict(int)

    recognized_passes = recognized_total = 0
    for case in query_cases:
        interpretation = occupation_runtime.interpret_occupation_query(case["query"])
        actual = {
            "status": interpretation.status,
            "concept_key": interpretation.concept_key,
            "soc_major_group": interpretation.soc_major_group,
            "occupation_phrase": interpretation.occupation_phrase,
            "suggestions": list(interpretation.suggestions),
            "reason": interpretation.reason,
        }
        passed = _query_case_passed(case, actual)
        kind_totals[case["kind"]] += 1
        kind_passes[case["kind"]] += int(passed)
        if case["kind"] in _RECOGNIZED_KINDS:
            recognized_total += 1
            recognized_passes += int(passed)
        if not passed:
            failures.append(
                _failure(
                    section="query",
                    case_id=case["id"],
                    kind=case["kind"],
                    expected=case["expected"],
                    actual=actual,
                )
            )

    true_positives = false_positives = true_negatives = false_negatives = 0
    for seed in benchmark_data["seeds"]:
        interpretation = occupation_runtime.interpret_occupation_query(
            seed["canonical_query"]
        )
        for label, title, expected_match in (
            ("positive", seed["positive_title"], True),
            ("negative", seed["negative_title"], False),
        ):
            predicted = occupation_runtime.title_matches_occupation(
                title,
                interpretation,
            )
            if expected_match and predicted:
                true_positives += 1
            elif expected_match and not predicted:
                false_negatives += 1
            elif not expected_match and predicted:
                false_positives += 1
            else:
                true_negatives += 1
            if predicted != expected_match:
                failures.append(
                    _failure(
                        section="title",
                        case_id=f"{seed['id']}-{label}",
                        kind=f"title_{label}",
                        expected={"match": expected_match},
                        actual={
                            "match": predicted,
                            "query_status": interpretation.status,
                            "concept_key": interpretation.concept_key,
                            "title": title,
                        },
                    )
                )

    query_passes = sum(kind_passes.values())
    title_total = true_positives + false_positives + true_negatives + false_negatives
    metrics = {
        "query_accuracy": _ratio(query_passes, len(query_cases)),
        "recognized_accuracy": _ratio(recognized_passes, recognized_total),
        "canonical_accuracy": _ratio(
            kind_passes["canonical"], kind_totals["canonical"]
        ),
        "modifier_accuracy": _ratio(
            kind_passes["modifier"], kind_totals["modifier"]
        ),
        "typo_accuracy": _ratio(kind_passes["typo"], kind_totals["typo"]),
        "alternate_accuracy": _ratio(
            kind_passes["alternate"], kind_totals["alternate"]
        ),
        "ambiguous_accuracy": _ratio(
            kind_passes["ambiguous"], kind_totals["ambiguous"]
        ),
        "safe_acronym_accuracy": _ratio(
            kind_passes["safe_acronym"], kind_totals["safe_acronym"]
        ),
        "unknown_accuracy": _ratio(
            kind_passes["unknown"], kind_totals["unknown"]
        ),
        "title_accuracy": _ratio(true_positives + true_negatives, title_total),
        "title_precision": _ratio(
            true_positives,
            true_positives + false_positives,
        ),
        "title_recall": _ratio(
            true_positives,
            true_positives + false_negatives,
        ),
        "negative_rejection_rate": _ratio(
            true_negatives,
            true_negatives + false_positives,
        ),
    }

    thresholds = {
        key: float(value)
        for key, value in benchmark_data.get("thresholds", {}).items()
    }
    threshold_failures = {
        metric: {"actual": metrics.get(metric), "required": required}
        for metric, required in thresholds.items()
        if metrics.get(metric, 0.0) < required
    }

    represented_groups = {
        str(case["expected"].get("soc_major_group"))
        for case in query_cases
        if case["expected"].get("soc_major_group") is not None
    }
    career_spheres = {
        str(case["career_sphere"])
        for case in query_cases
        if case["career_sphere"] not in {"unknown", "cross-sector ambiguity"}
    }
    required_groups = {str(group) for group in benchmark_data["required_major_groups"]}
    coverage_failures: dict[str, Any] = {}
    if len(query_cases) < int(benchmark_data["minimum_queries"]):
        coverage_failures["minimum_queries"] = {
            "actual": len(query_cases),
            "required": int(benchmark_data["minimum_queries"]),
        }
    missing_groups = sorted(required_groups - represented_groups)
    if missing_groups:
        coverage_failures["missing_major_groups"] = missing_groups
    if len(career_spheres) < int(benchmark_data["minimum_career_spheres"]):
        coverage_failures["minimum_career_spheres"] = {
            "actual": len(career_spheres),
            "required": int(benchmark_data["minimum_career_spheres"]),
        }

    counts = {
        "query_cases": len(query_cases),
        "unique_queries": len({case["query"].casefold() for case in query_cases}),
        "seed_occupations": len(benchmark_data["seeds"]),
        "canonical_cases": kind_totals["canonical"],
        "modifier_cases": kind_totals["modifier"],
        "typo_cases": kind_totals["typo"],
        "alternate_cases": kind_totals["alternate"],
        "ambiguous_cases": kind_totals["ambiguous"],
        "safe_acronym_cases": kind_totals["safe_acronym"],
        "unknown_cases": kind_totals["unknown"],
        "title_cases": title_total,
        "positive_title_cases": true_positives + false_negatives,
        "negative_title_cases": true_negatives + false_positives,
        "major_groups": len(represented_groups),
        "career_spheres": len(career_spheres),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "true_negatives": true_negatives,
        "false_negatives": false_negatives,
        "failures": len(failures),
    }

    return {
        "benchmark_version": benchmark_data["version"],
        "passed": not failures and not threshold_failures and not coverage_failures,
        "counts": counts,
        "metrics": metrics,
        "thresholds": thresholds,
        "threshold_failures": threshold_failures,
        "coverage": {
            "represented_major_groups": sorted(represented_groups),
            "career_spheres": sorted(career_spheres),
        },
        "coverage_failures": coverage_failures,
        "failures": failures,
    }


def format_held_out_occupation_evaluation_report(report: dict[str, Any]) -> str:
    counts = report["counts"]
    lines = [
        f"MarketLens held-out occupation evaluation: {'PASS' if report['passed'] else 'FAIL'}",
        (
            f"Queries: {counts['query_cases']} total / {counts['unique_queries']} unique; "
            f"{counts['major_groups']} SOC groups; {counts['career_spheres']} career spheres"
        ),
        (
            f"Title checks: {counts['title_cases']} "
            f"({counts['positive_title_cases']} positive, "
            f"{counts['negative_title_cases']} negative)"
        ),
    ]
    for metric, value in report["metrics"].items():
        required = report["thresholds"].get(metric)
        threshold_text = f" (required {required:.1%})" if required is not None else ""
        lines.append(f"- {metric}: {value:.1%}{threshold_text}")

    if report["coverage_failures"]:
        lines.append(f"Coverage failures: {report['coverage_failures']!r}")
    if report["threshold_failures"]:
        lines.append(f"Threshold failures: {report['threshold_failures']!r}")
    if report["failures"]:
        lines.append("Case failures:")
        for failure in report["failures"]:
            lines.append(
                f"- [{failure['section']}] {failure['id']}: "
                f"expected {failure['expected']!r}, got {failure['actual']!r}"
            )
    else:
        lines.append("No held-out case failures.")
    return "\n".join(lines)
