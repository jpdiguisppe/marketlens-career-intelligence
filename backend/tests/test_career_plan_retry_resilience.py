from __future__ import annotations

import json
from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.career_plans.evaluation import (
    DEFAULT_FIXTURE_PATH,
    _candidate,
    _load_fixture,
    _safe_fit_result,
)
from app.career_plans.models import CareerPlanAuditEventDB, CareerPlanRunDB
from app.career_plans.orchestrator import execute_career_plan
from app.career_plans.schemas import (
    CAREER_PLAN_SCHEMA_VERSION,
    CareerPlanExecuteRequest,
    CareerPlanGoal,
)
from app.career_plans.tools.job_search_tool import CareerPlanSearchToolOutput
from app.career_plans.tools.smart_fit_tool import (
    CareerPlanSmartFitToolError,
    CareerPlanSmartFitToolOutput,
)
from app.database import Base
from app.job_search import JobSearchResults

TEST_DATABASE_URL = "sqlite://"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine)


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _case() -> dict[str, object]:
    return _load_fixture(DEFAULT_FIXTURE_PATH)["cases"][0]


def _create_run(db: Session, case: dict[str, object]) -> CareerPlanRunDB:
    goal = CareerPlanGoal.model_validate(case["goal"])
    run = CareerPlanRunDB(
        user_id="retry-test-user",
        status="draft",
        schema_version=CAREER_PLAN_SCHEMA_VERSION,
        run_version=1,
        goal_json="{}",
        search_summary_json="{}",
        proposal_json="{}",
        approval_json="{}",
    )
    run.goal = goal.model_dump(mode="json")
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _tool_outputs(
    case: dict[str, object],
) -> tuple[CareerPlanSearchToolOutput, CareerPlanSmartFitToolOutput]:
    jobs = list(case["jobs"])
    candidates = [
        _candidate(case, job, rank)
        for rank, job in enumerate(jobs, start=1)
    ]
    raw = JobSearchResults(
        query=str(case["expected_search_query"]),
        location=str(case["expected_search_location"]),
        level=str(case["goal"]["experience_level"]),
        role_family="software",
        industry=None,
        providers_searched=sorted({candidate.job.source for candidate in candidates}),
        source_coverage=[],
        results=[candidate.job for candidate in candidates],
        warnings=[],
        search_suggestions=[],
        external_search_links=[],
    )
    search_output = CareerPlanSearchToolOutput(
        raw=raw,
        candidates=candidates,
        safe_summary={
            "tool_name": "career.search_jobs.v1",
            "query": raw.query,
            "location": raw.location,
            "level": raw.level,
            "role_family": raw.role_family,
            "industry": raw.industry,
            "providers_searched": raw.providers_searched,
            "source_coverage": [],
            "candidate_count": len(candidates),
            "candidates": [candidate.safe_metadata() for candidate in candidates],
            "warnings": [],
            "search_suggestions": [],
            "safe_status_code": "ok",
        },
        safe_status_code="ok",
    )
    jobs_by_id = {str(job["id"]): job for job in jobs}
    ranked = sorted(
        candidates,
        key=lambda candidate: (
            -int(jobs_by_id[candidate.job.id]["score"]),
            -float(jobs_by_id[candidate.job.id]["confidence"]),
            candidate.search_rank,
            candidate.job_ref,
        ),
    )
    results = [
        _safe_fit_result(case, candidate, jobs_by_id[candidate.job.id], rank)
        for rank, candidate in enumerate(ranked, start=1)
    ]
    smart_fit_output = CareerPlanSmartFitToolOutput(
        results=results,
        safe_summary={
            "tool_name": "career.smart_fit_batch.v1",
            "analyzed_count": len(results),
            "results": [result.safe_summary for result in results],
            "safe_status_code": "ok",
        },
        safe_status_code="ok",
    )
    return search_output, smart_fit_output


def _assert_clean_recovered_plan(db: Session, run: CareerPlanRunDB, case: dict[str, object]) -> None:
    db.refresh(run)
    assert run.status == "awaiting_approval"
    assert run.attempt_count == 2
    actions = run.proposal["actions"]
    action_ids = [action["id"] for action in actions]
    assert len(action_ids) == len(set(action_ids))
    assert all(action["status"] == "proposed" for action in actions)
    assert {step.attempt for step in run.steps} == {1, 2}
    assert sum(event.event_type == "proposal_ready" for event in run.audit_events) == 1
    serialized = json.dumps(
        {
            "search_summary": run.search_summary,
            "proposal": run.proposal,
            "audit": [event.safe_payload for event in run.audit_events],
        },
        sort_keys=True,
    )
    assert str(case["private_resume_marker"]) not in serialized
    assert str(case["private_job_marker"]) not in serialized


def test_cancelled_run_retries_to_complete_plan_without_duplicate_actions() -> None:
    case = _case()
    search_output, smart_fit_output = _tool_outputs(case)
    resume_text = f"{case['private_resume_marker']} Python SQL REST API project evidence."

    with TestingSessionLocal() as db:
        run = _create_run(db, case)

        def search_and_request_cancellation(goal: CareerPlanGoal) -> CareerPlanSearchToolOutput:
            with TestingSessionLocal() as other_db:
                persisted = other_db.get(CareerPlanRunDB, run.id)
                assert persisted is not None
                persisted.cancel_requested_at = datetime.now(timezone.utc)
                other_db.commit()
            return search_output

        cancelled = execute_career_plan(
            db,
            run,
            CareerPlanExecuteRequest(resume_text=resume_text, expected_run_version=run.run_version),
            search_tool=search_and_request_cancellation,
            smart_fit_tool=lambda resume, selected: smart_fit_output,
        )
        assert cancelled.status == "cancelled"
        assert cancelled.attempt_count == 1
        assert cancelled.safe_error_code == "cancelled_by_user"

        recovered = execute_career_plan(
            db,
            cancelled,
            CareerPlanExecuteRequest(
                resume_text=resume_text,
                expected_run_version=cancelled.run_version,
            ),
            search_tool=lambda goal: search_output,
            smart_fit_tool=lambda resume, selected: smart_fit_output,
        )
        _assert_clean_recovered_plan(db, recovered, case)


def test_failed_run_retries_to_complete_plan_without_corrupted_state() -> None:
    case = _case()
    search_output, smart_fit_output = _tool_outputs(case)
    resume_text = f"{case['private_resume_marker']} Python SQL REST API project evidence."

    with TestingSessionLocal() as db:
        run = _create_run(db, case)

        def fail_smart_fit(resume: str, selected: list[object]) -> CareerPlanSmartFitToolOutput:
            raise CareerPlanSmartFitToolError(
                "smart_fit_failure",
                "Raw provider failure detail must not survive.",
            )

        failed = execute_career_plan(
            db,
            run,
            CareerPlanExecuteRequest(resume_text=resume_text, expected_run_version=run.run_version),
            search_tool=lambda goal: search_output,
            smart_fit_tool=fail_smart_fit,
        )
        assert failed.status == "failed"
        assert failed.attempt_count == 1
        assert failed.safe_error_code == "smart_fit_failure"
        assert "Raw provider failure detail" not in json.dumps(
            [event.safe_payload for event in failed.audit_events]
        )

        recovered = execute_career_plan(
            db,
            failed,
            CareerPlanExecuteRequest(
                resume_text=resume_text,
                expected_run_version=failed.run_version,
            ),
            search_tool=lambda goal: search_output,
            smart_fit_tool=lambda resume, selected: smart_fit_output,
        )
        _assert_clean_recovered_plan(db, recovered, case)

        event_types = [
            event.event_type
            for event in db.query(CareerPlanAuditEventDB)
            .filter(CareerPlanAuditEventDB.run_id == recovered.id)
            .order_by(CareerPlanAuditEventDB.sequence_number)
        ]
        assert event_types.count("execution_failed") == 1
        assert event_types.count("proposal_ready") == 1
