from app.job_search import (
    DEFAULT_GREENHOUSE_BOARDS,
    DEFAULT_LEVER_SITES,
    _provider_company_name,
)
from app.job_source_registry import (
    SOURCE_REGISTRY,
    default_source_identifiers,
    find_source,
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


def test_registry_exposes_industry_and_function_metadata_for_future_routing() -> None:
    duolingo = find_source("duolingo", "greenhouse")
    twitch = find_source("twitch", "lever")
    addepar = find_source("addepar", "lever")

    assert duolingo is not None
    assert "education" in duolingo.industries
    assert "software" in duolingo.role_families

    assert twitch is not None
    assert {"entertainment", "media"}.issubset(twitch.industries)
    assert "marketing" in twitch.role_families

    assert addepar is not None
    assert "financial_services" in addepar.industries
    assert "finance" in addepar.role_families


def test_registry_lookup_and_company_name_fallbacks_are_stable() -> None:
    assert organization_name("github", "lever") == "GitHub"
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
