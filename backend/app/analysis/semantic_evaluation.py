from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import app.analysis.service as service
from app.analysis.evidence import extract_resume_evidence
from app.analysis.model_extractor import (
    MODEL_ASSISTED_SCHEMA_VERSION,
    ModelAssistedExtractionError,
    _validate_provider_extraction,
)
from app.analysis.normalization import normalize_document_text
from app.analysis.requirements import extract_job_requirements
from app.analysis.section_parser import parse_job_sections, parse_resume_sections
from app.analysis.semantic_merge_patch import install_semantic_merge_patch

DEFAULT_SEMANTIC_BENCHMARK_PATH = (
    Path(__file__).resolve().parents[2]
    / "evaluation"
    / "semantic_extraction_benchmark.json"
)

_WHITESPACE = re.compile(r"\s+")


def _key(value: str) -> str:
    return _WHITESPACE.sub(" ", value.strip()).casefold()


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


def load_semantic_extraction_benchmark(
    path: Path | None = None,
) -> dict[str, Any]:
    benchmark_path = path or DEFAULT_SEMANTIC_BENCHMARK_PATH
    with benchmark_path.open(encoding="utf-8") as benchmark_file:
        benchmark = json.load(benchmark_file)

    if benchmark.get("version") != 1:
        raise ValueError("Unsupported semantic extraction benchmark version.")
    if benchmark.get("contract_version") != MODEL_ASSISTED_SCHEMA_VERSION:
        raise ValueError("Semantic benchmark contract version does not match the extractor.")

    cases = benchmark.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Semantic extraction benchmark cases must be a non-empty list.")

    case_ids: list[str] = []
    sectors: set[str] = set()
    critical_cases = 0
    for case in cases:
        case_id = str(case.get("id") or "").strip()
        sector = str(case.get("sector") or "").strip()
        if not case_id:
            raise ValueError("Every semantic benchmark case must have an id.")
        if not sector:
            raise ValueError(f"Semantic benchmark case {case_id!r} must have a sector.")
        if not isinstance(case.get("provider_output"), dict):
            raise ValueError(f"Semantic benchmark case {case_id!r} needs provider_output.")
        if not isinstance(case.get("expected"), dict):
            raise ValueError(f"Semantic benchmark case {case_id!r} needs expected output.")
        case_ids.append(case_id)
        sectors.add(sector)
        critical_cases += int(bool(case.get("critical", False)))

    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Semantic benchmark case ids must be unique.")

    minimums = benchmark.get("minimums", {})
    if len(cases) < int(minimums.get("cases", 1)):
        raise ValueError("Semantic benchmark case count fell below its minimum.")
    if len(sectors) < int(minimums.get("sectors", 1)):
        raise ValueError("Semantic benchmark sector coverage fell below its minimum.")
    if critical_cases < int(minimums.get("critical_cases", 0)):
        raise ValueError("Semantic benchmark critical case count fell below its minimum.")

    return benchmark


def evaluate_semantic_extraction_benchmark(
    benchmark: dict[str, Any] | None = None,
) -> dict[str, Any]:
    install_semantic_merge_patch()
    benchmark_data = benchmark or load_semantic_extraction_benchmark()
    failures: list[dict[str, Any]] = []
    counters: dict[str, int] = defaultdict(int)
    sector_results: dict[str, list[bool]] = defaultdict(list)

    for case in benchmark_data["cases"]:
        expected = case["expected"]
        case_failure_count = len(failures)
        normalized_resume = normalize_document_text(case["resume_text"])
        normalized_job = normalize_document_text(case["job_description"])

        deterministic_requirements = extract_job_requirements(
            parse_job_sections(normalized_job)
        )
        deterministic_evidence = extract_resume_evidence(
            parse_resume_sections(normalized_resume)
        )

        expected_requirements = {
            _key(item["skill"]): item for item in expected.get("requirements", [])
        }
        expected_keys = set(expected_requirements)
        deterministic_keys = {_key(item.skill) for item in deterministic_requirements}
        counters["expected_requirements"] += len(expected_keys)
        counters["baseline_requirement_hits"] += len(
            expected_keys & deterministic_keys
        )

        try:
            extraction = _validate_provider_extraction(
                json.dumps(case["provider_output"]),
                resume_text=normalized_resume,
                job_description=normalized_job,
            )
            counters["grounding_pass"] += 1
        except ModelAssistedExtractionError as exc:
            counters["grounding_total"] += 1
            failures.append(
                _failure(
                    case=case,
                    check="provider_schema_and_grounding",
                    expected="valid grounded extraction",
                    actual=str(exc),
                )
            )
            sector_results[case["sector"]].append(False)
            continue

        counters["grounding_total"] += 1
        model_requirements = {
            _key(item.skill): item for item in extraction.job_requirements
        }
        model_keys = set(model_requirements)
        counters["model_requirement_tp"] += len(model_keys & expected_keys)
        counters["model_requirement_fp"] += len(model_keys - expected_keys)
        counters["model_requirement_fn"] += len(expected_keys - model_keys)

        if model_keys != expected_keys:
            failures.append(
                _failure(
                    case=case,
                    check="model_requirement_set",
                    expected=sorted(item["skill"] for item in expected_requirements.values()),
                    actual=sorted(item.skill for item in model_requirements.values()),
                )
            )

        for requirement_key, expected_requirement in expected_requirements.items():
            actual = model_requirements.get(requirement_key)
            counters["requirement_type_total"] += 1
            type_passed = bool(
                actual
                and actual.requirement_type.value == expected_requirement["type"]
            )
            counters["requirement_type_pass"] += int(type_passed)
            if not type_passed:
                failures.append(
                    _failure(
                        case=case,
                        check=f"requirement_type:{expected_requirement['skill']}",
                        expected=expected_requirement["type"],
                        actual=actual.requirement_type.value if actual else None,
                    )
                )

            counters["semantic_category_total"] += 1
            category_passed = bool(
                actual
                and actual.semantic_category.value
                == expected_requirement["semantic_category"]
            )
            counters["semantic_category_pass"] += int(category_passed)
            if not category_passed:
                failures.append(
                    _failure(
                        case=case,
                        check=f"semantic_category:{expected_requirement['skill']}",
                        expected=expected_requirement["semantic_category"],
                        actual=actual.semantic_category.value if actual else None,
                    )
                )

        merged_requirements, merged_evidence = service._merge_model_extraction(
            deterministic_requirements,
            deterministic_evidence,
            extraction,
        )
        merged_keys = {_key(item.skill) for item in merged_requirements}
        counters["merged_requirement_hits"] += len(expected_keys & merged_keys)

        for evidence_expectation in expected.get("evidence", []):
            counters["evidence_status_total"] += 1
            actual_evidence = next(
                (
                    item
                    for skill, item in merged_evidence.items()
                    if _key(skill) == _key(evidence_expectation["skill"])
                ),
                None,
            )
            actual_status = actual_evidence.status.value if actual_evidence else None
            passed = actual_status == evidence_expectation["status"]
            counters["evidence_status_pass"] += int(passed)
            if not passed:
                failures.append(
                    _failure(
                        case=case,
                        check=f"evidence_status:{evidence_expectation['skill']}",
                        expected=evidence_expectation["status"],
                        actual=actual_status,
                    )
                )

        actual_hard_categories = {
            constraint.category for constraint in extraction.hard_constraints
        }
        expected_hard_categories = {
            item["category"] for item in expected.get("hard_constraints", [])
        }
        counters["hard_constraint_total"] += len(expected_hard_categories)
        counters["hard_constraint_pass"] += len(
            actual_hard_categories & expected_hard_categories
        )
        if actual_hard_categories != expected_hard_categories:
            failures.append(
                _failure(
                    case=case,
                    check="hard_constraint_categories",
                    expected=sorted(expected_hard_categories),
                    actual=sorted(actual_hard_categories),
                )
            )

        case_passed = len(failures) == case_failure_count
        counters["case_pass"] += int(case_passed)
        sector_results[case["sector"]].append(case_passed)

    case_count = len(benchmark_data["cases"])
    critical_ids = {
        case["id"] for case in benchmark_data["cases"] if case.get("critical", False)
    }
    critical_failures = [
        failure for failure in failures if failure["id"] in critical_ids
    ]
    expected_total = counters["expected_requirements"]

    metrics = {
        "baseline_requirement_recall": _ratio(
            counters["baseline_requirement_hits"], expected_total
        ),
        "model_requirement_recall": _ratio(
            counters["model_requirement_tp"],
            counters["model_requirement_tp"] + counters["model_requirement_fn"],
        ),
        "model_requirement_precision": _ratio(
            counters["model_requirement_tp"],
            counters["model_requirement_tp"] + counters["model_requirement_fp"],
        ),
        "merged_requirement_recall": _ratio(
            counters["merged_requirement_hits"], expected_total
        ),
        "requirement_type_accuracy": _ratio(
            counters["requirement_type_pass"], counters["requirement_type_total"]
        ),
        "semantic_category_accuracy": _ratio(
            counters["semantic_category_pass"], counters["semantic_category_total"]
        ),
        "evidence_status_accuracy": _ratio(
            counters["evidence_status_pass"], counters["evidence_status_total"]
        ),
        "hard_constraint_accuracy": _ratio(
            counters["hard_constraint_pass"], counters["hard_constraint_total"]
        ),
        "grounding_pass_rate": _ratio(
            counters["grounding_pass"], counters["grounding_total"]
        ),
        "critical_case_pass_rate": _ratio(
            len(critical_ids) - len({failure["id"] for failure in critical_failures}),
            len(critical_ids),
        ),
    }
    metrics["semantic_recall_gain"] = (
        metrics["merged_requirement_recall"]
        - metrics["baseline_requirement_recall"]
    )

    thresholds = {
        key: float(value)
        for key, value in benchmark_data.get("thresholds", {}).items()
    }
    threshold_failures = {
        metric: {"actual": metrics.get(metric), "required": required}
        for metric, required in thresholds.items()
        if metrics.get(metric, 0.0) < required
    }

    return {
        "benchmark_version": benchmark_data["version"],
        "contract_version": benchmark_data["contract_version"],
        "passed": not failures and not threshold_failures,
        "counts": {
            "cases": case_count,
            "sectors": len(sector_results),
            "critical_cases": len(critical_ids),
            "expected_requirements": expected_total,
            "evidence_checks": counters["evidence_status_total"],
            "hard_constraint_checks": counters["hard_constraint_total"],
            "failures": len(failures),
        },
        "metrics": metrics,
        "thresholds": thresholds,
        "threshold_failures": threshold_failures,
        "sector_accuracy": {
            sector: _ratio(sum(results), len(results))
            for sector, results in sorted(sector_results.items())
        },
        "failures": failures,
    }


def format_semantic_extraction_report(report: dict[str, Any]) -> str:
    lines = [
        f"MarketLens semantic extraction benchmark: {'PASS' if report['passed'] else 'FAIL'}",
        (
            f"Contract {report['contract_version']} | "
            f"{report['counts']['cases']} cases across "
            f"{report['counts']['sectors']} sectors"
        ),
        (
            f"Checks: {report['counts']['expected_requirements']} requirements, "
            f"{report['counts']['evidence_checks']} evidence, "
            f"{report['counts']['hard_constraint_checks']} hard constraints"
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
                f"- {failure['id']}{critical} [{failure['check']}]: "
                f"expected {failure['expected']!r}, got {failure['actual']!r}"
            )
    else:
        lines.append("No semantic benchmark failures.")

    return "\n".join(lines)
