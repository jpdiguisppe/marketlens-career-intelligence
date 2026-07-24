import json

from app.job_search_evaluation import (
    evaluate_job_search_benchmark,
    load_job_search_benchmark,
)


def test_job_search_benchmark_has_meaningful_minimum_coverage() -> None:
    benchmark = load_job_search_benchmark()

    assert len(benchmark["intent_cases"]) >= 20
    assert len(benchmark["candidate_cases"]) >= 40
    assert len(benchmark["routing_cases"]) >= 9

    positive_candidates = sum(
        bool(case["expected_match"]) for case in benchmark["candidate_cases"]
    )
    negative_candidates = len(benchmark["candidate_cases"]) - positive_candidates
    critical_cases = sum(
        bool(case.get("critical", False))
        for section in ("intent_cases", "candidate_cases", "routing_cases")
        for case in benchmark[section]
    )

    assert positive_candidates >= 20
    assert negative_candidates >= 20
    assert critical_cases >= 10


def test_job_search_benchmark_meets_recall_precision_and_routing_thresholds() -> None:
    report = evaluate_job_search_benchmark()

    assert report["passed"], json.dumps(report, indent=2, sort_keys=True)
    assert report["counts"]["critical_failures"] == 0
    assert report["metrics"]["intent_accuracy"] == 1.0
    assert report["metrics"]["routing_accuracy"] == 1.0
