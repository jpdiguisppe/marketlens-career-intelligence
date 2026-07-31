from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ROUTER_SOURCE = REPOSITORY_ROOT / "frontend" / "src" / "WorkspaceRouter.tsx"
TABLET_STYLES = REPOSITORY_ROOT / "frontend" / "src" / "careerPlanTabletLayout.css"


def test_tablet_layout_override_loads_after_workspace_styles() -> None:
    source = ROUTER_SOURCE.read_text(encoding="utf-8")

    assert source.index('import "./workspaceRouter.css";') < source.index(
        'import "./careerPlanTabletLayout.css";'
    )


def test_career_plan_columns_can_shrink_without_overlap() -> None:
    source = TABLET_STYLES.read_text(encoding="utf-8")

    assert ".career-plan-sidebar," in source
    assert ".career-plan-main," in source
    assert ".career-plan-form-grid > *" in source
    assert ".career-plan-card," in source
    assert "min-width: 0;" in source


def test_career_plan_tablet_density_reduces_before_full_stack() -> None:
    source = TABLET_STYLES.read_text(encoding="utf-8")

    tablet = source.split("@media (max-width: 1120px)", 1)[1].split(
        "@media (max-width: 1040px)", 1
    )[0]
    assert ".career-plan-form-grid" in tablet
    assert "grid-template-columns: 1fr;" in tablet

    stacked = source.split("@media (max-width: 1040px)", 1)[1]
    assert ".career-plan-hero," in stacked
    assert ".career-plan-layout" in stacked
    assert "grid-template-columns: 1fr;" in stacked
    assert ".career-plan-sidebar" in stacked
    assert "position: static;" in stacked
