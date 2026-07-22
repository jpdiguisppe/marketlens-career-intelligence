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


def test_registry_preserves_existing_default_provider_order() -> None:
    assert default_source_identifiers("greenhouse") == EXPECTED_GREENHOUSE_BOARDS
    assert default_source_identifiers("lever") == EXPECTED_LEVER_SITES
    assert DEFAULT_GREENHOUSE_BOARDS == EXPECTED_GREENHOUSE_BOARDS
    assert DEFAULT_LEVER_SITES == EXPECTED_LEVER_SITES


def test_registry_exposes_industry_and_function_metadata_for_routing() -> None:
    duolingo = find_source("duolingo", "greenhouse")
    twitch = find_source("twitch", "lever")
    addepar = find_source("addepar", "lever")
    the_athletic = find_source("theathletic", "lever")
    feld = find_source("feldinc", "lever")
    stand_together = find_source("standtogether", "lever")

    assert duolingo is not None
    assert "education" in duolingo.industries
    assert "software" in duolingo.role_families

    assert twitch is not None
    assert {"entertainment", "media"}.issubset(twitch.industries)
    assert "marketing" in twitch.role_families

    assert addepar is not None
    assert "financial_services" in addepar.industries
    assert "finance" in addepar.role_families

    assert the_athletic is not None
    assert {"sports", "media"}.issubset(the_athletic.industries)
    assert "marketing" in the_athletic.role_families

    assert feld is not None
    assert {"sports", "entertainment"}.issubset(feld.industries)
    assert "operations" in feld.role_families

    assert stand_together is not None
    assert {"nonprofit", "education"}.issubset(stand_together.industries)
    assert stand_together.early_career_relevance == "strong"


def test_registry_lookup_and_company_name_fallbacks_are_stable() -> None:
    assert organization_name("github", "lever") == "GitHub"
    assert organization_name("theathletic", "lever") == "The Athletic"
    assert _provider_company_name("doordash") == "DoorDash"
    assert organization_name("example-company") == "Example Company"
    assert find_source("missing-source", "greenhouse") is None


def test_registry_can_filter_by_provider() -> None:
    greenhouse_entries = source_registry_entries("greenhouse")
    lever_entries = source_registry_entries("lever")

    assert len(greenhouse_entries) == len(EXPECTED_GREENHOUSE_BOARDS)
    assert len(lever_entries) == len(EXPECTED_LEVER_SITES)
    assert all(entry.provider == "greenhouse" for entry in greenhouse_entries)
    assert all(entry.provider == "lever" for entry in lever_entries)


def test_uncached_broad_search_keeps_remote_feed_request_headroom() -> None:
    ats_source_count = len(EXPECTED_GREENHOUSE_BOARDS) + len(EXPECTED_LEVER_SITES)

    assert ats_source_count <= DEFAULT_MAX_PROVIDER_REQUESTS_PER_SEARCH - 3


def test_registry_rejects_malformed_and_unregistered_identifiers() -> None:
    assert normalize_source_identifier("github") == "github"
    assert normalize_source_identifier("../internal") is None
    assert normalize_source_identifier("https://evil.example") is None
    assert normalize_source_identifier("name with spaces") is None
    assert find_source("../internal", "lever") is None


def test_environment_source_configuration_is_registry_allowlisted() -> None:
    assert configured_source_identifiers(
        "lever",
        " github,../internal,unknown-company,github, theathletic ",
    ) == ("github", "theathletic")
    assert configured_source_identifiers(
        "greenhouse",
        "https://evil.example,unknown-company",
    ) == EXPECTED_GREENHOUSE_BOARDS
