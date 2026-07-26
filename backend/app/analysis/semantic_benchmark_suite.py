from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.analysis.model_extractor import MODEL_ASSISTED_SCHEMA_VERSION
from app.analysis.semantic_evaluation import (
    DEFAULT_SEMANTIC_BENCHMARK_PATH,
    load_semantic_extraction_benchmark,
)

OVERLAP_BENCHMARK_PATH = (
    Path(__file__).resolve().parents[2]
    / "evaluation"
    / "semantic_extraction_overlap_cases.json"
)


def load_semantic_extraction_suite() -> dict[str, Any]:
    """Load the validated semantic-gap set plus deterministic-overlap cases."""

    base = load_semantic_extraction_benchmark(DEFAULT_SEMANTIC_BENCHMARK_PATH)
    with OVERLAP_BENCHMARK_PATH.open(encoding="utf-8") as benchmark_file:
        overlap = json.load(benchmark_file)

    if overlap.get("version") != 1:
        raise ValueError("Unsupported semantic overlap benchmark version.")
    if overlap.get("contract_version") != MODEL_ASSISTED_SCHEMA_VERSION:
        raise ValueError("Semantic overlap contract version does not match the extractor.")
    overlap_cases = overlap.get("cases")
    if not isinstance(overlap_cases, list) or not overlap_cases:
        raise ValueError("Semantic overlap benchmark cases must be non-empty.")

    combined = dict(base)
    combined["cases"] = [*base["cases"], *overlap_cases]
    combined["minimums"] = {
        "cases": 8,
        "sectors": 8,
        "critical_cases": 4,
    }

    case_ids = [str(case.get("id") or "").strip() for case in combined["cases"]]
    sectors = {str(case.get("sector") or "").strip() for case in combined["cases"]}
    critical_cases = sum(bool(case.get("critical", False)) for case in combined["cases"])

    if any(not case_id for case_id in case_ids):
        raise ValueError("Every combined semantic benchmark case must have an id.")
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Combined semantic benchmark case ids must be unique.")
    if len(combined["cases"]) < combined["minimums"]["cases"]:
        raise ValueError("Combined semantic benchmark case count fell below its minimum.")
    if len(sectors) < combined["minimums"]["sectors"]:
        raise ValueError("Combined semantic benchmark sector coverage fell below its minimum.")
    if critical_cases < combined["minimums"]["critical_cases"]:
        raise ValueError("Combined semantic benchmark critical case count fell below its minimum.")

    return combined
