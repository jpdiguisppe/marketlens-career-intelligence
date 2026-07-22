from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

Provider = Literal["greenhouse", "lever"]
EarlyCareerRelevance = Literal["general", "strong", "limited", "unknown"]

DEFAULT_COVERAGE_NOTE = (
    "Official public ATS board. Available roles and locations change with the organization's current postings."
)
SOURCE_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def normalize_source_identifier(identifier: str) -> str | None:
    normalized = identifier.strip().lower()
    if not SOURCE_IDENTIFIER_PATTERN.fullmatch(normalized):
        return None
    return normalized


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
    normalized_identifier = normalize_source_identifier(identifier)
    if normalized_identifier is None:
        raise ValueError(f"Invalid {provider} source identifier: {identifier!r}")

    return JobSourceRegistryEntry(
        provider=provider,
        identifier=normalized_identifier,
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
    normalized_identifier = normalize_source_identifier(identifier)
    if normalized_identifier is None:
        return None

    for entry in SOURCE_REGISTRY:
        if entry.identifier == normalized_identifier and (
            provider is None or entry.provider == provider
        ):
            return entry
    return None


def configured_source_identifiers(
    provider: Provider,
    raw_identifiers: str | None,
) -> tuple[str, ...]:
    """Resolve environment configuration through the registry allowlist.

    Invalid, disabled, duplicate, and unregistered identifiers are ignored.
    An empty or fully rejected configuration safely falls back to the enabled
    registry defaults rather than creating arbitrary outbound request targets.
    """

    defaults = default_source_identifiers(provider)
    if not raw_identifiers:
        return defaults

    selected: list[str] = []
    for raw_identifier in raw_identifiers.split(","):
        normalized = normalize_source_identifier(raw_identifier)
        if normalized is None or normalized in selected:
            continue
        entry = find_source(normalized, provider)
        if entry is not None and entry.enabled:
            selected.append(normalized)

    return tuple(selected) or defaults


def organization_name(identifier: str, provider: Provider | None = None) -> str:
    entry = find_source(identifier, provider)
    if entry is not None:
        return entry.organization
    return identifier.replace("-", " ").replace("_", " ").title()
