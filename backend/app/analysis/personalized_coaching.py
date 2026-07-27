"""Evidence-bound personalized coaching for Milestone 8D.

The provider may improve the clarity and prioritization of coaching, but it may
not change Smart Fit scores, requirement assessments, hard constraints, or
provenance. Provider input is a compact structured summary of the completed
analysis rather than the raw resume or full job description.
"""

from __future__ import annotations

import json
import logging
import re
from enum import Enum
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.analysis.model_extractor import (
    ModelAssistedExtractionError,
    ModelAssistedUnavailable,
    _extract_output_text,
    _provider_compatible_schema,
    _require_provider_config,
)
from app.analysis.schemas import (
    COACHING_SCHEMA_VERSION,
    CoachingAction,
    CoachingActionType,
    EvidenceStatus,
    HardRequirementAssessment,
    RequirementAssessment,
    SmartFitAnalysisResponse,
)

COACHING_PROMPT_VERSION = "8d.1"
MAX_PERSONALIZED_ACTIONS = 5

_logger = logging.getLogger(__name__)
_WHITESPACE = re.compile(r"\s+")


class CoachingBasis(str, Enum):
    STRENGTH_POSITIONING = "strength_positioning"
    WORDING_PROOF_GAP = "wording_proof_gap"
    EXPERIENCE_LEARNING_GAP = "experience_learning_gap"
    HARD_CONSTRAINT_CHECK = "hard_constraint_check"
    LOWER_PRIORITY_PREFERENCE = "lower_priority_preference"


class PersonalizedCoachingAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: CoachingActionType
    priority: Literal["high", "medium", "low"]
    basis: CoachingBasis
    title: str = Field(min_length=3, max_length=120)
    reference: str = Field(min_length=1, max_length=140)
    category: str | None = Field(default=None, max_length=80)
    resume_evidence: list[str] = Field(default_factory=list, max_length=3)
    job_evidence: str | None = Field(default=None, max_length=500)
    advice: str = Field(min_length=20, max_length=700)


class PersonalizedCoachingPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[COACHING_SCHEMA_VERSION]
    strategy_summary: str = Field(min_length=30, max_length=500)
    action_items: list[PersonalizedCoachingAction] = Field(
        min_length=1,
        max_length=MAX_PERSONALIZED_ACTIONS,
    )
    application_guidance: str = Field(min_length=20, max_length=500)
    uncertainty_note: str | None = Field(default=None, max_length=300)


class PersonalizedCoachingError(RuntimeError):
    """Raised when provider coaching is unavailable, invalid, or ungrounded."""

    def __init__(self, message: str, *, code: str = "coaching_provider_error"):
        super().__init__(message)
        self.code = code


def _key(value: str) -> str:
    return _WHITESPACE.sub(" ", value.strip()).casefold()


def _coaching_schema() -> dict[str, Any]:
    return _provider_compatible_schema(PersonalizedCoachingPlan.model_json_schema())


def _analysis_context(analysis: SmartFitAnalysisResponse) -> dict[str, Any]:
    """Return the only facts the coach is allowed to use.

    Raw resume and full job text are intentionally excluded. Every quote below
    already passed the Milestone 8C request-time grounding checks.
    """

    return {
        "fit_summary": {
            "score": analysis.fit_summary.score,
            "band": analysis.fit_summary.band.value,
            "headline": analysis.fit_summary.headline,
        },
        "requirements": [
            {
                "reference": assessment.skill,
                "requirement_type": assessment.requirement_type.value,
                "weight": assessment.weight,
                "status": assessment.status.value,
                "resume_evidence": assessment.resume_evidence,
                "job_evidence": assessment.job_evidence,
                "grounded": assessment.grounded,
            }
            for assessment in analysis.requirement_assessments
            if assessment.grounded
            and assessment.job_provenance
            and assessment.job_provenance.grounded
        ],
        "hard_requirements": [
            {
                "reference": f"hard:{requirement.category}",
                "category": requirement.category,
                "status": requirement.status.value,
                "requirement": requirement.requirement,
                "resume_evidence": requirement.resume_evidence,
                "job_evidence": requirement.source_text,
                "grounded": requirement.grounded,
            }
            for requirement in analysis.hard_requirements
            if requirement.grounded
        ],
        "deterministic_actions": [
            {
                "action_type": action.action_type.value,
                "priority": action.priority,
                "title": action.title,
                "skill": action.skill,
                "category": action.category,
                "source_evidence": action.source_evidence,
                "job_evidence": action.job_evidence,
                "advice": action.advice,
            }
            for action in analysis.coaching_actions
        ],
    }


_SYSTEM_PROMPT = f"""You write personalized career coaching for MarketLens Smart Fit.

Contract version: {COACHING_SCHEMA_VERSION}
Prompt version: {COACHING_PROMPT_VERSION}

You receive only a completed, evidence-grounded Smart Fit summary. You do not
receive the raw resume or full job description.

Rules:
- Return schema_version exactly as {COACHING_SCHEMA_VERSION!r}.
- Never change, reinterpret, or dispute the supplied score, band, status, weight, hard constraint, or evidence.
- Every action must use one exact supplied reference.
- Copy job_evidence exactly from that reference.
- Copy resume_evidence only from the exact supplied resume_evidence list.
- Never invent experience, projects, coursework, credentials, outcomes, metrics, or evidence.
- A demonstrated or explicit requirement may support strength_positioning.
- A mentioned, implied, or related requirement may support wording_proof_gap.
- A missing high-priority requirement may support experience_learning_gap.
- A lower-weight missing preference may support lower_priority_preference.
- A hard:* reference may support only hard_constraint_check.
- Distinguish resume wording fixes from real learning or experience gaps.
- Suggestions may describe what the candidate could build, learn, verify, or rewrite, but must not claim they already did it.
- Do not predict hiring probability, ATS success, interview selection, or an offer.
- Keep advice concrete, truthful, concise, and immediately actionable.
- Return every schema field. Use null for nullable fields and [] for empty lists.
- Return only schema-valid JSON with no extra fields.
"""


def _build_user_prompt(analysis: SmartFitAnalysisResponse) -> str:
    return (
        "Create an evidence-bound coaching plan from this completed Smart Fit analysis.\n\n"
        + json.dumps(_analysis_context(analysis), ensure_ascii=False, separators=(",", ":"))
    )


def _assessment_map(
    analysis: SmartFitAnalysisResponse,
) -> dict[str, RequirementAssessment]:
    return {_key(item.skill): item for item in analysis.requirement_assessments}


def _hard_requirement_map(
    analysis: SmartFitAnalysisResponse,
) -> dict[str, HardRequirementAssessment]:
    return {
        _key(f"hard:{item.category}"): item
        for item in analysis.hard_requirements
    }


def _validate_summary_language(plan: PersonalizedCoachingPlan) -> None:
    combined = f"{plan.strategy_summary} {plan.application_guidance}".casefold()
    banned = (
        "guaranteed offer",
        "guaranteed interview",
        "will get hired",
        "will be hired",
        "ats score",
        "hiring probability",
    )
    if any(phrase in combined for phrase in banned) or "% chance" in combined:
        raise PersonalizedCoachingError(
            "Provider coaching included an unsupported hiring prediction.",
            code="coaching_unsupported_prediction",
        )


def validate_personalized_coaching(
    plan: PersonalizedCoachingPlan,
    analysis: SmartFitAnalysisResponse,
) -> None:
    """Reject advice that is not traceable to the completed grounded analysis."""

    _validate_summary_language(plan)
    assessments = _assessment_map(analysis)
    hard_requirements = _hard_requirement_map(analysis)
    seen_references: set[str] = set()

    for action in plan.action_items:
        reference_key = _key(action.reference)
        if reference_key in seen_references:
            raise PersonalizedCoachingError(
                f"Provider coaching repeated reference {action.reference!r}.",
                code="coaching_duplicate_reference",
            )
        seen_references.add(reference_key)

        if reference_key in hard_requirements:
            requirement = hard_requirements[reference_key]
            if not requirement.grounded:
                raise PersonalizedCoachingError(
                    "Provider coaching referenced an ungrounded hard requirement.",
                    code="coaching_ungrounded_reference",
                )
            if action.basis != CoachingBasis.HARD_CONSTRAINT_CHECK:
                raise PersonalizedCoachingError(
                    "Hard requirements may only produce verification coaching.",
                    code="coaching_basis_mismatch",
                )
            if action.action_type != CoachingActionType.HARD_REQUIREMENT_CHECK:
                raise PersonalizedCoachingError(
                    "Hard requirement coaching used the wrong action type.",
                    code="coaching_action_type_mismatch",
                )
            if action.job_evidence != requirement.source_text:
                raise PersonalizedCoachingError(
                    "Hard requirement coaching changed the grounded job quote.",
                    code="coaching_job_evidence_mismatch",
                )
            allowed_resume = [requirement.resume_evidence] if requirement.resume_evidence else []
            if any(item not in allowed_resume for item in action.resume_evidence):
                raise PersonalizedCoachingError(
                    "Hard requirement coaching invented resume evidence.",
                    code="coaching_resume_evidence_mismatch",
                )
            continue

        assessment = assessments.get(reference_key)
        if assessment is None:
            raise PersonalizedCoachingError(
                f"Provider coaching referenced unknown requirement {action.reference!r}.",
                code="coaching_unknown_reference",
            )
        if not assessment.grounded or not assessment.job_provenance or not assessment.job_provenance.grounded:
            raise PersonalizedCoachingError(
                "Provider coaching referenced an ungrounded assessment.",
                code="coaching_ungrounded_reference",
            )
        if action.job_evidence != assessment.job_evidence:
            raise PersonalizedCoachingError(
                "Provider coaching changed the grounded job quote.",
                code="coaching_job_evidence_mismatch",
            )
        if any(item not in assessment.resume_evidence for item in action.resume_evidence):
            raise PersonalizedCoachingError(
                "Provider coaching invented resume evidence.",
                code="coaching_resume_evidence_mismatch",
            )

        if assessment.status == EvidenceStatus.MISSING and action.resume_evidence:
            raise PersonalizedCoachingError(
                "Missing requirements cannot carry resume evidence.",
                code="coaching_missing_claimed_as_proven",
            )

        if action.basis == CoachingBasis.STRENGTH_POSITIONING:
            if assessment.status not in {EvidenceStatus.DEMONSTRATED, EvidenceStatus.EXPLICIT}:
                raise PersonalizedCoachingError(
                    "Strength coaching was not backed by strong resume evidence.",
                    code="coaching_basis_mismatch",
                )
            if action.action_type not in {
                CoachingActionType.INTERVIEW_PREP,
                CoachingActionType.RESUME_REWRITE,
            }:
                raise PersonalizedCoachingError(
                    "Strength coaching used an incompatible action type.",
                    code="coaching_action_type_mismatch",
                )
            if not action.resume_evidence:
                raise PersonalizedCoachingError(
                    "Strength coaching omitted its resume evidence.",
                    code="coaching_resume_evidence_missing",
                )
        elif action.basis == CoachingBasis.WORDING_PROOF_GAP:
            if assessment.status not in {
                EvidenceStatus.MENTIONED,
                EvidenceStatus.IMPLIED,
                EvidenceStatus.RELATED,
            }:
                raise PersonalizedCoachingError(
                    "Wording-gap coaching did not match the assessment status.",
                    code="coaching_basis_mismatch",
                )
            if action.action_type not in {
                CoachingActionType.RESUME_REWRITE,
                CoachingActionType.INTERVIEW_PREP,
            }:
                raise PersonalizedCoachingError(
                    "Wording-gap coaching used an incompatible action type.",
                    code="coaching_action_type_mismatch",
                )
            if not action.resume_evidence:
                raise PersonalizedCoachingError(
                    "Wording-gap coaching omitted its existing evidence.",
                    code="coaching_resume_evidence_missing",
                )
        elif action.basis == CoachingBasis.EXPERIENCE_LEARNING_GAP:
            if assessment.status != EvidenceStatus.MISSING or assessment.weight < 0.75:
                raise PersonalizedCoachingError(
                    "Learning-gap coaching did not match a high-priority missing requirement.",
                    code="coaching_basis_mismatch",
                )
            if action.action_type != CoachingActionType.LEARNING_FOCUS:
                raise PersonalizedCoachingError(
                    "Learning-gap coaching used the wrong action type.",
                    code="coaching_action_type_mismatch",
                )
        elif action.basis == CoachingBasis.LOWER_PRIORITY_PREFERENCE:
            if assessment.status != EvidenceStatus.MISSING or assessment.weight >= 0.75:
                raise PersonalizedCoachingError(
                    "Lower-priority coaching did not match a lower-weight missing preference.",
                    code="coaching_basis_mismatch",
                )
            if action.action_type != CoachingActionType.LOWER_PRIORITY:
                raise PersonalizedCoachingError(
                    "Lower-priority coaching used the wrong action type.",
                    code="coaching_action_type_mismatch",
                )
        else:
            raise PersonalizedCoachingError(
                "A non-hard requirement used hard-constraint coaching.",
                code="coaching_basis_mismatch",
            )


def _request_personalized_coaching(
    analysis: SmartFitAnalysisResponse,
) -> PersonalizedCoachingPlan:
    api_key, model, base_url, timeout_seconds = _require_provider_config()
    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(analysis)},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": f"marketlens_personalized_coaching_{COACHING_SCHEMA_VERSION.replace('.', '_')}",
                "schema": _coaching_schema(),
                "strict": True,
            }
        },
        "store": False,
    }

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(
                f"{base_url}/responses",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        _logger.warning("personalized_coaching_provider_failure code=coaching_timeout")
        raise PersonalizedCoachingError(
            "Personalized coaching request timed out.",
            code="coaching_timeout",
        ) from exc
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        request_id = exc.response.headers.get("x-request-id", "unavailable")
        _logger.warning(
            "personalized_coaching_provider_failure code=coaching_http_%s request_id=%s",
            status_code,
            request_id,
        )
        raise PersonalizedCoachingError(
            f"Personalized coaching provider returned HTTP {status_code}.",
            code=f"coaching_http_{status_code}",
        ) from exc
    except httpx.HTTPError as exc:
        _logger.warning("personalized_coaching_provider_failure code=coaching_transport_error")
        raise PersonalizedCoachingError(
            "Personalized coaching provider request failed.",
            code="coaching_transport_error",
        ) from exc

    try:
        response_json = response.json()
    except json.JSONDecodeError as exc:
        _logger.warning("personalized_coaching_provider_failure code=coaching_invalid_json")
        raise PersonalizedCoachingError(
            "Personalized coaching provider response was not valid JSON.",
            code="coaching_invalid_json",
        ) from exc

    try:
        output_text = _extract_output_text(response_json)
    except ModelAssistedExtractionError as exc:
        raise PersonalizedCoachingError(
            "Personalized coaching provider response had no parseable output.",
            code="coaching_missing_output",
        ) from exc

    try:
        plan = PersonalizedCoachingPlan.model_validate_json(output_text)
    except ValidationError as exc:
        locations = [
            ".".join(str(part) for part in error.get("loc", ()))
            for error in exc.errors(include_url=False)[:3]
        ]
        _logger.warning(
            "personalized_coaching_provider_failure code=coaching_schema_mismatch fields=%s",
            ",".join(location for location in locations if location) or "unknown",
        )
        raise PersonalizedCoachingError(
            "Personalized coaching output did not match the versioned schema.",
            code="coaching_schema_mismatch",
        ) from exc

    validate_personalized_coaching(plan, analysis)
    return plan


def _to_coaching_action(item: PersonalizedCoachingAction) -> CoachingAction:
    skill = None if item.reference.startswith("hard:") else item.reference
    return CoachingAction(
        action_type=item.action_type,
        priority=item.priority,
        title=item.title,
        skill=skill,
        category=item.category,
        source_evidence=item.resume_evidence,
        job_evidence=item.job_evidence,
        advice=item.advice,
    )


def _merge_actions(
    personalized: list[CoachingAction],
    deterministic: list[CoachingAction],
) -> list[CoachingAction]:
    merged: list[CoachingAction] = []
    seen: set[tuple[str, str, str]] = set()

    for action in [*personalized, *deterministic]:
        key = (
            action.action_type.value,
            _key(action.skill or action.category or ""),
            _key(action.title),
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(action)
        if len(merged) >= MAX_PERSONALIZED_ACTIONS:
            break

    return merged


def apply_personalized_coaching(
    analysis: SmartFitAnalysisResponse,
    *,
    use_model_assisted: bool,
) -> SmartFitAnalysisResponse:
    """Add optional coaching without changing any scored analysis fields."""

    base_update = {
        "coaching_engine": "deterministic",
        "coaching_status": "not_requested",
        "coaching_version": COACHING_SCHEMA_VERSION,
    }
    if not use_model_assisted:
        return analysis.model_copy(update=base_update)

    grounded_reference_count = sum(
        assessment.grounded
        and bool(assessment.job_provenance)
        and bool(assessment.job_provenance and assessment.job_provenance.grounded)
        for assessment in analysis.requirement_assessments
    ) + sum(requirement.grounded for requirement in analysis.hard_requirements)
    if grounded_reference_count == 0:
        return analysis.model_copy(
            update={
                **base_update,
                "coaching_status": "fallback_insufficient_grounded_context",
            }
        )

    try:
        plan = _request_personalized_coaching(analysis)
    except ModelAssistedUnavailable as exc:
        return analysis.model_copy(
            update={
                **base_update,
                "coaching_status": f"fallback_unavailable: {exc}",
            }
        )
    except PersonalizedCoachingError:
        return analysis.model_copy(
            update={
                **base_update,
                "coaching_status": "fallback_failed: personalized coaching could not produce a valid grounded plan.",
            }
        )

    personalized_actions = [_to_coaching_action(item) for item in plan.action_items]
    summary = [
        f"Personalized AI coaching: {plan.strategy_summary}",
        f"Application approach: {plan.application_guidance}",
        *analysis.report_summary,
    ]
    limitations = list(analysis.limitations)
    limitations.append(
        "Personalized coaching is generated only from the completed grounded assessment; it cannot change the score, evidence status, hard requirements, or provenance."
    )
    if plan.uncertainty_note:
        limitations.append(f"Coaching uncertainty note: {plan.uncertainty_note}")

    return analysis.model_copy(
        update={
            "coaching_actions": _merge_actions(
                personalized_actions,
                analysis.coaching_actions,
            ),
            "report_summary": summary[:7],
            "limitations": limitations,
            "coaching_engine": "model_assisted",
            "coaching_status": "used",
            "coaching_version": COACHING_SCHEMA_VERSION,
        }
    )


__all__ = [
    "COACHING_PROMPT_VERSION",
    "CoachingBasis",
    "PersonalizedCoachingAction",
    "PersonalizedCoachingError",
    "PersonalizedCoachingPlan",
    "apply_personalized_coaching",
    "validate_personalized_coaching",
]
