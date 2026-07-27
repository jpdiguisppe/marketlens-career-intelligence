from __future__ import annotations

import json

import pytest

from app.analysis import analyze_smart_fit
from app.analysis import personalized_coaching
from app.analysis.personalized_coaching import (
    PersonalizedCoachingError,
    PersonalizedCoachingPlan,
    apply_personalized_coaching,
    validate_personalized_coaching,
)

RESUME_TEXT = """PROJECTS
Built a Python FastAPI service backed by PostgreSQL.
SKILLS
Python, SQL, FastAPI, PostgreSQL
"""

JOB_TEXT = """Backend Engineer
REQUIRED QUALIFICATIONS
Python and SQL are required.
PREFERRED QUALIFICATIONS
Docker is preferred.
RESPONSIBILITIES
Build reliable backend APIs.
"""


def _analysis():
    return analyze_smart_fit(
        resume_text=RESUME_TEXT,
        job_description=JOB_TEXT,
        use_model_assisted=False,
    )


def _reference_only_plan() -> dict:
    return {
        "schema_version": "8d.1",
        "strategy_summary": (
            "Lead with the demonstrated Python backend project, strengthen the existing SQL proof, "
            "and keep Docker framed as a lower-priority preference rather than current experience."
        ),
        "action_items": [
            {
                "action_type": "interview_prep",
                "priority": "high",
                "basis": "strength_positioning",
                "title": "Prepare the Python project story",
                "reference": "Python",
                "category": None,
                "resume_evidence": [],
                "job_evidence": None,
                "advice": (
                    "Prepare a concise explanation of the backend problem, the FastAPI design choice, "
                    "and how PostgreSQL supported the service without adding undocumented outcomes."
                ),
            },
            {
                "action_type": "resume_rewrite",
                "priority": "medium",
                "basis": "strength_positioning",
                "title": "Make the Python application explicit",
                "reference": "Python",
                "category": None,
                "resume_evidence": [],
                "job_evidence": None,
                "advice": (
                    "Keep the existing project truthful while making the Python implementation and backend "
                    "service responsibility easier to recognize in one concise bullet."
                ),
            },
            {
                "action_type": "resume_rewrite",
                "priority": "high",
                "basis": "wording_proof_gap",
                "title": "Turn the SQL mention into applied proof",
                "reference": "SQL",
                "category": None,
                "resume_evidence": [],
                "job_evidence": None,
                "advice": (
                    "Rewrite an existing accurate project bullet to state what SQL was used to query, store, "
                    "or change rather than leaving it only in the skills list."
                ),
            },
            {
                "action_type": "lower_priority",
                "priority": "low",
                "basis": "lower_priority_preference",
                "title": "Keep Docker behind required proof",
                "reference": "Docker",
                "category": None,
                "resume_evidence": [],
                "job_evidence": None,
                "advice": (
                    "Treat Docker as an optional project enhancement after the required Python and SQL evidence "
                    "is clear, and do not imply current Docker experience."
                ),
            },
        ],
        "application_guidance": (
            "The role is reasonable to pursue while strengthening the existing SQL explanation and keeping "
            "the preferred Docker requirement clearly separated from demonstrated experience."
        ),
        "uncertainty_note": None,
    }


class _FakeResponse:
    status_code = 200
    headers = {"x-request-id": "req_live_regression"}

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"output_text": json.dumps(_reference_only_plan())}


class _FakeClient:
    captured: dict = {}

    def __init__(self, *, timeout: float):
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def post(self, url: str, *, headers: dict, json: dict):
        self.__class__.captured = {
            "url": url,
            "headers": headers,
            "payload": json,
            "timeout": self.timeout,
        }
        return _FakeResponse()


def _configure_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "backend-secret")
    monkeypatch.setenv("OPENAI_MODEL", "fixture-model")
    monkeypatch.setenv("OPENAI_TIMEOUT_SECONDS", "4.5")


def test_reference_only_plan_is_hydrated_with_canonical_evidence() -> None:
    analysis = _analysis()
    plan = PersonalizedCoachingPlan.model_validate(_reference_only_plan())

    validate_personalized_coaching(plan, analysis)

    python_actions = [item for item in plan.action_items if item.reference == "Python"]
    assert len(python_actions) == 2
    assert all(
        item.resume_evidence == ["Built a Python FastAPI service backed by PostgreSQL."]
        for item in python_actions
    )
    assert all(item.job_evidence == "Python and SQL are required." for item in python_actions)

    sql_action = next(item for item in plan.action_items if item.reference == "SQL")
    assert sql_action.resume_evidence == ["Python, SQL, FastAPI, PostgreSQL"]
    assert sql_action.job_evidence == "Python and SQL are required."

    docker_action = next(item for item in plan.action_items if item.reference == "Docker")
    assert docker_action.resume_evidence == []
    assert docker_action.job_evidence == "Docker is preferred."


def test_distinct_actions_may_reuse_a_reference_but_true_duplicates_fail() -> None:
    analysis = _analysis()
    payload = _reference_only_plan()
    duplicate = dict(payload["action_items"][0])
    duplicate["title"] = "Repeat the same Python interview action"
    payload["action_items"] = [payload["action_items"][0], duplicate]
    plan = PersonalizedCoachingPlan.model_validate(payload)

    with pytest.raises(PersonalizedCoachingError, match="repeated the same action"):
        validate_personalized_coaching(plan, analysis)


def test_noncanonical_provider_evidence_is_still_rejected() -> None:
    analysis = _analysis()
    payload = _reference_only_plan()
    payload["action_items"][0]["resume_evidence"] = ["Built a Kubernetes platform."]
    plan = PersonalizedCoachingPlan.model_validate(payload)

    with pytest.raises(PersonalizedCoachingError, match="invented resume evidence"):
        validate_personalized_coaching(plan, analysis)


def test_provider_context_exposes_only_valid_reference_sources() -> None:
    context = personalized_coaching._analysis_context(_analysis())

    assert "deterministic_actions" not in context
    assert set(context["allowed_references"]) == {"Python", "SQL", "Docker"}
    assert "Turn background into resume proof" not in json.dumps(context)


def test_live_shaped_provider_response_succeeds_and_preserves_scored_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_provider(monkeypatch)
    monkeypatch.setattr(personalized_coaching.httpx, "Client", _FakeClient)
    analysis = _analysis()
    snapshot = {
        "fit_summary": analysis.fit_summary.model_dump(),
        "requirements": [item.model_dump() for item in analysis.requirement_assessments],
        "hard_requirements": [item.model_dump() for item in analysis.hard_requirements],
        "provenance_version": analysis.provenance_version,
        "grounding_warnings": list(analysis.grounding_warnings),
    }

    result = apply_personalized_coaching(analysis, use_model_assisted=True)

    assert result.coaching_engine == "model_assisted"
    assert result.coaching_status == "used"
    assert result.coaching_version == "8d.1"
    assert result.report_summary[0].startswith("Personalized AI coaching:")
    assert result.fit_summary.model_dump() == snapshot["fit_summary"]
    assert [item.model_dump() for item in result.requirement_assessments] == snapshot["requirements"]
    assert [item.model_dump() for item in result.hard_requirements] == snapshot["hard_requirements"]
    assert result.provenance_version == snapshot["provenance_version"]
    assert result.grounding_warnings == snapshot["grounding_warnings"]

    user_prompt = _FakeClient.captured["payload"]["input"][1]["content"]
    assert "allowed_references" in user_prompt
    assert "deterministic_actions" not in user_prompt
    assert _FakeClient.captured["payload"]["store"] is False
