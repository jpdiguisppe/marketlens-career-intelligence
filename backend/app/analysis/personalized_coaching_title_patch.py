"""Backend-owned display fields for live Milestone 8D coaching.

Structured Outputs intentionally omits some local validation metadata because the
provider supports only a JSON Schema subset. Provider-selected display titles and
action types are not evidence-bearing facts, so MarketLens normalizes them before
consequential validation and derives the final values from the validated coaching
basis and grounded reference.
"""

from __future__ import annotations

import json

import app.analysis.personalized_coaching as _coaching
from app.analysis.schemas import CoachingActionType


_PARSE_PLACEHOLDER_TITLE = "Pending action"


_ACTION_TYPE_BY_BASIS = {
    _coaching.CoachingBasis.STRENGTH_POSITIONING: CoachingActionType.INTERVIEW_PREP,
    _coaching.CoachingBasis.WORDING_PROOF_GAP: CoachingActionType.RESUME_REWRITE,
    _coaching.CoachingBasis.EXPERIENCE_LEARNING_GAP: CoachingActionType.LEARNING_FOCUS,
    _coaching.CoachingBasis.HARD_CONSTRAINT_CHECK: CoachingActionType.HARD_REQUIREMENT_CHECK,
    _coaching.CoachingBasis.LOWER_PRIORITY_PREFERENCE: CoachingActionType.LOWER_PRIORITY,
}


def _canonical_action_type(
    action: _coaching.PersonalizedCoachingAction,
) -> CoachingActionType:
    return _ACTION_TYPE_BY_BASIS[action.basis]


def _canonical_title(action: _coaching.PersonalizedCoachingAction) -> str:
    reference = action.reference.strip()

    if action.basis == _coaching.CoachingBasis.HARD_CONSTRAINT_CHECK:
        category = reference.removeprefix("hard:").replace("_", " ").strip()
        return f"Verify {category or 'hard'} requirement"[:120]

    if action.basis == _coaching.CoachingBasis.STRENGTH_POSITIONING:
        return f"Prepare the {reference} interview story"[:120]

    if action.basis == _coaching.CoachingBasis.WORDING_PROOF_GAP:
        return f"Strengthen {reference} resume proof"[:120]

    if action.basis == _coaching.CoachingBasis.EXPERIENCE_LEARNING_GAP:
        return f"Build evidence for {reference}"[:120]

    if action.basis == _coaching.CoachingBasis.LOWER_PRIORITY_PREFERENCE:
        return f"Keep {reference} as a lower priority"[:120]

    return f"Review {reference}"[:120]


def install_personalized_coaching_title_patch() -> None:
    if getattr(_coaching, "_title_hydration_patch_installed", False):
        return

    original_model_validate_json = _coaching.PersonalizedCoachingPlan.model_validate_json
    original_validate = _coaching.validate_personalized_coaching

    def model_validate_json_with_title_placeholder(cls, json_data, *args, **kwargs):
        try:
            payload = json.loads(json_data)
        except (TypeError, json.JSONDecodeError):
            return original_model_validate_json(json_data, *args, **kwargs)

        if isinstance(payload, dict):
            action_items = payload.get("action_items")
            if isinstance(action_items, list):
                for item in action_items:
                    if not isinstance(item, dict):
                        continue
                    title = item.get("title")
                    if not isinstance(title, str) or len(title.strip()) < 3:
                        item["title"] = _PARSE_PLACEHOLDER_TITLE

        normalized_json = json.dumps(payload, ensure_ascii=False)
        return original_model_validate_json(normalized_json, *args, **kwargs)

    def validate_and_hydrate_display_fields(plan, analysis) -> None:
        for action in plan.action_items:
            action.action_type = _canonical_action_type(action)

        original_validate(plan, analysis)

        for action in plan.action_items:
            action.title = _canonical_title(action)

    _coaching.PersonalizedCoachingPlan.model_validate_json = classmethod(
        model_validate_json_with_title_placeholder
    )
    _coaching.validate_personalized_coaching = validate_and_hydrate_display_fields
    _coaching._SYSTEM_PROMPT += (
        "\n- Set title to an empty string and action_type to 'resume_rewrite' as "
        "placeholders. MarketLens generates the final display title and action type "
        "after validating the reference and basis."
    )
    _coaching._title_hydration_patch_installed = True


__all__ = ["install_personalized_coaching_title_patch"]
