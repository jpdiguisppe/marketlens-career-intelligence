from app.job_source_registry import default_source_identifiers
from app.job_source_routing import (
    MAX_INDUSTRY_ROUTED_SOURCES,
    build_source_routing_plan,
)


def _plan(
    *,
    industry: str | None,
    job_function: str | None = None,
    level: str = "any",
    location: str | None = None,
):
    return build_source_routing_plan(
        greenhouse_identifiers=default_source_identifiers("greenhouse"),
        lever_identifiers=default_source_identifiers("lever"),
        industry=industry,
        job_function=job_function,
        level=level,  # type: ignore[arg-type]
        location=location,
    )


def test_broad_search_uses_only_primary_sources() -> None:
    plan = _plan(industry=None, job_function="software", level="entry")

    assert plan.routed is False
    assert plan.greenhouse_identifiers == default_source_identifiers("greenhouse")
    assert plan.lever_identifiers == default_source_identifiers("lever")
    assert {"theathletic", "feldinc", "standtogether"}.isdisjoint(plan.lever_identifiers)
    assert plan.industry_only_sources_activated == 0
    assert "Industry-only boards remained inactive" in plan.lever_note


def test_financial_services_search_does_not_activate_unrelated_niche_sources() -> None:
    plan = _plan(
        industry="financial_services",
        job_function="finance",
        level="intern",
        location="Philadelphia",
    )

    selected = set(plan.greenhouse_identifiers) | set(plan.lever_identifiers)
    assert plan.routed is True
    assert plan.direct_industry_matches >= 8
    assert {"plaid", "brex", "ramp", "robinhood", "addepar"}.issubset(selected)
    assert {"theathletic", "feldinc", "standtogether"}.isdisjoint(selected)
    assert plan.industry_only_sources_activated == 0
    assert len(selected) <= MAX_INDUSTRY_ROUTED_SOURCES


def test_education_search_activates_matching_mission_source() -> None:
    plan = _plan(
        industry="education",
        job_function="software",
        level="entry",
    )

    assert "duolingo" in plan.greenhouse_identifiers
    assert "coursera" in plan.lever_identifiers
    assert "standtogether" in plan.lever_identifiers
    assert plan.industry_only_sources_activated == 1
    assert "Activated 1 matching industry-only Lever board" in plan.lever_note


def test_sports_search_activates_exact_industry_only_sources() -> None:
    plan = _plan(
        industry="sports",
        job_function="marketing",
        level="intern",
    )

    selected = set(plan.greenhouse_identifiers) | set(plan.lever_identifiers)
    assert plan.direct_industry_matches == 2
    assert {"theathletic", "feldinc"}.issubset(selected)
    assert "standtogether" not in selected
    assert plan.industry_only_sources_activated == 2
    assert "Activated 2 matching industry-only Lever boards" in plan.lever_note


def test_nonprofit_search_activates_only_stand_together() -> None:
    plan = _plan(
        industry="nonprofit",
        job_function="marketing",
        level="intern",
    )

    assert plan.direct_industry_matches == 1
    assert "standtogether" in plan.lever_identifiers
    assert "theathletic" not in plan.lever_identifiers
    assert "feldinc" not in plan.lever_identifiers
    assert plan.industry_only_sources_activated == 1


def test_unregistered_and_wrong_pool_identifiers_are_never_routed() -> None:
    plan = build_source_routing_plan(
        greenhouse_identifiers=("duolingo", "../internal", "unknown-board"),
        lever_identifiers=("coursera", "theathletic", "https://evil.example"),
        industry="education",
        job_function="software",
        level="any",
        location=None,
    )

    assert plan.greenhouse_identifiers == ("duolingo",)
    assert plan.lever_identifiers == ("coursera", "standtogether")
