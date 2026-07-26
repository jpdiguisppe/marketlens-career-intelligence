from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.analysis.semantic_benchmark_suite import load_semantic_extraction_suite
from app.analysis.semantic_evaluation import (
    evaluate_semantic_extraction_benchmark,
    format_semantic_extraction_report,
    load_semantic_extraction_benchmark,
)


def test_semantic_extraction_benchmark_passes() -> None:
    benchmark = load_semantic_extraction_suite()
    report = evaluate_semantic_extraction_benchmark(benchmark)

    assert report["passed"], format_semantic_extraction_report(report)
    assert report["counts"]["cases"] >= 8
    assert report["counts"]["sectors"] >= 8
    assert report["counts"]["critical_cases"] >= 4
    assert report["counts"]["expected_requirements"] >= 26
    assert report["metrics"]["baseline_requirement_recall"] > 0
    assert report["metrics"]["baseline_requirement_recall"] < 1.0
    assert report["metrics"]["model_requirement_recall"] == 1.0
    assert report["metrics"]["model_requirement_precision"] == 1.0
    assert report["metrics"]["merged_requirement_recall"] == 1.0
    assert report["metrics"]["requirement_type_accuracy"] == 1.0
    assert report["metrics"]["semantic_category_accuracy"] == 1.0
    assert report["metrics"]["evidence_status_accuracy"] == 1.0
    assert report["metrics"]["hard_constraint_accuracy"] == 1.0
    assert report["metrics"]["grounding_pass_rate"] == 1.0
    assert report["metrics"]["critical_case_pass_rate"] == 1.0
    assert report["metrics"]["semantic_recall_gain"] > 0


def test_semantic_benchmark_rejects_silent_case_removal(tmp_path: Path) -> None:
    benchmark = load_semantic_extraction_benchmark()
    benchmark["cases"] = benchmark["cases"][:2]
    path = tmp_path / "semantic-benchmark.json"
    path.write_text(json.dumps(benchmark), encoding="utf-8")

    with pytest.raises(ValueError, match="case count"):
        load_semantic_extraction_benchmark(path)


def test_combined_suite_includes_overlap_sectors() -> None:
    benchmark = load_semantic_extraction_suite()
    sectors = {case["sector"] for case in benchmark["cases"]}

    assert {"data", "devops"}.issubset(sectors)
    assert len(benchmark["cases"]) >= benchmark["minimums"]["cases"]


def test_semantic_report_displays_baseline_comparison() -> None:
    report = evaluate_semantic_extraction_benchmark(
        load_semantic_extraction_suite()
    )
    formatted = format_semantic_extraction_report(report)

    assert "baseline_requirement_recall" in formatted
    assert "merged_requirement_recall" in formatted
    assert "semantic_recall_gain" in formatted
