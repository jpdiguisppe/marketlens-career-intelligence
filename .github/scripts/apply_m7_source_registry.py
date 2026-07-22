from pathlib import Path
import re

job_search_path = Path("backend/app/job_search.py")
registry_path = Path("backend/app/job_source_registry.py")
test_path = Path("backend/tests/test_job_source_registry.py")
docs_path = Path("docs/milestone-7-source-registry.md")

job_search = job_search_path.read_text()

old_import = "import httpx\n"
new_import = "import httpx\n\nfrom app.job_source_registry import default_source_identifiers, organization_name\n"
if job_search.count(old_import) != 1:
    raise RuntimeError(f"Expected one httpx import, found {job_search.count(old_import)}")
job_search = job_search.replace(old_import, new_import, 1)

old_defaults = """DEFAULT_GREENHOUSE_BOARDS = (
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
DEFAULT_LEVER_SITES = (
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
"""
new_defaults = """DEFAULT_GREENHOUSE_BOARDS = default_source_identifiers("greenhouse")
DEFAULT_LEVER_SITES = default_source_identifiers("lever")
"""
if job_search.count(old_defaults) != 1:
    raise RuntimeError(f"Expected one default provider block, found {job_search.count(old_defaults)}")
job_search = job_search.replace(old_defaults, new_defaults, 1)

provider_name_pattern = re.compile(
    r"def _provider_company_name\(provider_token: str\) -> str:\n.*?(?=\ndef _normalize_greenhouse_job)",
    re.DOTALL,
)
provider_name_replacement = """def _provider_company_name(provider_token: str) -> str:
    return organization_name(provider_token)

"""
job_search, replacement_count = provider_name_pattern.subn(
    provider_name_replacement,
    job_search,
    count=1,
)
if replacement_count != 1:
    raise RuntimeError(f"Expected one provider company-name function, found {replacement_count}")

job_search_path.write_text(job_search)
registry_path.write_text('''from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Provider = Literal["greenhouse", "lever"]
EarlyCareerRelevance = Literal["general", "strong", "limited", "unknown"]

DEFAULT_COVERAGE_NOTE = (
    "Official public ATS board. Available roles and locations change with the organization\'s current postings."
)


@dataclass(frozen=True)
class JobSourceRegistryEntry:
    provider: Provider
    identifier: str
    organization: str
    industries: tuple[str, ...]
    role_families: tuple[str, ...]
    early_career_relevance: EarlyCareerRelevance
    geographic_focus: tuple[str, ...]
    enabled: bool = True
    coverage_note: str = DEFAULT_COVERAGE_NOTE


TECH_ROLE_FAMILIES = (
    "software",
    "data",
    "cybersecurity",
    "product",
    "design",
    "marketing",
    "operations",
)
FINTECH_ROLE_FAMILIES = TECH_ROLE_FAMILIES + ("finance",)
HEALTH_ROLE_FAMILIES = TECH_ROLE_FAMILIES + ("healthcare",)


def _source(
    provider: Provider,
    identifier: str,
    organization: str,
    industries: tuple[str, ...],
    role_families: tuple[str, ...] = TECH_ROLE_FAMILIES,
    early_career_relevance: EarlyCareerRelevance = "general",
    geographic_focus: tuple[str, ...] = ("varies_by_posting",),
    coverage_note: str | None = None,
) -> JobSourceRegistryEntry:
    return JobSourceRegistryEntry(
        provider=provider,
        identifier=identifier,
        organization=organization,
        industries=industries,
        role_families=role_families,
        early_career_relevance=early_career_relevance,
        geographic_focus=geographic_focus,
        coverage_note=coverage_note or DEFAULT_COVERAGE_NOTE,
    )


SOURCE_REGISTRY: tuple[JobSourceRegistryEntry, ...] = (
    _source("greenhouse", "datadog", "Datadog", ("technology", "data")),
    _source("greenhouse", "airbnb", "Airbnb", ("technology", "travel")),
    _source("greenhouse", "figma", "Figma", ("technology", "design")),
    _source("greenhouse", "duolingo", "Duolingo", ("education", "technology")),
    _source("greenhouse", "roblox", "Roblox", ("entertainment", "gaming", "technology")),
    _source("greenhouse", "scaleai", "Scale AI", ("technology", "artificial_intelligence", "data")),
    _source("greenhouse", "hubspot", "HubSpot", ("technology", "marketing")),
    _source("greenhouse", "cloudflare", "Cloudflare", ("technology", "cybersecurity")),
    _source("greenhouse", "verkada", "Verkada", ("technology", "security")),
    _source("greenhouse", "doordash", "DoorDash", ("technology", "consumer_services")),
    _source("greenhouse", "okta", "Okta", ("technology", "cybersecurity")),
    _source("greenhouse", "mongodb", "MongoDB", ("technology", "data")),
    _source("greenhouse", "asana", "Asana", ("technology", "productivity")),
    _source("greenhouse", "plaid", "Plaid", ("financial_services", "fintech", "technology"), FINTECH_ROLE_FAMILIES),
    _source("greenhouse", "brex", "Brex", ("financial_services", "fintech", "technology"), FINTECH_ROLE_FAMILIES),
    _source("greenhouse", "coinbase", "Coinbase", ("financial_services", "fintech", "technology"), FINTECH_ROLE_FAMILIES),
    _source("greenhouse", "ramp", "Ramp", ("financial_services", "fintech", "technology"), FINTECH_ROLE_FAMILIES),
    _source("greenhouse", "gusto", "Gusto", ("technology", "human_resources")),
    _source("greenhouse", "rippling", "Rippling", ("technology", "human_resources")),
    _source("greenhouse", "affirm", "Affirm", ("financial_services", "fintech", "technology"), FINTECH_ROLE_FAMILIES),
    _source("lever", "github", "GitHub", ("technology", "software")),
    _source("lever", "postman", "Postman", ("technology", "software")),
    _source("lever", "benchling", "Benchling", ("healthcare", "life_sciences", "technology"), HEALTH_ROLE_FAMILIES),
    _source("lever", "box", "Box", ("technology", "cloud")),
    _source("lever", "coursera", "Coursera", ("education", "technology")),
    _source("lever", "lyft", "Lyft", ("technology", "transportation")),
    _source("lever", "pinterest", "Pinterest", ("media", "technology")),
    _source("lever", "reddit", "Reddit", ("media", "technology")),
    _source("lever", "snap", "Snap", ("media", "technology")),
    _source("lever", "twitch", "Twitch", ("entertainment", "media", "gaming", "technology")),
    _source("lever", "zapier", "Zapier", ("technology", "productivity")),
    _source("lever", "affirm", "Affirm", ("financial_services", "fintech", "technology"), FINTECH_ROLE_FAMILIES),
    _source("lever", "robinhood", "Robinhood", ("financial_services", "fintech", "technology"), FINTECH_ROLE_FAMILIES),
    _source("lever", "rippling", "Rippling", ("technology", "human_resources")),
    _source("lever", "webflow", "Webflow", ("technology", "design")),
    _source("lever", "notion", "Notion", ("technology", "productivity")),
    _source("lever", "loom", "Loom", ("technology", "media", "productivity")),
    _source("lever", "intercom", "Intercom", ("technology", "customer_experience")),
    _source("lever", "mixpanel", "Mixpanel", ("technology", "data")),
    _source("lever", "fivetran", "Fivetran", ("technology", "data")),
    _source("lever", "algolia", "Algolia", ("technology", "search")),
    _source("lever", "addepar", "Addepar", ("financial_services", "fintech", "technology"), FINTECH_ROLE_FAMILIES),
)


def source_registry_entries(
    provider: Provider | None = None,
    *,
    enabled_only: bool = True,
) -> tuple[JobSourceRegistryEntry, ...]:
    return tuple(
        entry
        for entry in SOURCE_REGISTRY
        if (provider is None or entry.provider == provider)
        and (entry.enabled or not enabled_only)
    )


def default_source_identifiers(provider: Provider) -> tuple[str, ...]:
    return tuple(entry.identifier for entry in source_registry_entries(provider))


def find_source(
    identifier: str,
    provider: Provider | None = None,
) -> JobSourceRegistryEntry | None:
    normalized_identifier = identifier.strip().lower()
    for entry in SOURCE_REGISTRY:
        if entry.identifier == normalized_identifier and (
            provider is None or entry.provider == provider
        ):
            return entry
    return None


def organization_name(identifier: str, provider: Provider | None = None) -> str:
    entry = find_source(identifier, provider)
    if entry is not None:
        return entry.organization
    return identifier.replace("-", " ").replace("_", " ").title()
''')
test_path.write_text('''from app.job_search import (
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
''')
docs_path.write_text('''# Milestone 7 — Source Registry

MarketLens now has a centralized registry for its configured public Greenhouse and Lever organization boards.

## Registry fields

Each source records:

- provider type and ATS identifier
- display organization name
- likely industries
- likely job-function families
- early-career relevance
- geographic focus
- enabled status
- an honest coverage note

## Current behavior

The existing default Greenhouse and Lever token lists now come from the registry, preserving the exact search order and current source behavior. Company display names also resolve through the same registry, with a safe title-cased fallback for environment-configured sources that are not registered yet.

This phase does **not** route searches differently yet. It establishes the structured configuration needed for the next phase: choosing source groups based on job function, industry, experience level, and location.

## Why this matters

Before this change, provider tokens and company-name formatting were hardcoded inside the search implementation. Expanding coverage would have required adding more one-off constants. The registry makes future source expansion reviewable, testable, and explainable without coupling every organization to the provider-fetching code.
''')
