from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.analysis.semantic_evaluation import (
    evaluate_semantic_extraction_benchmark,
    format_semantic_extraction_report,
    load_semantic_extraction_benchmark,
)


def test_semantic_extraction_benchmark_passes() -> None:
    report = evaluate_semantic_extraction_benchmark()

    assert report["passed"], format_semantic_extraction_report(report)
    assert report["counts"]["cases"] >= 6
    assert report["counts"]["sectors"] >= 6
    assert report["counts"]["critical_cases"] >= 3
    assert report["counts"]["expected_requirements"] >= 18
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


def test_semantic_report_displays_baseline_comparison() -> None:
    report = evaluate_semantic_extraction_benchmark()
    formatted = format_semantic_extraction_report(report)

    assert "baseline_requirement_recall" in formatted
    assert "merged_requirement_recall" in formatted
    assert "semantic_recall_gain" in formatted
