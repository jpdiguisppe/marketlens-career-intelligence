from app.analysis.evaluation import (
    evaluate_smart_fit_benchmark,
    load_smart_fit_benchmark,
)


def test_smart_fit_benchmark_has_permanent_breadth_guards() -> None:
    benchmark = load_smart_fit_benchmark()

    assert len(benchmark["cases"]) >= benchmark["minimums"]["cases"]
    assert len({case["sector"] for case in benchmark["cases"]}) >= benchmark["minimums"]["sectors"]
    assert sum(bool(case.get("critical")) for case in benchmark["cases"]) >= benchmark["minimums"]["critical_cases"]
    assert len({case["id"] for case in benchmark["cases"]}) == len(benchmark["cases"])


def test_deterministic_smart_fit_baseline_passes() -> None:
    report = evaluate_smart_fit_benchmark()

    assert report["passed"], report["failures"]
    assert report["metrics"]["critical_case_pass_rate"] == 1.0
    assert not report["threshold_failures"]
