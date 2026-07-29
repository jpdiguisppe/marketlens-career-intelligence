from __future__ import annotations

from app.career_plans.schemas import (
    CareerPlanExplanationRequest,
    CareerPlanExplanationResponse,
    CareerPlanExplanationType,
    CareerPlanProposal,
)

EXPLANATION_ENGINE = "deterministic_saved_plan_explanation_v1"


class CareerPlanExplanationError(RuntimeError):
    def __init__(self, message: str, *, code: str = "explanation_unavailable") -> None:
        super().__init__(message)
        self.code = code


def _job_explanation(
    proposal: CareerPlanProposal,
    reference_id: str,
    run_version: int,
) -> CareerPlanExplanationResponse:
    entry = next((item for item in proposal.portfolio if item.job_ref == reference_id), None)
    if entry is None:
        raise CareerPlanExplanationError(
            "The requested job is not part of this saved Career Plan.",
            code="explanation_unknown_job",
        )

    reason_text = ", ".join(code.replace("_", " ") for code in entry.reason_codes) or "saved deterministic fit rules"
    hard_text = (
        " Hard-requirement flags: " + ", ".join(entry.hard_requirement_flags) + "."
        if entry.hard_requirement_flags
        else " No hard-requirement failure was stored for this opportunity."
    )
    answer = (
        f"{entry.title} at {entry.company} is classified as {entry.category.value.replace('_', ' ')} "
        f"from the saved Smart Fit score of {entry.fit_score}/100, confidence {entry.confidence:.2f}, "
        f"and reason basis: {reason_text}.{hard_text} This is an application-strategy category, not a hiring prediction."
    )
    return CareerPlanExplanationResponse(
        explanation_type=CareerPlanExplanationType.WHY_JOB,
        reference_id=reference_id,
        answer=answer[:2_000],
        evidence_refs=(entry.evidence_refs + entry.gap_refs)[:50],
        engine=EXPLANATION_ENGINE,
        based_on_run_version=run_version,
    )


def _action_explanation(
    proposal: CareerPlanProposal,
    reference_id: str,
    run_version: int,
) -> CareerPlanExplanationResponse:
    action = next((item for item in proposal.actions if item.id == reference_id), None)
    if action is None:
        raise CareerPlanExplanationError(
            "The requested action is not part of this saved Career Plan.",
            code="explanation_unknown_action",
        )

    job_scope = ", ".join(action.job_refs) if action.job_refs else "the overall saved plan"
    answer = (
        f"{action.title} is a {action.priority}-priority {action.action_type.value.replace('_', ' ')} action "
        f"for {job_scope}. The deterministic rationale is: {action.rationale[:1_200]} "
        "The action remains a proposal until the user approves or edits the plan."
    )
    return CareerPlanExplanationResponse(
        explanation_type=CareerPlanExplanationType.WHY_ACTION,
        reference_id=reference_id,
        answer=answer[:2_000],
        evidence_refs=action.evidence_refs,
        engine=EXPLANATION_ENGINE,
        based_on_run_version=run_version,
    )


def _gap_explanation(
    proposal: CareerPlanProposal,
    reference_id: str,
    run_version: int,
) -> CareerPlanExplanationResponse:
    normalized = reference_id.strip().casefold()
    gap = next(
        (item for item in proposal.recurring_gaps if item.capability.casefold() == normalized),
        None,
    )
    if gap is None:
        raise CareerPlanExplanationError(
            "The requested recurring gap is not part of this saved Career Plan.",
            code="explanation_unknown_gap",
        )

    priority = gap.priority or "unranked"
    answer = (
        f"{gap.capability} is stored as a {priority}-priority recurring gap because it appears across "
        f"{gap.job_count} analyzed opportunities: {', '.join(gap.job_refs)}. "
        "This means the supplied résumé did not show enough evidence for those saved requirements; it does not prove the user lacks the capability."
    )
    return CareerPlanExplanationResponse(
        explanation_type=CareerPlanExplanationType.WHY_GAP,
        reference_id=reference_id,
        answer=answer[:2_000],
        evidence_refs=gap.evidence_refs,
        engine=EXPLANATION_ENGINE,
        based_on_run_version=run_version,
    )


def _model_assistance_explanation(
    proposal: CareerPlanProposal,
    run_version: int,
) -> CareerPlanExplanationResponse:
    assistance = proposal.model_assisted
    if assistance is None:
        answer = "This saved proposal predates the bounded model-assistance envelope. Its portfolio and actions are deterministic."
    elif assistance.status == "used":
        answer = (
            f"Model assistance used prompt {assistance.prompt_version} and schema {assistance.schema_version} "
            "to select ordering, focus codes, and emphasis from existing IDs. MarketLens rendered the displayed summaries deterministically. "
            "The model could not change scores, categories, evidence statuses, hard requirements, provenance, actions, or approval state."
        )
    elif assistance.status == "not_requested":
        answer = "Model assistance was not requested. The complete saved proposal was generated deterministically."
    else:
        answer = (
            f"Model assistance fell back with safe status {assistance.telemetry.status_code}. "
            "The complete deterministic proposal was preserved and no model-generated selection affected the plan."
        )

    return CareerPlanExplanationResponse(
        explanation_type=CareerPlanExplanationType.MODEL_ASSISTANCE,
        reference_id=None,
        answer=answer[:2_000],
        evidence_refs=[],
        engine=EXPLANATION_ENGINE,
        based_on_run_version=run_version,
    )


def explain_saved_career_plan(
    proposal: CareerPlanProposal,
    request: CareerPlanExplanationRequest,
    run_version: int,
) -> CareerPlanExplanationResponse:
    if request.explanation_type == CareerPlanExplanationType.WHY_JOB:
        return _job_explanation(proposal, request.reference_id or "", run_version)
    if request.explanation_type == CareerPlanExplanationType.WHY_ACTION:
        return _action_explanation(proposal, request.reference_id or "", run_version)
    if request.explanation_type == CareerPlanExplanationType.WHY_GAP:
        return _gap_explanation(proposal, request.reference_id or "", run_version)
    return _model_assistance_explanation(proposal, run_version)


__all__ = [
    "CareerPlanExplanationError",
    "EXPLANATION_ENGINE",
    "explain_saved_career_plan",
]
