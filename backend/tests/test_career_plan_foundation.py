import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["AUTH_DEV_MODE"] = "true"
os.environ["AUTH_DEV_BEARER_TOKEN"] = "test-user-token"
os.environ["AUTH_DEV_USER_ID"] = "test-clerk-user-1"

from app.career_plans.models import CareerPlanAuditEventDB, CareerPlanRunDB, CareerPlanStepDB
from app.career_plans.router import _validate_safe_audit_payload
from app.career_plans.schemas import CareerPlanRunStatus
from app.career_plans.state_machine import InvalidCareerPlanTransition, ensure_run_transition
from app.database import Base, get_db
from app.main import app

AUTH_HEADERS = {"Authorization": "Bearer test-user-token"}
TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine)
client = TestClient(app)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def reset_career_plan_database(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setenv("AUTH_DEV_USER_ID", "test-clerk-user-1")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if previous_override is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous_override


def _career_plan_payload(idempotency_key: str = "career-plan-create-1") -> dict[str, object]:
    return {
        "goal": {
            "target_occupation": "Software Engineer",
            "experience_level": "entry",
            "industry": "healthcare",
            "location": "Philadelphia, PA",
            "work_mode": "hybrid",
            "portfolio_strategy": "balanced",
            "max_jobs_to_analyze": 5,
            "model_assisted_planning": False,
        },
        "idempotency_key": idempotency_key,
    }


def _create_plan(idempotency_key: str = "career-plan-create-1") -> dict[str, object]:
    response = client.post(
        "/career-plans",
        json=_career_plan_payload(idempotency_key),
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_state_machine_allows_only_documented_transitions() -> None:
    assert ensure_run_transition("draft", "running") == CareerPlanRunStatus.RUNNING
    assert ensure_run_transition("running", "awaiting_approval") == CareerPlanRunStatus.AWAITING_APPROVAL
    assert ensure_run_transition("awaiting_approval", "approved") == CareerPlanRunStatus.APPROVED

    with pytest.raises(InvalidCareerPlanTransition):
        ensure_run_transition("draft", "approved")

    with pytest.raises(InvalidCareerPlanTransition):
        ensure_run_transition("approved", "running")


def test_career_plan_routes_require_authentication() -> None:
    assert client.get("/career-plans").status_code == 401
    assert client.post("/career-plans", json=_career_plan_payload()).status_code == 401


def test_create_list_and_idempotent_replay_store_only_safe_state() -> None:
    first = _create_plan()
    second = _create_plan()

    assert first["id"] == second["id"]
    assert first["status"] == "draft"
    assert first["run_version"] == 1
    assert first["goal"]["target_occupation"] == "Software Engineer"
    assert first["search_summary"] == {}
    assert first["proposal"] == {}
    assert first["approval"] == {}
    assert first["audit_events"][0]["event_type"] == "run_created"
    assert "user_id" not in first
    assert "idempotency_key" not in first
    assert "resume_text" not in str(first)
    assert "job_description" not in str(first)

    list_response = client.get("/career-plans", headers=AUTH_HEADERS)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["id"] == first["id"]
    assert "audit_events" not in list_response.json()[0]


def test_create_rejects_raw_documents_and_out_of_bounds_goal() -> None:
    raw_document_payload = {
        **_career_plan_payload(),
        "resume_text": "Raw resume content must not be accepted here.",
        "job_description": "Raw posting content must not be accepted here.",
    }
    assert client.post("/career-plans", json=raw_document_payload, headers=AUTH_HEADERS).status_code == 422

    invalid_bound_payload = _career_plan_payload("invalid-bound")
    invalid_bound_payload["goal"]["max_jobs_to_analyze"] = 6
    assert client.post("/career-plans", json=invalid_bound_payload, headers=AUTH_HEADERS).status_code == 422


def test_career_plans_are_isolated_for_every_owned_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    first_user_plan = _create_plan()
    plan_id = first_user_plan["id"]

    monkeypatch.setenv("AUTH_DEV_USER_ID", "test-clerk-user-2")

    assert client.get(f"/career-plans/{plan_id}", headers=AUTH_HEADERS).status_code == 404
    assert client.post(f"/career-plans/{plan_id}/cancel", headers=AUTH_HEADERS).status_code == 404
    assert (
        client.post(
            f"/career-plans/{plan_id}/decision",
            json={"decision": "rejected", "edited_actions": []},
            headers=AUTH_HEADERS,
        ).status_code
        == 404
    )
    assert client.delete(f"/career-plans/{plan_id}", headers=AUTH_HEADERS).status_code == 404


def test_running_plan_cancellation_is_bounded_and_idempotent() -> None:
    plan = _create_plan()
    plan_id = plan["id"]

    with TestingSessionLocal() as db:
        run = db.get(CareerPlanRunDB, plan_id)
        assert run is not None
        run.status = "running"
        db.commit()

    first_response = client.post(f"/career-plans/{plan_id}/cancel", headers=AUTH_HEADERS)
    second_response = client.post(f"/career-plans/{plan_id}/cancel", headers=AUTH_HEADERS)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["status"] == "running"
    assert first_response.json()["cancel_requested_at"] is not None
    assert first_response.json()["run_version"] == 2
    assert second_response.json()["run_version"] == 2
    assert [event["event_type"] for event in second_response.json()["audit_events"]] == [
        "run_created",
        "cancellation_requested",
    ]


def test_non_running_plan_cannot_request_cancellation() -> None:
    plan = _create_plan()
    response = client.post(f"/career-plans/{plan['id']}/cancel", headers=AUTH_HEADERS)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "run_not_active"


def test_user_decision_is_stored_separately_from_generated_proposal() -> None:
    plan = _create_plan()
    plan_id = plan["id"]

    with TestingSessionLocal() as db:
        run = db.get(CareerPlanRunDB, plan_id)
        assert run is not None
        run.status = "awaiting_approval"
        run.proposal = {"actions": [{"id": "action-1", "status": "proposed"}]}
        db.commit()

    decision_response = client.post(
        f"/career-plans/{plan_id}/decision",
        json={
            "decision": "approved",
            "edited_actions": [
                {
                    "id": "action-1",
                    "action_type": "build_proof",
                    "priority": "high",
                    "title": "Build Docker deployment proof",
                    "rationale": "Docker is a repeated gap across selected opportunities.",
                    "job_refs": ["job-1", "job-2"],
                    "evidence_refs": ["gap-docker"],
                    "status": "edited",
                }
            ],
        },
        headers=AUTH_HEADERS,
    )

    assert decision_response.status_code == 200, decision_response.text
    body = decision_response.json()
    assert body["status"] == "approved"
    assert body["proposal"]["actions"][0]["status"] == "proposed"
    assert body["approval"]["decision"] == "approved"
    assert body["approval"]["edited_actions"][0]["status"] == "edited"
    assert body["completed_at"] is not None


def test_rejected_plan_cannot_smuggle_edited_actions() -> None:
    response = client.post(
        "/career-plans/999/decision",
        json={
            "decision": "rejected",
            "edited_actions": [
                {
                    "id": "action-1",
                    "action_type": "build_proof",
                    "priority": "high",
                    "title": "Unexpected edit",
                    "rationale": "Rejected plans should not accept edits.",
                    "status": "edited",
                }
            ],
        },
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 422


def test_deleting_owned_plan_cascades_steps_and_audit_events() -> None:
    plan = _create_plan()
    plan_id = plan["id"]

    with TestingSessionLocal() as db:
        step = CareerPlanStepDB(
            run_id=plan_id,
            step_name="validate_input",
            status="completed",
            attempt=1,
            safe_output_summary_json='{"validated": true}',
        )
        db.add(step)
        db.commit()

    delete_response = client.delete(f"/career-plans/{plan_id}", headers=AUTH_HEADERS)
    assert delete_response.status_code == 200
    assert delete_response.json() == {"status": "deleted"}

    with TestingSessionLocal() as db:
        assert db.query(CareerPlanRunDB).count() == 0
        assert db.query(CareerPlanStepDB).count() == 0
        assert db.query(CareerPlanAuditEventDB).count() == 0


def test_audit_payload_guard_rejects_raw_or_secret_shaped_fields() -> None:
    _validate_safe_audit_payload({"status": "running", "job_count": 5, "reason_codes": ["ok"]})

    with pytest.raises(Exception) as raw_error:
        _validate_safe_audit_payload({"resume_text": "must not persist"})
    assert getattr(raw_error.value, "status_code", None) == 409

    with pytest.raises(Exception) as secret_error:
        _validate_safe_audit_payload({"api_key": "must not persist"})
    assert getattr(secret_error.value, "status_code", None) == 409
