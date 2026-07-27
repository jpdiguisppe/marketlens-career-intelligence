from __future__ import annotations

import json

import pytest

from app.analysis import analyze_smart_fit
from app.analysis import personalized_coaching
from app.analysis.personalized_coaching import (
    CoachingBasis,
    PersonalizedCoachingAction,
    PersonalizedCoachingError,
    PersonalizedCoachingPlan,
    apply_personalized_coaching,
    validate_personalized_coaching,
)
from app.analysis.schemas import CoachingActionType

RESUME_TEXT = """PROJECTS
Built a Python FastAPI service backed by PostgreSQL.
SKILLS
Python, SQL, FastAPI, PostgreSQL
UNRELATED PRIVATE NOTE
This sentence must never be sent to the coaching provider.
"""

JOB_TEXT = """Backend Engineer
REQUIRED QUALIFICATIONS
Python and SQL are required.
PREFERRED QUALIFICATIONS
Docker is preferred.
RESPONSIBILITIES
Build reliable backend APIs.
UNRELATED COMPANY NOTE
This sentence must never be sent to the coaching provider.
"""


def _analysis():
    return analyze_smart_fit(
        resume_text=RESUME_TEXT,
        job_description=JOB_TEXT,
        use_model_assisted=False,
    )


def _plan_dict() -> dict:
    return {
        "schema_version": "8d.1",
        "strategy_summary": (
            "Lead with the demonstrated Python backend project, strengthen the existing SQL proof, "
            "and treat Docker as a lower-priority learning target rather than overstating experience."
        ),
        "action_items": [
            {
                "action_type": "interview_prep",
                "priority": "high",
                "basis": "strength_positioning",
                "title": "Prepare the Python backend project story",
                "reference": "Python",
                "category": "programming_language",
                "resume_evidence": [
                    "Built a Python FastAPI service backed by PostgreSQL."
                ],
                "job_evidence": "Python and SQL are required.",
                "advice": (
                    "Prepare a concise explanation of the backend problem, why FastAPI was selected, "
                    "and how the service used PostgreSQL, while staying within the documented project evidence."
                ),
            },
            {
                "action_type": "resume_rewrite",
                "priority": "high",
                "basis": "wording_proof_gap",
                "title": "Turn the SQL mention into applied proof",
                "reference": "SQL",
                "category": "database",
                "resume_evidence": ["Python, SQL, FastAPI, PostgreSQL"],
                "job_evidence": "Python and SQL are required.",
                "advice": (
                    "Rewrite an existing truthful project bullet to describe what SQL was used to query, "
                    "store, or change; do not add an outcome or responsibility that is not already accurate."
                ),
            },
            {
                "action_type": "lower_priority",
                "priority": "low",
                "basis": "lower_priority_preference",
                "title": "Keep Docker behind required proof",
                "reference": "Docker",
                "category": "devops",
                "resume_evidence": [],
                "job_evidence": "Docker is preferred.",
                "advice": (
                    "Treat Docker as an optional next project enhancement after the required Python and SQL "
                    "evidence is clear; do not imply current Docker experience."
                ),
            },
        ],
        "application_guidance": (
            "The role is reasonable to pursue if the candidate can clarify the existing SQL work, while "
            "keeping Docker framed as a preference and not a demonstrated strength."
        ),
        "uncertainty_note": None,
    }


class _FakeResponse:
    status_code = 200
    headers = {"x-request-id": "req_test"}

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"output_text": json.dumps(_plan_dict())}


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


def test_personalized_coaching_uses_strict_schema_and_compact_grounded_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_provider(monkeypatch)
    monkeypatch.setattr(personalized_coaching.httpx, "Client", _FakeClient)
    analysis = _analysis()

    result = apply_personalized_coaching(analysis, use_model_assisted=True)
    payload = _FakeClient.captured["payload"]
    user_prompt = payload["input"][1]["content"]

    assert result.coaching_engine == "model_assisted"
    assert result.coaching_status == "used"
    assert result.coaching_version == "8d.1"
    assert result.report_summary[0].startswith("Personalized AI coaching:")
    assert result.coaching_actions[0].skill == "Python"
    assert payload["store"] is False
    assert payload["text"]["format"]["strict"] is True
    assert _FakeClient.captured["url"].endswith("/responses")
    assert _FakeClient.captured["headers"]["Authorization"] == "Bearer backend-secret"
    assert _FakeClient.captured["timeout"] == 4.5
    assert "This sentence must never be sent to the coaching provider." not in user_prompt
    assert "Python and SQL are required." in user_prompt


def test_personalized_coaching_cannot_change_scored_analysis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_provider(monkeypatch)
    monkeypatch.setattr(personalized_coaching.httpx, "Client", _FakeClient)
    analysis = _analysis()
    immutable_snapshot = {
        "fit_summary": analysis.fit_summary.model_dump(),
        "requirements": [item.model_dump() for item in analysis.requirement_assessments],
        "hard_requirements": [item.model_dump() for item in analysis.hard_requirements],
        "provenance_version": analysis.provenance_version,
        "grounding_warnings": analysis.grounding_warnings,
    }

    result = apply_personalized_coaching(analysis, use_model_assisted=True)

    assert result.fit_summary.model_dump() == immutable_snapshot["fit_summary"]
    assert [item.model_dump() for item in result.requirement_assessments] == immutable_snapshot["requirements"]
    assert [item.model_dump() for item in result.hard_requirements] == immutable_snapshot["hard_requirements"]
    assert result.provenance_version == immutable_snapshot["provenance_version"]
    assert result.grounding_warnings == immutable_snapshot["grounding_warnings"]


def test_unknown_requirement_reference_is_rejected() -> None:
    analysis = _analysis()
    payload = _plan_dict()
    payload["action_items"][0]["reference"] = "Kubernetes"
    payload["action_items"][0]["job_evidence"] = "Kubernetes is required."
    plan = PersonalizedCoachingPlan.model_validate(payload)

    with pytest.raises(PersonalizedCoachingError, match="unknown requirement"):
        validate_personalized_coaching(plan, analysis)


def test_missing_requirement_cannot_be_presented_as_existing_resume_proof() -> None:
    analysis = _analysis()
    payload = _plan_dict()
    docker = payload["action_items"][2]
    docker["resume_evidence"] = [
        "Built a Python FastAPI service backed by PostgreSQL."
    ]
    plan = PersonalizedCoachingPlan.model_validate(payload)

    with pytest.raises(PersonalizedCoachingError, match="invented resume evidence"):
        validate_personalized_coaching(plan, analysis)


def test_wrong_gap_kind_is_rejected() -> None:
    analysis = _analysis()
    payload = _plan_dict()
    payload["action_items"][1]["basis"] = "experience_learning_gap"
    payload["action_items"][1]["action_type"] = "learning_focus"
    plan = PersonalizedCoachingPlan.model_validate(payload)

    with pytest.raises(PersonalizedCoachingError, match="high-priority missing"):
        validate_personalized_coaching(plan, analysis)


def test_changed_job_quote_is_rejected() -> None:
    analysis = _analysis()
    payload = _plan_dict()
    payload["action_items"][0]["job_evidence"] = "Ten years of Python are required."
    plan = PersonalizedCoachingPlan.model_validate(payload)

    with pytest.raises(PersonalizedCoachingError, match="changed the grounded job quote"):
        validate_personalized_coaching(plan, analysis)


def test_unsupported_hiring_prediction_is_rejected() -> None:
    analysis = _analysis()
    payload = _plan_dict()
    payload["application_guidance"] = (
        "This rewrite gives a 90% chance of an interview and should therefore be completed immediately."
    )
    plan = PersonalizedCoachingPlan.model_validate(payload)

    with pytest.raises(PersonalizedCoachingError, match="unsupported hiring prediction"):
        validate_personalized_coaching(plan, analysis)


def test_disabled_provider_keeps_complete_deterministic_coaching(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_ANALYSIS_ENABLED", "false")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    analysis = _analysis()

    result = apply_personalized_coaching(analysis, use_model_assisted=True)

    assert result.coaching_engine == "deterministic"
    assert result.coaching_status.startswith("fallback_unavailable")
    assert result.coaching_actions == analysis.coaching_actions
    assert result.report_summary == analysis.report_summary
    assert result.fit_summary == analysis.fit_summary


def test_provider_schema_requires_all_object_fields_recursively() -> None:
    schema = personalized_coaching._coaching_schema()

    def assert_strict_objects(value):
        if isinstance(value, list):
            for item in value:
                assert_strict_objects(item)
            return
        if not isinstance(value, dict):
            return
        if value.get("type") == "object":
            assert value.get("additionalProperties") is False
            assert set(value.get("required", [])) == set(value.get("properties", {}))
        for item in value.values():
            assert_strict_objects(item)

    assert_strict_objects(schema)


def test_contract_rejects_extra_fields() -> None:
    payload = _plan_dict()
    payload["unexpected"] = True

    with pytest.raises(ValidationError):
        PersonalizedCoachingPlan.model_validate(payload)


def test_action_contract_examples_are_valid() -> None:
    action = PersonalizedCoachingAction.model_validate(_plan_dict()["action_items"][0])

    assert action.basis == CoachingBasis.STRENGTH_POSITIONING
    assert action.action_type == CoachingActionType.INTERVIEW_PREP
