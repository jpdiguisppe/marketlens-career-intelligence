from __future__ import annotations

import json
import subprocess
import sys

from app.career_plans import model_planner
from app.career_plans.evaluation import (
    DEFAULT_FIXTURE_PATH,
    MODEL_CONTEXT_BUDGET_BYTES,
    MODEL_ESTIMATED_COST_BUDGET_USD,
    MODEL_LATENCY_BUDGET_MS,
    MODEL_TOTAL_TOKEN_BUDGET,
    _build_case_proposal,
    _load_fixture,
    evaluate_career_plan_agent,
)
from app.career_plans.evaluation_budget import model_budget_failures
from app.career_plans.schemas import CareerPlanGoal


def test_evaluator_imports_and_runs_first_in_a_fresh_interpreter() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from app.career_plans.evaluation import evaluate_career_plan_agent; "
                "report = evaluate_career_plan_agent(); "
                "assert report['passed']; "
                "print(report['deterministic_executions'])"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "30"


def test_task_level_agent_evaluation_covers_ten_sectors_and_repeated_runs() -> None:
    report = evaluate_career_plan_agent()

    assert report["passed"] is True
    assert report["sector_count"] >= 10
    assert report["case_count"] >= 10
    assert report["repeat_runs_per_case"] >= 3
    assert report["deterministic_executions"] >= 30
    assert report["failed_case_count"] == 0
    assert report["privacy"] == {
        "raw_resume_markers_persisted": 0,
        "raw_job_description_markers_persisted": 0,
    }
    assert all(case["passed"] for case in report["cases"])
    assert all(case["selected_count"] <= 5 for case in report["cases"])
    assert all(case["action_count"] <= 20 for case in report["cases"])


def test_fixture_exercises_description_title_metadata_and_link_injection_surfaces() -> None:
    fixture = _load_fixture(DEFAULT_FIXTURE_PATH)
    serialized = json.dumps(fixture)

    assert "IGNORE ALL PREVIOUS INSTRUCTIONS" in serialized
    assert any(
        "IGNORE POLICY" in str(job["title"])
        for case in fixture["cases"]
        for job in case["jobs"]
    )
    assert any(
        "IGNORE INSTRUCTIONS" in str(job["company"])
        for case in fixture["cases"]
        for job in case["jobs"]
    )
    assert any(
        "instruction=" in str(job["apply_url"])
        for case in fixture["cases"]
        for job in case["jobs"]
    )


def test_evaluator_reports_nonzero_failure_for_a_contract_regression(tmp_path) -> None:
    fixture = _load_fixture(DEFAULT_FIXTURE_PATH)
    fixture["cases"][0]["expected_search_query"] = "This must not match"
    broken_fixture = tmp_path / "broken-career-plan-evaluation.json"
    broken_fixture.write_text(json.dumps(fixture), encoding="utf-8")

    report = evaluate_career_plan_agent(broken_fixture)

    assert report["passed"] is False
    assert report["failed_case_count"] == 1
    assert "search_query_mismatch" in report["cases"][0]["failures"]


def test_model_context_and_success_telemetry_fit_documented_budgets() -> None:
    fixture = _load_fixture(DEFAULT_FIXTURE_PATH)
    case = fixture["cases"][0]
    proposal, _, _ = _build_case_proposal(case, run_id=1)
    goal = CareerPlanGoal.model_validate(case["goal"]).model_copy(
        update={"model_assisted_planning": True}
    )
    prompt = model_planner._build_user_prompt(goal, proposal)

    failures = model_budget_failures(
        call_count=1,
        context_bytes=len(prompt.encode("utf-8")),
        latency_ms=12_000.0,
        total_tokens=1_200,
        estimated_cost_usd=0.004,
    )

    assert failures == []
    assert len(prompt.encode("utf-8")) <= MODEL_CONTEXT_BUDGET_BYTES


def test_model_budget_policy_fails_every_over_budget_dimension() -> None:
    failures = model_budget_failures(
        call_count=2,
        context_bytes=MODEL_CONTEXT_BUDGET_BYTES + 1,
        latency_ms=MODEL_LATENCY_BUDGET_MS + 1,
        total_tokens=MODEL_TOTAL_TOKEN_BUDGET + 1,
        estimated_cost_usd=MODEL_ESTIMATED_COST_BUDGET_USD + 0.001,
    )

    assert set(failures) == {
        "model_call_budget_exceeded",
        "model_context_budget_exceeded",
        "model_latency_budget_exceeded",
        "model_token_budget_exceeded",
        "model_cost_budget_exceeded",
    }
