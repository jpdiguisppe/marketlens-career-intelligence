"""Backend-owned display titles for live Milestone 8D coaching.

Structured Outputs intentionally omits local string-length metadata because the
provider supports only a JSON Schema subset. A provider may therefore return an
empty or very short display title even when the reference, basis, action type,
and advice are valid. MarketLens treats titles as presentation text: it accepts a
short placeholder for parsing, validates the consequential coaching fields, and
then generates a deterministic title from the validated action.
"""

from __future__ import annotations

import json

import app.analysis.personalized_coaching as _coaching
from app.analysis.schemas import CoachingActionType


_PARSE_PLACEHOLDER_TITLE = "Pending action"


def _canonical_title(action: _coaching.PersonalizedCoachingAction) -> str:
    reference = action.reference.strip()

    if action.basis == _coaching.CoachingBasis.HARD_CONSTRAINT_CHECK:
        category = reference.removeprefix("hard:").replace("_", " ").strip()
        return f"Verify {category or 'hard'} requirement"[:120]

    if action.basis == _coaching.CoachingBasis.STRENGTH_POSITIONING:
        if action.action_type == CoachingActionType.INTERVIEW_PREP:
            return f"Prepare the {reference} interview story"[:120]
        return f"Highlight existing {reference} proof"[:120]

    if action.basis == _coaching.CoachingBasis.WORDING_PROOF_GAP:
        if action.action_type == CoachingActionType.INTERVIEW_PREP:
            return f"Clarify the {reference} experience"[:120]
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

    def validate_and_hydrate_title(plan, analysis) -> None:
        original_validate(plan, analysis)
        for action in plan.action_items:
            action.title = _canonical_title(action)

    _coaching.PersonalizedCoachingPlan.model_validate_json = classmethod(
        model_validate_json_with_title_placeholder
    )
    _coaching.validate_personalized_coaching = validate_and_hydrate_title
    _coaching._SYSTEM_PROMPT += (
        "\n- Set title to an empty string. MarketLens generates the final display title "
        "after validating the reference, basis, and action type."
    )
    _coaching._title_hydration_patch_installed = True


__all__ = ["install_personalized_coaching_title_patch"]
