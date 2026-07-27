"""Reliability patch for live Milestone 8D coaching.

The first production smoke test showed that requiring the provider to reproduce
canonical evidence strings and use each requirement only once was unnecessarily
brittle. This patch keeps references and status transitions strict, while making
the backend authoritative for the evidence attached to accepted coaching.
"""

from __future__ import annotations

import logging

import app.analysis.personalized_coaching as _coaching
from app.analysis.schemas import CoachingActionType, EvidenceStatus, SmartFitAnalysisResponse

_logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = f"""You write personalized career coaching for MarketLens Smart Fit.

Contract version: {_coaching.COACHING_SCHEMA_VERSION}
Prompt version: {_coaching.COACHING_PROMPT_VERSION}

You receive only a completed, evidence-grounded Smart Fit summary. You do not
receive the raw resume or full job description.

Rules:
- Return schema_version exactly as {_coaching.COACHING_SCHEMA_VERSION!r}.
- Never change, reinterpret, or dispute the supplied score, band, status, weight, hard constraint, or evidence.
- Every action.reference must exactly equal one requirements[].reference or hard_requirements[].reference value.
- Never use a title, category, evidence quote, or summary phrase as the reference.
- Set resume_evidence to [] and job_evidence to null. MarketLens attaches the canonical verified evidence after validation.
- Never invent experience, projects, coursework, credentials, outcomes, metrics, or evidence.
- A demonstrated or explicit requirement may support strength_positioning.
- A mentioned, implied, or related requirement may support wording_proof_gap.
- A missing high-priority requirement may support experience_learning_gap.
- A lower-weight missing preference may support lower_priority_preference.
- A hard:* reference may support only hard_constraint_check.
- Distinct actions may reuse a reference only when their action_type or basis differs.
- Distinguish resume wording fixes from real learning or experience gaps.
- Suggestions may describe what the candidate could build, learn, verify, or rewrite, but must not claim they already did it.
- Do not predict hiring probability, ATS success, interview selection, or an offer.
- Keep advice concrete, truthful, concise, and immediately actionable.
- Return every schema field. Use null for nullable fields and [] for empty lists.
- Return only schema-valid JSON with no extra fields.
"""


def _reference_only_context(analysis: SmartFitAnalysisResponse) -> dict:
    """Expose only scored references and their already-grounded evidence."""

    requirements = [
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
    ]
    hard_requirements = [
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
    ]
    return {
        "fit_summary": {
            "score": analysis.fit_summary.score,
            "band": analysis.fit_summary.band.value,
            "headline": analysis.fit_summary.headline,
        },
        "allowed_references": [
            item["reference"] for item in [*requirements, *hard_requirements]
        ],
        "requirements": requirements,
        "hard_requirements": hard_requirements,
    }


def _validate_all_language(plan: _coaching.PersonalizedCoachingPlan) -> None:
    combined = " ".join(
        [
            plan.strategy_summary,
            plan.application_guidance,
            *(item.title for item in plan.action_items),
            *(item.advice for item in plan.action_items),
        ]
    ).casefold()
    banned = (
        "guaranteed offer",
        "guaranteed interview",
        "will get hired",
        "will be hired",
        "ats score",
        "hiring probability",
    )
    if any(phrase in combined for phrase in banned) or "% chance" in combined:
        raise _coaching.PersonalizedCoachingError(
            "Provider coaching included an unsupported hiring prediction.",
            code="coaching_unsupported_prediction",
        )


def _validate_and_hydrate(
    plan: _coaching.PersonalizedCoachingPlan,
    analysis: SmartFitAnalysisResponse,
) -> None:
    """Validate references and attach canonical evidence owned by MarketLens."""

    _validate_all_language(plan)
    assessments = _coaching._assessment_map(analysis)
    hard_requirements = _coaching._hard_requirement_map(analysis)
    seen_actions: set[tuple[str, str, str]] = set()

    for action in plan.action_items:
        reference_key = _coaching._key(action.reference)
        action_key = (reference_key, action.action_type.value, action.basis.value)
        if action_key in seen_actions:
            raise _coaching.PersonalizedCoachingError(
                f"Provider coaching repeated the same action for {action.reference!r}.",
                code="coaching_duplicate_action",
            )
        seen_actions.add(action_key)

        if reference_key in hard_requirements:
            requirement = hard_requirements[reference_key]
            if not requirement.grounded:
                raise _coaching.PersonalizedCoachingError(
                    "Provider coaching referenced an ungrounded hard requirement.",
                    code="coaching_ungrounded_reference",
                )
            if action.basis != _coaching.CoachingBasis.HARD_CONSTRAINT_CHECK:
                raise _coaching.PersonalizedCoachingError(
                    "Hard requirements may only produce verification coaching.",
                    code="coaching_basis_mismatch",
                )
            if action.action_type != CoachingActionType.HARD_REQUIREMENT_CHECK:
                raise _coaching.PersonalizedCoachingError(
                    "Hard requirement coaching used the wrong action type.",
                    code="coaching_action_type_mismatch",
                )
            canonical_resume = [requirement.resume_evidence] if requirement.resume_evidence else []
            if action.job_evidence not in {None, requirement.source_text}:
                raise _coaching.PersonalizedCoachingError(
                    "Hard requirement coaching changed the grounded job quote.",
                    code="coaching_job_evidence_mismatch",
                )
            if any(item not in canonical_resume for item in action.resume_evidence):
                raise _coaching.PersonalizedCoachingError(
                    "Hard requirement coaching invented resume evidence.",
                    code="coaching_resume_evidence_mismatch",
                )
            action.category = requirement.category
            action.job_evidence = requirement.source_text
            action.resume_evidence = canonical_resume
            continue

        assessment = assessments.get(reference_key)
        if assessment is None:
            raise _coaching.PersonalizedCoachingError(
                f"Provider coaching referenced unknown requirement {action.reference!r}.",
                code="coaching_unknown_reference",
            )
        if (
            not assessment.grounded
            or not assessment.job_provenance
            or not assessment.job_provenance.grounded
        ):
            raise _coaching.PersonalizedCoachingError(
                "Provider coaching referenced an ungrounded assessment.",
                code="coaching_ungrounded_reference",
            )
        if action.job_evidence not in {None, assessment.job_evidence}:
            raise _coaching.PersonalizedCoachingError(
                "Provider coaching changed the grounded job quote.",
                code="coaching_job_evidence_mismatch",
            )
        if any(item not in assessment.resume_evidence for item in action.resume_evidence):
            raise _coaching.PersonalizedCoachingError(
                "Provider coaching invented resume evidence.",
                code="coaching_resume_evidence_mismatch",
            )

        if action.basis == _coaching.CoachingBasis.STRENGTH_POSITIONING:
            if assessment.status not in {EvidenceStatus.DEMONSTRATED, EvidenceStatus.EXPLICIT}:
                raise _coaching.PersonalizedCoachingError(
                    "Strength coaching was not backed by strong resume evidence.",
                    code="coaching_basis_mismatch",
                )
            if action.action_type not in {
                CoachingActionType.INTERVIEW_PREP,
                CoachingActionType.RESUME_REWRITE,
            }:
                raise _coaching.PersonalizedCoachingError(
                    "Strength coaching used an incompatible action type.",
                    code="coaching_action_type_mismatch",
                )
            canonical_resume = list(assessment.resume_evidence)
        elif action.basis == _coaching.CoachingBasis.WORDING_PROOF_GAP:
            if assessment.status not in {
                EvidenceStatus.MENTIONED,
                EvidenceStatus.IMPLIED,
                EvidenceStatus.RELATED,
            }:
                raise _coaching.PersonalizedCoachingError(
                    "Wording-gap coaching did not match the assessment status.",
                    code="coaching_basis_mismatch",
                )
            if action.action_type not in {
                CoachingActionType.RESUME_REWRITE,
                CoachingActionType.INTERVIEW_PREP,
            }:
                raise _coaching.PersonalizedCoachingError(
                    "Wording-gap coaching used an incompatible action type.",
                    code="coaching_action_type_mismatch",
                )
            canonical_resume = list(assessment.resume_evidence)
        elif action.basis == _coaching.CoachingBasis.EXPERIENCE_LEARNING_GAP:
            if assessment.status != EvidenceStatus.MISSING or assessment.weight < 0.75:
                raise _coaching.PersonalizedCoachingError(
                    "Learning-gap coaching did not match a high-priority missing requirement.",
                    code="coaching_basis_mismatch",
                )
            if action.action_type != CoachingActionType.LEARNING_FOCUS:
                raise _coaching.PersonalizedCoachingError(
                    "Learning-gap coaching used the wrong action type.",
                    code="coaching_action_type_mismatch",
                )
            canonical_resume = []
        elif action.basis == _coaching.CoachingBasis.LOWER_PRIORITY_PREFERENCE:
            if assessment.status != EvidenceStatus.MISSING or assessment.weight >= 0.75:
                raise _coaching.PersonalizedCoachingError(
                    "Lower-priority coaching did not match a lower-weight missing preference.",
                    code="coaching_basis_mismatch",
                )
            if action.action_type != CoachingActionType.LOWER_PRIORITY:
                raise _coaching.PersonalizedCoachingError(
                    "Lower-priority coaching used the wrong action type.",
                    code="coaching_action_type_mismatch",
                )
            canonical_resume = []
        else:
            raise _coaching.PersonalizedCoachingError(
                "A non-hard requirement used hard-constraint coaching.",
                code="coaching_basis_mismatch",
            )

        action.job_evidence = assessment.job_evidence
        action.resume_evidence = canonical_resume


def install_personalized_coaching_reliability_patch() -> None:
    if getattr(_coaching, "_live_reliability_patch_installed", False):
        return

    original_request = _coaching._request_personalized_coaching

    def logged_request(analysis: SmartFitAnalysisResponse):
        try:
            return original_request(analysis)
        except _coaching.PersonalizedCoachingError as exc:
            _logger.warning(
                "personalized_coaching_provider_failure code=%s",
                exc.code,
            )
            raise

    _coaching._analysis_context = _reference_only_context
    _coaching._SYSTEM_PROMPT = _SYSTEM_PROMPT
    _coaching.validate_personalized_coaching = _validate_and_hydrate
    _coaching._request_personalized_coaching = logged_request
    _coaching._live_reliability_patch_installed = True


__all__ = ["install_personalized_coaching_reliability_patch"]
