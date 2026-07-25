import json
from collections import Counter
from pathlib import Path

from app.job_search_evaluation import _candidate_match, _ranking_result


SCENARIO_PATH = (
    Path(__file__).resolve().parents[1]
    / "evaluation"
    / "job_search_integrated_scenarios.json"
)
REQUIRED_SECTORS = {
    "healthcare",
    "education-liberal-arts",
    "science-research",
    "engineering-built-environment",
    "business-finance-operations",
    "legal-public-service",
    "trades-construction-logistics",
    "creative-communications",
    "service-hospitality-transport-agriculture",
}


def _load_scenarios() -> dict[str, object]:
    with SCENARIO_PATH.open(encoding="utf-8") as scenario_file:
        scenarios = json.load(scenario_file)
    assert scenarios["version"] == 1
    return scenarios


def test_integrated_matrix_cannot_shrink_to_narrow_role_only_coverage() -> None:
    scenarios = _load_scenarios()
    declared_sectors = set(scenarios["sectors"])
    candidate_cases = scenarios["candidate_cases"]
    ranking_cases = scenarios["ranking_cases"]

    assert declared_sectors == REQUIRED_SECTORS
    assert len(candidate_cases) == len(REQUIRED_SECTORS) * 3
    assert len(ranking_cases) == len(REQUIRED_SECTORS)

    candidate_sector_counts = Counter(case["sector"] for case in candidate_cases)
    ranking_sector_counts = Counter(case["sector"] for case in ranking_cases)
    assert candidate_sector_counts == Counter({sector: 3 for sector in REQUIRED_SECTORS})
    assert ranking_sector_counts == Counter({sector: 1 for sector in REQUIRED_SECTORS})

    for sector in REQUIRED_SECTORS:
        sector_candidates = [
            case for case in candidate_cases if case["sector"] == sector
        ]
        assert sum(bool(case["expected_match"]) for case in sector_candidates) == 1
        assert sum(not bool(case["expected_match"]) for case in sector_candidates) == 2
        assert all(case.get("level") for case in sector_candidates)
        assert all(case.get("location") for case in sector_candidates)
        assert all(case.get("job_location") for case in sector_candidates)

        sector_ranking = next(
            case for case in ranking_cases if case["sector"] == sector
        )
        assert sector_ranking.get("level")
        assert sector_ranking.get("location")
        assert {candidate["id"] for candidate in sector_ranking["candidates"]} == {
            "exact-local",
            "exact-remote",
            "wrong-local",
        }


def test_integrated_occupation_level_and_location_candidates_all_pass() -> None:
    scenarios = _load_scenarios()
    failures = []

    for case in scenarios["candidate_cases"]:
        predicted_match, actual = _candidate_match(case)
        expected_match = bool(case["expected_match"])
        if predicted_match != expected_match:
            failures.append(
                {
                    "id": case["id"],
                    "sector": case["sector"],
                    "expected_match": expected_match,
                    "actual": actual,
                }
            )

    assert not failures, json.dumps(failures, indent=2, sort_keys=True)


def test_integrated_cross_sector_ranking_prefers_exact_local_work() -> None:
    scenarios = _load_scenarios()
    failures = []

    for case in scenarios["ranking_cases"]:
        passed, actual = _ranking_result(case)
        if not passed:
            failures.append(
                {
                    "id": case["id"],
                    "sector": case["sector"],
                    "expected_best": case["expected_best"],
                    "actual": actual,
                }
            )

    assert not failures, json.dumps(failures, indent=2, sort_keys=True)
