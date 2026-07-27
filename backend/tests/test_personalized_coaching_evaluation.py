from app.analysis.coaching_evaluation import evaluate_personalized_coaching


def test_personalized_coaching_benchmark_passes_all_gates() -> None:
    report = evaluate_personalized_coaching()

    assert report["passed"] is True
    assert report["failures"] == []
    assert report["version"] == "8d.1"
    assert report["counts"]["critical_rejection_checks"] == 5
    assert report["counts"]["grounded_actions"] == 3
    assert all(value == 1.0 for value in report["metrics"].values())
