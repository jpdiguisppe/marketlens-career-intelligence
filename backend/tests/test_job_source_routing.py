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


def test_broad_search_preserves_full_configured_registry_order() -> None:
    plan = _plan(industry=None, job_function="software", level="entry")

    assert plan.routed is False
    assert plan.greenhouse_identifiers == default_source_identifiers("greenhouse")
    assert plan.lever_identifiers == default_source_identifiers("lever")
    assert "kept all" in plan.greenhouse_note
    assert "kept all" in plan.lever_note


def test_financial_services_search_prioritizes_fintech_sources() -> None:
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
    assert len(selected) <= MAX_INDUSTRY_ROUTED_SOURCES
    assert "industry=financial_services" in plan.greenhouse_note
    assert "function=finance" in plan.lever_note
    assert "level=intern" in plan.greenhouse_note


def test_education_search_keeps_direct_sources_and_provider_diversity() -> None:
    plan = _plan(
        industry="education",
        job_function="software",
        level="entry",
    )

    assert "duolingo" in plan.greenhouse_identifiers
    assert "coursera" in plan.lever_identifiers
    assert len(plan.greenhouse_identifiers) >= 2
    assert len(plan.lever_identifiers) >= 2
    assert plan.direct_industry_matches == 2


def test_sports_search_uses_adjacent_sources_until_exact_boards_are_added() -> None:
    plan = _plan(
        industry="sports",
        job_function="marketing",
        level="intern",
    )

    selected = set(plan.greenhouse_identifiers) | set(plan.lever_identifiers)
    assert plan.direct_industry_matches == 0
    assert {"roblox", "twitch"}.issubset(selected)
    assert "No exact-industry registry match" in plan.greenhouse_note
    assert "No exact-industry registry match" in plan.lever_note


def test_unregistered_identifiers_are_never_routed() -> None:
    plan = build_source_routing_plan(
        greenhouse_identifiers=("duolingo", "../internal", "unknown-board"),
        lever_identifiers=("coursera", "https://evil.example"),
        industry="education",
        job_function="software",
        level="any",
        location=None,
    )

    assert plan.greenhouse_identifiers == ("duolingo",)
    assert plan.lever_identifiers == ("coursera",)
