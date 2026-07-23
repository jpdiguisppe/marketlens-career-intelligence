from app.job_search import (
    DEFAULT_GREENHOUSE_BOARDS,
    DEFAULT_LEVER_SITES,
    DEFAULT_MAX_PROVIDER_REQUESTS_PER_SEARCH,
    _provider_company_name,
)
from app.job_source_registry import (
    SOURCE_REGISTRY,
    configured_source_identifiers,
    default_source_identifiers,
    find_source,
    industry_source_identifiers,
    normalize_source_identifier,
    organization_name,
    source_registry_entries,
)


EXPECTED_GREENHOUSE_BOARDS = (
    "datadog",
    "airbnb",
    "figma",
    "duolingo",
    "roblox",
    "scaleai",
    "hubspot",
    "cloudflare",
    "verkada",
    "doordash",
    "okta",
    "mongodb",
    "asana",
    "plaid",
    "brex",
    "coinbase",
    "ramp",
    "gusto",
    "rippling",
    "affirm",
)
EXPECTED_LEVER_SITES = (
    "github",
    "postman",
    "benchling",
    "box",
    "coursera",
    "lyft",
    "pinterest",
    "reddit",
    "snap",
    "twitch",
    "zapier",
    "affirm",
    "robinhood",
    "rippling",
    "webflow",
    "notion",
    "loom",
    "intercom",
    "mixpanel",
    "fivetran",
    "algolia",
    "addepar",
)
EXPECTED_GREENHOUSE_INDUSTRY_BOARDS = ("aclu",)
EXPECTED_LEVER_INDUSTRY_SITES = (
    "avalerehealth",
    "wattpad",
    "thedispatch",
    "kiddom",
    "stradaeducation",
    "theathletic",
    "feldinc",
    "standtogether",
)


def test_registry_keys_are_unique_and_metadata_is_complete() -> None:
    keys = [(entry.provider, entry.identifier) for entry in SOURCE_REGISTRY]

    assert len(keys) == len(set(keys))
    assert all(entry.organization for entry in SOURCE_REGISTRY)
    assert all(entry.industries for entry in SOURCE_REGISTRY)
    assert all(entry.role_families for entry in SOURCE_REGISTRY)
    assert all(entry.geographic_focus for entry in SOURCE_REGISTRY)
    assert all(entry.coverage_note for entry in SOURCE_REGISTRY)
    assert all(entry.source_pool in {"primary", "industry_only"} for entry in SOURCE_REGISTRY)


def test_registry_separates_primary_and_industry_only_defaults() -> None:
    assert default_source_identifiers("greenhouse") == EXPECTED_GREENHOUSE_BOARDS
    assert default_source_identifiers("lever") == EXPECTED_LEVER_SITES
    assert industry_source_identifiers("greenhouse") == EXPECTED_GREENHOUSE_INDUSTRY_BOARDS
    assert industry_source_identifiers("lever") == EXPECTED_LEVER_INDUSTRY_SITES
    assert DEFAULT_GREENHOUSE_BOARDS == EXPECTED_GREENHOUSE_BOARDS
    assert DEFAULT_LEVER_SITES == EXPECTED_LEVER_SITES


def test_registry_exposes_industry_metadata_and_source_pool() -> None:
    duolingo = find_source("duolingo", "greenhouse")
    the_athletic = find_source("theathletic", "lever")
    feld = find_source("feldinc", "lever")
    stand_together = find_source("standtogether", "lever")
    aclu = find_source("aclu", "greenhouse")
    avalere = find_source("avalerehealth", "lever")
    wattpad = find_source("wattpad", "lever")
    dispatch = find_source("thedispatch", "lever")
    strada = find_source("stradaeducation", "lever")

    assert duolingo is not None
    assert duolingo.source_pool == "primary"

    assert the_athletic is not None
    assert {"sports", "media"}.issubset(the_athletic.industries)
    assert the_athletic.source_pool == "industry_only"

    assert feld is not None
    assert {"sports", "entertainment"}.issubset(feld.industries)
    assert feld.source_pool == "industry_only"

    assert stand_together is not None
    assert {"nonprofit", "education"}.issubset(stand_together.industries)
    assert stand_together.source_pool == "industry_only"
    assert stand_together.early_career_relevance == "strong"

    assert aclu is not None
    assert {"legal_services", "public_interest"}.issubset(aclu.industries)
    assert aclu.source_pool == "industry_only"

    assert avalere is not None
    assert {"healthcare", "public_policy"}.issubset(avalere.industries)
    assert "compliance" in avalere.role_families

    assert wattpad is not None
    assert {"media", "corporate_legal"}.issubset(wattpad.industries)
    assert wattpad.early_career_relevance == "strong"

    assert dispatch is not None
    assert {"media", "legal_services"}.issubset(dispatch.industries)
    assert dispatch.early_career_relevance == "strong"

    assert strada is not None
    assert {"education", "public_interest"}.issubset(strada.industries)
    assert strada.early_career_relevance == "strong"


def test_registry_lookup_and_company_name_fallbacks_are_stable() -> None:
    assert organization_name("github", "lever") == "GitHub"
    assert organization_name("theathletic", "lever") == "The Athletic"
    assert _provider_company_name("doordash") == "DoorDash"
    assert organization_name("example-company") == "Example Company"
    assert find_source("missing-source", "greenhouse") is None


def test_registry_can_filter_by_provider_and_pool() -> None:
    primary_lever = source_registry_entries("lever", source_pool="primary")
    industry_lever = source_registry_entries("lever", source_pool="industry_only")

    assert len(primary_lever) == len(EXPECTED_LEVER_SITES)
    assert len(industry_lever) == len(EXPECTED_LEVER_INDUSTRY_SITES)
    assert all(entry.provider == "lever" for entry in primary_lever + industry_lever)


def test_uncached_broad_search_gains_request_headroom() -> None:
    ats_source_count = len(EXPECTED_GREENHOUSE_BOARDS) + len(EXPECTED_LEVER_SITES)

    assert ats_source_count <= DEFAULT_MAX_PROVIDER_REQUESTS_PER_SEARCH - 6


def test_registry_rejects_malformed_and_unregistered_identifiers() -> None:
    assert normalize_source_identifier("github") == "github"
    assert normalize_source_identifier("../internal") is None
    assert normalize_source_identifier("https://evil.example") is None
    assert normalize_source_identifier("name with spaces") is None
    assert find_source("../internal", "lever") is None


def test_environment_configuration_cannot_move_sources_between_pools() -> None:
    assert configured_source_identifiers(
        "lever",
        " github,../internal,unknown-company,theathletic ",
    ) == ("github",)
    assert configured_source_identifiers(
        "lever",
        " github,theathletic,feldinc ",
        source_pool="industry_only",
    ) == ("theathletic", "feldinc")
    assert configured_source_identifiers(
        "greenhouse",
        "https://evil.example,unknown-company",
    ) == EXPECTED_GREENHOUSE_BOARDS
