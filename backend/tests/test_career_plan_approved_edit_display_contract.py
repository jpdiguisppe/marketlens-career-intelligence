from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CAREER_PLAN_API_SOURCE = REPOSITORY_ROOT / "frontend" / "src" / "careerPlansApi.ts"


def test_frontend_overlays_saved_approved_edits_without_mutating_backend_proposal() -> None:
    source = CAREER_PLAN_API_SOURCE.read_text(encoding="utf-8")

    assert "function withApprovedEditsForDisplay" in source
    assert 'approval.decision !== "approved"' in source
    assert "generatedActionIds.has(action.id)" in source
    assert "const editsById = new Map" in source
    assert "actions: run.proposal.actions.map" in source
    assert source.count("return withApprovedEditsForDisplay(run);") == 5


def test_frontend_approved_edit_overlay_is_bounded_to_known_action_ids() -> None:
    source = CAREER_PLAN_API_SOURCE.read_text(encoding="utf-8")

    assert "new Set(run.proposal.actions.map" in source
    assert "isCareerPlanAction(action)" in source
    assert "generatedActionIds.has(action.id)" in source
