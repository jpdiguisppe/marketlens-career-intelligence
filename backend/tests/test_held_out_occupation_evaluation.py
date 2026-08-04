from __future__ import annotations

from app.held_out_occupation_evaluation import (
    evaluate_held_out_occupation_benchmark,
    expand_held_out_query_cases,
    load_held_out_occupation_benchmark,
)


def test_held_out_occupation_manifest_meets_coverage_contract() -> None:
    benchmark = load_held_out_occupation_benchmark()
    cases = expand_held_out_query_cases(benchmark)

    assert len(cases) >= benchmark["minimum_queries"]
    assert len({case["query"].casefold() for case in cases}) >= 250
    assert len({seed["soc_major_group"] for seed in benchmark["seeds"]}) == 23
    assert len({seed["career_sphere"] for seed in benchmark["seeds"]}) >= 12
    assert len(benchmark["alternate_query_cases"]) >= 46
    assert {
        alternate["soc_major_group"]
        for alternate in benchmark["alternate_query_cases"]
    } == set(benchmark["required_major_groups"])
    assert len(benchmark["ambiguous_acronyms"]) >= 30
    assert len({case["id"] for case in cases}) == len(cases)


def test_held_out_occupation_benchmark_passes() -> None:
    report = evaluate_held_out_occupation_benchmark()

    assert report["passed"], report
    assert report["counts"]["query_cases"] >= 250
    assert report["counts"]["major_groups"] == 23
    assert report["counts"]["career_spheres"] >= 12
    assert report["counts"]["alternate_cases"] >= 46
    assert report["counts"]["title_cases"] >= 90
    assert report["metrics"]["alternate_accuracy"] == 1.0
    assert report["metrics"]["ambiguous_accuracy"] == 1.0
    assert report["metrics"]["negative_rejection_rate"] == 1.0
