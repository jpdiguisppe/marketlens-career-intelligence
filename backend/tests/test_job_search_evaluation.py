import json
from collections import Counter

from app.job_search_evaluation import (
    evaluate_job_search_benchmark,
    load_job_search_benchmark,
)


REQUIRED_CROSS_SECTOR_CATEGORIES = {
    "cross-sector-business-finance-operations",
    "cross-sector-creative-communications",
    "cross-sector-education-liberal-arts",
    "cross-sector-engineering-built-environment",
    "cross-sector-healthcare",
    "cross-sector-legal-public-service",
    "cross-sector-science-research",
    "cross-sector-service-hospitality-transport-agriculture",
    "cross-sector-trades-construction-logistics",
}


def test_job_search_benchmark_has_meaningful_minimum_coverage() -> None:
    benchmark = load_job_search_benchmark()

    assert len(benchmark["intent_cases"]) >= 20
    assert len(benchmark["candidate_cases"]) >= 250
    assert len(benchmark["location_cases"]) >= 15
    assert len(benchmark["ranking_cases"]) >= 15
    assert len(benchmark["routing_cases"]) >= 9

    positive_candidates = sum(
        bool(case["expected_match"]) for case in benchmark["candidate_cases"]
    )
    negative_candidates = len(benchmark["candidate_cases"]) - positive_candidates
    critical_cases = sum(
        bool(case.get("critical", False))
        for section in (
            "intent_cases",
            "candidate_cases",
            "location_cases",
            "ranking_cases",
            "routing_cases",
        )
        for case in benchmark[section]
    )

    assert positive_candidates >= 125
    assert negative_candidates >= 125
    assert critical_cases >= 50

    cross_sector_categories = {
        case.get("category")
        for case in benchmark["candidate_cases"]
        if str(case.get("category") or "").startswith("cross-sector-")
    }
    assert cross_sector_categories == REQUIRED_CROSS_SECTOR_CATEGORIES


def test_each_required_sector_has_diverse_positive_negative_and_critical_cases() -> None:
    benchmark = load_job_search_benchmark()
    cross_sector_cases = [
        case
        for case in benchmark["candidate_cases"]
        if case.get("category") in REQUIRED_CROSS_SECTOR_CATEGORIES
    ]

    category_counts = Counter(case["category"] for case in cross_sector_cases)
    assert set(category_counts) == REQUIRED_CROSS_SECTOR_CATEGORIES

    for category in REQUIRED_CROSS_SECTOR_CATEGORIES:
        cases = [case for case in cross_sector_cases if case["category"] == category]
        positive_cases = [case for case in cases if bool(case["expected_match"])]
        negative_cases = [case for case in cases if not bool(case["expected_match"])]
        unique_queries = {str(case["query"]).strip().lower() for case in cases}
        critical_cases = [case for case in cases if bool(case.get("critical", False))]

        assert len(cases) >= 12, category
        assert len(positive_cases) >= 6, category
        assert len(negative_cases) >= 6, category
        assert len(unique_queries) >= 6, category
        assert len(critical_cases) >= 2, category


def test_benchmark_preserves_level_and_location_contracts() -> None:
    benchmark = load_job_search_benchmark()

    candidate_levels = {
        str(case.get("level") or "any") for case in benchmark["candidate_cases"]
    }
    assert {"any", "intern", "entry", "mid", "senior"}.issubset(candidate_levels)

    location_constrained_candidates = [
        case
        for case in benchmark["candidate_cases"]
        if "location" in case and "job_location" in case
    ]
    assert len(location_constrained_candidates) >= 4
    assert {
        "correctness-electrical-engineer-local-positive",
        "correctness-electrical-engineer-analytics-negative",
        "correctness-electrical-engineer-remote-negative",
        "correctness-electrical-engineer-marketing-negative",
    }.issubset({case["id"] for case in location_constrained_candidates})


def test_job_search_benchmark_meets_recall_precision_and_routing_thresholds() -> None:
    report = evaluate_job_search_benchmark()

    assert report["passed"], json.dumps(report, indent=2, sort_keys=True)
    assert report["counts"]["critical_failures"] == 0
    assert report["metrics"]["intent_accuracy"] == 1.0
    assert report["metrics"]["routing_accuracy"] == 1.0
