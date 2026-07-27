from __future__ import annotations

import json

from app.analysis import analyze_smart_fit
from app.analysis import personalized_coaching


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


def _payload() -> dict:
    return {
        "schema_version": "8d.1",
        "strategy_summary": (
            "Lead with the demonstrated Python project, strengthen the existing SQL proof, "
            "and keep Docker framed as a lower-priority preference."
        ),
        "action_items": [
            {
                "action_type": "interview_prep",
                "priority": "high",
                "basis": "strength_positioning",
                "title": "",
                "reference": "Python",
                "category": None,
                "resume_evidence": [],
                "job_evidence": None,
                "advice": (
                    "Prepare a concise explanation of the backend project using only the "
                    "documented Python and FastAPI evidence."
                ),
            },
            {
                "action_type": "resume_rewrite",
                "priority": "high",
                "basis": "wording_proof_gap",
                "title": "A",
                "reference": "SQL",
                "category": None,
                "resume_evidence": [],
                "job_evidence": None,
                "advice": (
                    "Rewrite an existing truthful project bullet to explain how SQL was used "
                    "without inventing an outcome or responsibility."
                ),
            },
            {
                "action_type": "lower_priority",
                "priority": "low",
                "basis": "lower_priority_preference",
                "title": "AI",
                "reference": "Docker",
                "category": None,
                "resume_evidence": [],
                "job_evidence": None,
                "advice": (
                    "Keep Docker behind the required Python and SQL proof and do not imply "
                    "current Docker experience."
                ),
            },
        ],
        "application_guidance": (
            "The role is reasonable to pursue while improving the existing SQL proof and "
            "keeping Docker clearly labeled as a preference."
        ),
        "uncertainty_note": None,
    }


def _assessment_by_skill(analysis, skill: str):
    return next(
        assessment
        for assessment in analysis.requirement_assessments
        if assessment.skill.casefold() == skill.casefold()
    )


def test_short_provider_titles_are_hydrated_after_grounded_validation() -> None:
    analysis = analyze_smart_fit(
        resume_text=RESUME_TEXT,
        job_description=JOB_TEXT,
        use_model_assisted=False,
    )
    immutable_snapshot = {
        "fit_summary": analysis.fit_summary.model_dump(),
        "requirements": [item.model_dump() for item in analysis.requirement_assessments],
        "hard_requirements": [item.model_dump() for item in analysis.hard_requirements],
        "provenance_version": analysis.provenance_version,
        "grounding_warnings": list(analysis.grounding_warnings),
    }

    plan = personalized_coaching.PersonalizedCoachingPlan.model_validate_json(
        json.dumps(_payload())
    )

    assert [item.title for item in plan.action_items] == [
        "Pending action",
        "Pending action",
        "Pending action",
    ]

    personalized_coaching.validate_personalized_coaching(plan, analysis)

    python = _assessment_by_skill(analysis, "Python")
    sql = _assessment_by_skill(analysis, "SQL")
    docker = _assessment_by_skill(analysis, "Docker")

    assert [item.title for item in plan.action_items] == [
        "Prepare the Python interview story",
        "Strengthen SQL resume proof",
        "Keep Docker as a lower priority",
    ]
    assert plan.action_items[0].resume_evidence == python.resume_evidence
    assert plan.action_items[0].job_evidence == python.job_evidence
    assert plan.action_items[1].resume_evidence == sql.resume_evidence
    assert plan.action_items[1].job_evidence == sql.job_evidence
    assert plan.action_items[2].resume_evidence == docker.resume_evidence
    assert plan.action_items[2].job_evidence == docker.job_evidence

    assert analysis.fit_summary.model_dump() == immutable_snapshot["fit_summary"]
    assert [item.model_dump() for item in analysis.requirement_assessments] == immutable_snapshot["requirements"]
    assert [item.model_dump() for item in analysis.hard_requirements] == immutable_snapshot["hard_requirements"]
    assert analysis.provenance_version == immutable_snapshot["provenance_version"]
    assert analysis.grounding_warnings == immutable_snapshot["grounding_warnings"]


def test_valid_provider_title_is_still_replaced_with_backend_title() -> None:
    analysis = analyze_smart_fit(
        resume_text=RESUME_TEXT,
        job_description=JOB_TEXT,
        use_model_assisted=False,
    )
    payload = _payload()
    payload["action_items"] = [payload["action_items"][0]]
    payload["action_items"][0]["title"] = "Provider-written display title"

    plan = personalized_coaching.PersonalizedCoachingPlan.model_validate_json(
        json.dumps(payload)
    )
    personalized_coaching.validate_personalized_coaching(plan, analysis)

    assert plan.action_items[0].title == "Prepare the Python interview story"


def test_provider_action_type_mismatch_is_hydrated_from_validated_basis() -> None:
    analysis = analyze_smart_fit(
        resume_text=RESUME_TEXT,
        job_description=JOB_TEXT,
        use_model_assisted=False,
    )
    payload = _payload()
    for action in payload["action_items"]:
        action["action_type"] = "resume_rewrite"

    plan = personalized_coaching.PersonalizedCoachingPlan.model_validate_json(
        json.dumps(payload)
    )
    assert [item.action_type.value for item in plan.action_items] == [
        "resume_rewrite",
        "resume_rewrite",
        "resume_rewrite",
    ]

    personalized_coaching.validate_personalized_coaching(plan, analysis)

    assert [item.action_type.value for item in plan.action_items] == [
        "interview_prep",
        "resume_rewrite",
        "lower_priority",
    ]
    assert [item.title for item in plan.action_items] == [
        "Prepare the Python interview story",
        "Strengthen SQL resume proof",
        "Keep Docker as a lower priority",
    ]
