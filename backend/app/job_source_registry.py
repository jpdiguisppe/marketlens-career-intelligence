from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

Provider = Literal["greenhouse", "lever"]
SourcePool = Literal["primary", "industry_only"]
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
    source_pool: SourcePool = "primary"
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
MISSION_ROLE_FAMILIES = (
    "data",
    "product",
    "design",
    "marketing",
    "operations",
)
ENTERTAINMENT_ROLE_FAMILIES = (
    "data",
    "product",
    "design",
    "marketing",
    "operations",
)
LEGAL_ROLE_FAMILIES = (
    "legal",
    "compliance",
    "policy",
    "legal_operations",
    "contracts",
    "operations",
    "marketing",
    "data",
)
HEALTH_POLICY_ROLE_FAMILIES = HEALTH_ROLE_FAMILIES + (
    "legal",
    "compliance",
    "policy",
    "contracts",
)
MEDIA_POLICY_ROLE_FAMILIES = ENTERTAINMENT_ROLE_FAMILIES + (
    "software",
    "legal",
    "compliance",
    "policy",
    "legal_operations",
    "contracts",
)
EDUCATION_ROLE_FAMILIES = TECH_ROLE_FAMILIES + ("policy",)
MISSION_POLICY_ROLE_FAMILIES = MISSION_ROLE_FAMILIES + (
    "legal",
    "compliance",
    "policy",
)


def _source(
    provider: Provider,
    identifier: str,
    organization: str,
    industries: tuple[str, ...],
    role_families: tuple[str, ...] = TECH_ROLE_FAMILIES,
    early_career_relevance: EarlyCareerRelevance = "general",
    geographic_focus: tuple[str, ...] = ("varies_by_posting",),
    source_pool: SourcePool = "primary",
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
        source_pool=source_pool,
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
    _source(
        "greenhouse",
        "aclu",
        "ACLU",
        ("legal_services", "public_interest", "nonprofit", "government", "public_policy"),
        LEGAL_ROLE_FAMILIES,
        geographic_focus=("united_states", "varies_by_posting"),
        source_pool="industry_only",
        coverage_note="Official public Greenhouse board for national civil-liberties, legal, policy, and advocacy roles.",
    ),
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
    _source(
        "lever",
        "avalerehealth",
        "Avalere Health",
        ("healthcare", "life_sciences", "public_policy", "government"),
        HEALTH_POLICY_ROLE_FAMILIES,
        geographic_focus=("united_states", "remote", "varies_by_posting"),
        source_pool="industry_only",
        coverage_note="Official public Lever board spanning healthcare policy, advisory, medical, marketing, and operations roles.",
    ),
    _source(
        "lever",
        "wattpad",
        "WEBTOON / Wattpad",
        ("media", "entertainment", "publishing", "corporate_legal"),
        MEDIA_POLICY_ROLE_FAMILIES,
        early_career_relevance="strong",
        geographic_focus=("united_states", "varies_by_posting"),
        source_pool="industry_only",
        coverage_note="Official public Lever board with media, content-policy, legal-business, and internship roles.",
    ),
    _source(
        "lever",
        "thedispatch",
        "The Dispatch",
        ("media", "journalism", "public_policy", "legal_services"),
        ("policy", "legal", "marketing", "operations", "design"),
        early_career_relevance="strong",
        geographic_focus=("united_states", "remote", "varies_by_posting"),
        source_pool="industry_only",
        coverage_note="Official public Lever board for journalism, policy-adjacent media, and recurring internship roles.",
    ),
    _source(
        "lever",
        "kiddom",
        "Kiddom",
        ("education", "technology"),
        EDUCATION_ROLE_FAMILIES,
        geographic_focus=("united_states", "remote", "varies_by_posting"),
        source_pool="industry_only",
        coverage_note="Official public Lever board for K-12 education technology, curriculum, product, and operations roles.",
    ),
    _source(
        "lever",
        "stradaeducation",
        "Strada Education Foundation",
        ("education", "nonprofit", "public_interest", "public_policy", "social_impact"),
        MISSION_POLICY_ROLE_FAMILIES,
        early_career_relevance="strong",
        geographic_focus=("united_states", "varies_by_posting"),
        source_pool="industry_only",
        coverage_note="Official public Lever board for education, workforce policy, nonprofit, internship, and co-op pathways.",
    ),
    _source(
        "lever",
        "theathletic",
        "The Athletic",
        ("sports", "media", "entertainment"),
        TECH_ROLE_FAMILIES,
        source_pool="industry_only",
        coverage_note="Official public Lever board for a sports-media organization.",
    ),
    _source(
        "lever",
        "feldinc",
        "Feld Entertainment",
        ("sports", "entertainment", "media", "events"),
        ENTERTAINMENT_ROLE_FAMILIES,
        source_pool="industry_only",
        coverage_note="Official public Lever board covering live entertainment and motorsports operations.",
    ),
    _source(
        "lever",
        "standtogether",
        "Stand Together",
        ("nonprofit", "education", "social_impact", "media"),
        MISSION_ROLE_FAMILIES,
        early_career_relevance="strong",
        source_pool="industry_only",
        coverage_note="Official public Lever board with mission-driven roles and fellowship pathways.",
    ),
)


def source_registry_entries(
    provider: Provider | None = None,
    *,
    enabled_only: bool = True,
    source_pool: SourcePool | None = None,
) -> tuple[JobSourceRegistryEntry, ...]:
    return tuple(
        entry
        for entry in SOURCE_REGISTRY
        if (provider is None or entry.provider == provider)
        and (entry.enabled or not enabled_only)
        and (source_pool is None or entry.source_pool == source_pool)
    )


def default_source_identifiers(provider: Provider) -> tuple[str, ...]:
    """Return primary sources used by broad searches."""
    return tuple(
        entry.identifier
        for entry in source_registry_entries(provider, source_pool="primary")
    )


def industry_source_identifiers(provider: Provider) -> tuple[str, ...]:
    """Return secondary sources activated only for matching industries."""
    return tuple(
        entry.identifier
        for entry in source_registry_entries(provider, source_pool="industry_only")
    )


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
    *,
    source_pool: SourcePool = "primary",
) -> tuple[str, ...]:
    """Resolve environment configuration through the registry allowlist.

    Invalid, disabled, duplicate, unregistered, and wrong-pool identifiers are
    ignored. An empty or fully rejected configuration safely falls back to the
    enabled defaults for the requested pool.
    """

    defaults = tuple(
        entry.identifier
        for entry in source_registry_entries(provider, source_pool=source_pool)
    )
    if not raw_identifiers:
        return defaults

    selected: list[str] = []
    for raw_identifier in raw_identifiers.split(","):
        normalized = normalize_source_identifier(raw_identifier)
        if normalized is None or normalized in selected:
            continue
        entry = find_source(normalized, provider)
        if (
            entry is not None
            and entry.enabled
            and entry.source_pool == source_pool
        ):
            selected.append(normalized)

    return tuple(selected) or defaults


def organization_name(identifier: str, provider: Provider | None = None) -> str:
    entry = find_source(identifier, provider)
    if entry is not None:
        return entry.organization
    return identifier.replace("-", " ").replace("_", " ").title()
