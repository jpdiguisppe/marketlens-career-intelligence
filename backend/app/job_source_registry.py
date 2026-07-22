from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Provider = Literal["greenhouse", "lever"]
EarlyCareerRelevance = Literal["general", "strong", "limited", "unknown"]

DEFAULT_COVERAGE_NOTE = (
    "Official public ATS board. Available roles and locations change with the organization's current postings."
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
