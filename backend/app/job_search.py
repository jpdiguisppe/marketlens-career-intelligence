import os
import re
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from html import unescape
from typing import Any, Literal
from urllib.parse import quote_plus

import httpx

from app.external_urls import sanitize_external_https_url
from app.job_source_registry import (
    configured_source_identifiers,
    default_source_identifiers,
    organization_name,
)
from app.job_source_routing import build_source_routing_plan

GREENHOUSE_BASE_URL = "https://boards-api.greenhouse.io/v1/boards"
LEVER_BASE_URL = "https://api.lever.co/v0/postings"
REMOTEOK_BASE_URL = "https://remoteok.com/api"
REMOTIVE_BASE_URL = "https://remotive.com/api/remote-jobs"

DEFAULT_GREENHOUSE_BOARDS = default_source_identifiers("greenhouse")
DEFAULT_LEVER_SITES = default_source_identifiers("lever")
MAX_PROVIDER_RESULTS_PER_BOARD = 100
REMOTEOK_CACHE_SECONDS = 15 * 60
REMOTIVE_CACHE_SECONDS = 6 * 60 * 60
DEFAULT_PROVIDER_CACHE_SECONDS = 5 * 60
DEFAULT_MAX_PROVIDER_REQUESTS_PER_SEARCH = 48
MIN_PROVIDER_REQUESTS_PER_SEARCH = 4
MAX_PROVIDER_REQUESTS_PER_SEARCH = 50

JobLevel = Literal["any", "intern", "entry", "mid", "senior"]
VALID_JOB_LEVELS: set[str] = {"any", "intern", "entry", "mid", "senior"}
RoleFamily = Literal[
    "technology",
    "software",
    "finance",
    "data",
    "cybersecurity",
    "product",
    "marketing",
    "operations",
    "healthcare",
    "design",
    "legal",
    "compliance",
    "policy",
    "legal_operations",
    "contracts",
]
Industry = Literal[
    "sports",
    "entertainment",
    "healthcare",
    "financial_services",
    "education",
    "nonprofit",
    "media",
    "legal_services",
    "government",
    "public_interest",
    "corporate_legal",
    "public_policy",
]

EXPERIENCE_YEARS_PATTERN = re.compile(r"\b(\d{1,2})\s*\+?\s*(?:years?|yrs?)\b", re.IGNORECASE)
MID_LEVEL_TITLE_PATTERN = re.compile(
    r"\b(?:software\s+)?(?:engineer|developer|analyst|accountant|specialist)\s+(?:ii|iii|2|3)\b",
    re.IGNORECASE,
)
SENIOR_NUMBERED_TITLE_PATTERN = re.compile(
    r"\b(?:software\s+)?(?:engineer|developer|analyst|accountant|specialist)\s+(?:iv|v|4|5)\b",
    re.IGNORECASE,
)
ENTRY_NUMBERED_TITLE_PATTERN = re.compile(
    r"\b(?:software\s+)?(?:engineer|developer|analyst|accountant|specialist)\s+(?:i|1)\b",
    re.IGNORECASE,
)
SOFTWARE_ENGINEER_I_PATTERN = ENTRY_NUMBERED_TITLE_PATTERN

NON_US_LOCATION_TERMS = {
    "australia",
    "beijing",
    "brazil",
    "canada",
    "china",
    "denmark",
    "europe",
    "france",
    "germany",
    "india",
    "ireland",
    "japan",
    "lisbon",
    "london",
    "mexico",
    "norway",
    "portugal",
    "singapore",
    "spain",
    "sweden",
    "united kingdom",
    "uk",
}
US_LOCATION_TERMS = {
    "united states",
    "u.s.",
    "usa",
    "us",
    "us remote",
    "remote us",
    "remote - us",
    "remote-us",
    "atlanta",
    "austin",
    "boston",
    "chicago",
    "colorado",
    "dc",
    "denver",
    "los angeles",
    "new york",
    "palo alto",
    "philadelphia",
    "pittsburgh",
    "san francisco",
    "san jose",
    "santa clara",
    "seattle",
    "st. louis",
    "washington",
    "washington, dc",
    "washington, d.c.",
}
LOCATION_ALIASES: dict[str, set[str]] = {
    "philadelphia": {"philadelphia", "philly"},
    "philly": {"philadelphia", "philly"},
    "pittsburgh": {"pittsburgh"},
    "pennsylvania": {"pennsylvania", "pa", "philadelphia", "pittsburgh"},
    "pa": {"pennsylvania", "pa", "philadelphia", "pittsburgh"},
    "new york": {"new york", "nyc", "new york city", "ny"},
    "new york city": {"new york", "nyc", "new york city", "ny"},
    "nyc": {"new york", "nyc", "new york city", "ny"},
    "ny": {"new york", "nyc", "new york city", "ny"},
    "washington dc": {"washington", "washington dc", "washington, dc", "dc", "d.c."},
    "washington, dc": {"washington", "washington dc", "washington, dc", "dc", "d.c."},
    "dc": {"washington", "washington dc", "washington, dc", "dc", "d.c."},
    "san francisco": {"san francisco", "sf"},
    "sf": {"san francisco", "sf"},
    "bay area": {"san francisco", "sf", "bay area", "palo alto", "san jose", "santa clara"},
    "seattle": {"seattle"},
    "boston": {"boston"},
    "chicago": {"chicago"},
    "austin": {"austin"},
    "denver": {"denver"},
}

NON_SOFTWARE_TITLE_TERMS = {
    "account executive",
    "business development",
    "customer success",
    "developer advocate",
    "developer relations",
    "marketing",
    "recruiter",
    "sales",
    "salesforce",
}
SOFTWARE_TITLE_TERMS = {
    "software engineer",
    "software engineering",
    "software developer",
    "backend engineer",
    "backend developer",
    "back-end engineer",
    "back-end developer",
    "frontend engineer",
    "frontend developer",
    "front-end engineer",
    "front-end developer",
    "full stack engineer",
    "full stack developer",
    "full-stack engineer",
    "full-stack developer",
    "web developer",
    "application developer",
    "app developer",
    "python developer",
    "java developer",
    "javascript developer",
    "typescript developer",
    "react developer",
    "node developer",
    "mobile engineer",
    "mobile developer",
    "ios engineer",
    "ios developer",
    "android engineer",
    "android developer",
    "platform engineer",
    "infrastructure engineer",
    "devops engineer",
    "programmer",
    "developer",
    "forward deployed software engineer",
}
FINANCE_TITLE_TERMS = {
    "finance",
    "financial",
    "fp&a",
    "fpa",
    "accounting",
    "accountant",
    "audit",
    "auditor",
    "tax",
    "treasury",
    "investment",
    "investment banking",
    "banking",
    "private equity",
    "equity research",
    "valuation",
    "wealth",
    "risk analyst",
    "credit analyst",
    "financial analyst",
    "finance analyst",
    "business analyst",
    "quantitative analyst",
    "portfolio analyst",
    "corporate finance",
    "summer analyst",
    "analyst intern",
    "rotational finance",
}
DATA_TITLE_TERMS = {
    "analytics engineer",
    "data analyst",
    "data scientist",
    "data engineer",
    "analytics",
    "business intelligence",
    "bi analyst",
    "machine learning",
    "ml engineer",
    "research analyst",
    "reporting analyst",
}
CYBERSECURITY_TITLE_TERMS = {
    "cybersecurity",
    "cyber security",
    "security analyst",
    "soc analyst",
    "information security",
    "infosec",
    "security engineer",
    "threat analyst",
}
PRODUCT_TITLE_TERMS = {
    "product manager",
    "product analyst",
    "product owner",
    "program manager",
    "project manager",
    "scrum master",
}
MARKETING_TITLE_TERMS = {
    "marketing",
    "growth",
    "content marketing",
    "seo",
    "social media",
    "brand",
    "communications",
    "media",
    "digital media",
    "partnership",
    "partnerships",
    "sponsorship",
    "fan engagement",
}
OPERATIONS_TITLE_TERMS = {
    "operations",
    "business operations",
    "strategy",
    "supply chain",
    "logistics",
    "procurement",
    "customer success",
    "human resources",
    "hr intern",
}
HEALTHCARE_TITLE_TERMS = {
    "healthcare",
    "health care",
    "clinical",
    "patient",
    "medical",
    "hospital",
    "health analyst",
}
DESIGN_TITLE_TERMS = {
    "designer",
    "product designer",
    "ux",
    "ui designer",
    "visual designer",
    "graphic designer",
}
LEGAL_TITLE_TERMS = {
    "legal intern",
    "legal assistant",
    "legal analyst",
    "legal coordinator",
    "paralegal",
    "law clerk",
    "attorney",
    "counsel",
    "litigation",
}
COMPLIANCE_TITLE_TERMS = {
    "compliance",
    "regulatory",
    "risk and compliance",
    "aml",
    "kyc",
    "ethics",
}
POLICY_TITLE_TERMS = {
    "policy analyst",
    "policy associate",
    "policy intern",
    "public policy",
    "government affairs",
    "public affairs",
    "legislative",
    "advocacy",
}
LEGAL_OPERATIONS_TITLE_TERMS = {
    "legal operations",
    "legal ops",
    "litigation support",
    "legal project manager",
    "legal technology",
    "e-billing",
}
CONTRACTS_TITLE_TERMS = {
    "contracts analyst",
    "contract analyst",
    "contracts specialist",
    "contract specialist",
    "contract administrator",
    "commercial contracts",
}
TECHNOLOGY_TITLE_TERMS = SOFTWARE_TITLE_TERMS | DATA_TITLE_TERMS | CYBERSECURITY_TITLE_TERMS
ROLE_FAMILY_TITLE_TERMS: dict[RoleFamily, set[str]] = {
    "technology": TECHNOLOGY_TITLE_TERMS,
    "software": SOFTWARE_TITLE_TERMS,
    "finance": FINANCE_TITLE_TERMS,
    "data": DATA_TITLE_TERMS,
    "cybersecurity": CYBERSECURITY_TITLE_TERMS,
    "product": PRODUCT_TITLE_TERMS,
    "marketing": MARKETING_TITLE_TERMS,
    "operations": OPERATIONS_TITLE_TERMS,
    "healthcare": HEALTHCARE_TITLE_TERMS,
    "design": DESIGN_TITLE_TERMS,
    "legal": LEGAL_TITLE_TERMS,
    "compliance": COMPLIANCE_TITLE_TERMS,
    "policy": POLICY_TITLE_TERMS,
    "legal_operations": LEGAL_OPERATIONS_TITLE_TERMS,
    "contracts": CONTRACTS_TITLE_TERMS,
}
ROLE_FAMILY_QUERY_TERMS: dict[RoleFamily, set[str]] = {
    "technology": {"computer science", "cs jobs", "tech jobs", "technology", "technical roles"},
    "software": {"swe", "software", "software engineer", "software developer", "backend", "frontend", "front end", "back end", "full stack", "programmer"},
    "finance": {"finance", "financial", "accounting", "accountant", "audit", "tax", "fp&a", "fpa", "investment", "banking", "equity", "valuation", "treasury", "wealth", "portfolio", "credit"},
    "data": {"data", "analytics", "analytics engineer", "business intelligence", "bi", "data analyst", "data scientist", "data engineer", "machine learning", "ml", "reporting"},
    "cybersecurity": {"cybersecurity", "cyber security", "security analyst", "soc", "infosec", "information security"},
    "product": {"product manager", "product management", "product analyst", "project manager", "program manager", "scrum"},
    "marketing": {"marketing", "growth", "seo", "social media", "brand", "communications", "media", "digital media", "partnership", "partnerships", "sponsorship", "fan engagement"},
    "operations": {"operations", "strategy", "supply chain", "logistics", "procurement", "human resources", "hr"},
    "healthcare": {"healthcare", "health care", "clinical", "patient", "medical", "hospital"},
    "design": {"design", "designer", "ux", "ui", "visual design", "graphic design"},
    "legal": {"legal", "law", "paralegal", "attorney", "counsel", "litigation", "law clerk"},
    "compliance": {"compliance", "regulatory", "regulatory affairs", "aml", "kyc", "ethics", "risk and compliance"},
    "policy": {"policy", "public policy", "government affairs", "public affairs", "legislative", "advocacy"},
    "legal_operations": {"legal operations", "legal ops", "litigation support", "legal technology"},
    "contracts": {"contracts", "contract analyst", "contracts analyst", "contract specialist", "contract administrator"},
}
INDUSTRY_QUERY_TERMS: dict[Industry, set[str]] = {
    "sports": {"sport", "sports", "athletic", "athletics", "esports", "e-sports"},
    "entertainment": {"entertainment", "film", "television", "tv", "music", "streaming", "gaming"},
    "healthcare": {"healthcare", "health care", "hospital", "medical", "clinical", "patient care"},
    "financial_services": {"finance", "financial services", "banking", "fintech", "insurance", "investment"},
    "education": {"education", "edtech", "university", "college", "school", "academic"},
    "nonprofit": {"nonprofit", "non-profit", "charity", "foundation", "social impact"},
    "media": {"media", "journalism", "publishing", "news", "broadcast", "broadcasting"},
    "public_interest": {"public interest", "civil liberties", "civil rights", "legal aid"},
    "government": {"government", "public sector", "federal government", "state government", "municipal"},
    "corporate_legal": {"corporate legal", "in-house legal", "in house legal", "legal department"},
    "public_policy": {"public policy", "policy research", "regulatory policy"},
    "legal_services": {"legal", "law firm", "law office", "litigation", "paralegal", "attorney"},
}
CROSS_INDUSTRY_FUNCTION_QUERY_TERMS: dict[RoleFamily, set[str]] = {
    "legal_operations": ROLE_FAMILY_QUERY_TERMS["legal_operations"],
    "contracts": ROLE_FAMILY_QUERY_TERMS["contracts"],
    "compliance": ROLE_FAMILY_QUERY_TERMS["compliance"],
    "policy": ROLE_FAMILY_QUERY_TERMS["policy"],
    "legal": ROLE_FAMILY_QUERY_TERMS["legal"],
    "software": ROLE_FAMILY_QUERY_TERMS["software"],
    "data": ROLE_FAMILY_QUERY_TERMS["data"],
    "cybersecurity": ROLE_FAMILY_QUERY_TERMS["cybersecurity"],
    "product": ROLE_FAMILY_QUERY_TERMS["product"],
    "marketing": ROLE_FAMILY_QUERY_TERMS["marketing"],
    "operations": ROLE_FAMILY_QUERY_TERMS["operations"],
    "design": ROLE_FAMILY_QUERY_TERMS["design"],
}
SPORTS_QUERY_TERMS = INDUSTRY_QUERY_TERMS["sports"]
SPORTS_TITLE_OR_COMPANY_TERMS = {
    "sport",
    "sports",
    "athletic",
    "athletics",
    "esports",
    "e-sports",
    "sportsbook",
    "sports media",
    "major league",
    "minor league",
    "football club",
    "soccer club",
    "basketball club",
    "baseball club",
    "hockey club",
}
SPORTS_DESCRIPTION_STRONG_PHRASES = {
    "sports organization",
    "sports organisation",
    "professional sports organization",
    "professional sports organisation",
    "professional sports team",
    "professional sports league",
    "sports team",
    "sports league",
    "sports club",
    "athletic department",
    "athletics program",
    "collegiate athletics",
    "college athletics",
    "sports media company",
    "sports network",
    "sports broadcaster",
    "sports marketing agency",
    "sports agency",
    "stadium operations",
    "arena operations",
}
SPORTS_DESCRIPTION_ANCHOR_TERMS = {
    "sport",
    "sports",
    "athletic",
    "athletics",
    "esports",
    "e-sports",
}
SPORTS_DESCRIPTION_SIGNAL_GROUPS = (
    {"fan engagement", "fan experience", "fan growth", "fan base"},
    {"game day", "gameday", "match day", "matchday"},
    {"ticket sales", "ticketing", "season tickets"},
    {"stadium", "arena", "ballpark", "venue operations"},
    {"athlete", "athletes", "player relations", "player marketing"},
    {"sports media", "sports broadcast", "sports broadcasting", "live sports"},
    {"sponsorship activation", "sports partnerships", "partnership activation"},
)

LEVEL_QUERY_TERMS = {
    "intern",
    "internship",
    "co-op",
    "coop",
    "co",
    "op",
    "entry",
    "level",
    "junior",
    "associate",
    "new",
    "grad",
    "graduate",
    "senior",
    "staff",
    "principal",
    "lead",
    "mid",
}
GENERIC_SOFTWARE_QUERY_TERMS = {"engineer", "engineering", "developer", "development"}
INTERN_TERMS = {"intern", "internship", "co-op", "coop", "co op"}
ENTRY_TITLE_TERMS = {
    "entry level",
    "entry-level",
    "junior",
    "associate",
    "new grad",
    "new graduate",
    "university grad",
    "university graduate",
    "early career",
}
ENTRY_DESCRIPTION_TERMS = {
    "entry level",
    "entry-level",
    "junior engineer",
    "junior developer",
    "junior analyst",
    "junior accountant",
    "new grad",
    "new graduate",
    "university grad",
    "university graduate",
    "early career",
}
MID_TERMS = {
    "mid level",
    "mid-level",
    "software engineer ii",
    "software engineer iii",
    "software developer ii",
    "software developer iii",
    "engineer ii",
    "engineer iii",
    "developer ii",
    "developer iii",
    "analyst ii",
    "analyst iii",
    "accountant ii",
    "accountant iii",
}
SENIOR_TERMS = {
    "principal",
    "staff",
    "senior",
    "sr.",
    "sr",
    "lead",
    "manager",
    "director",
    "architect",
}

_REMOTEOK_CACHE: dict[str, Any] = {"expires_at": 0.0, "jobs": []}
_REMOTIVE_CACHE: dict[str, dict[str, Any]] = {}
_ATS_PROVIDER_CACHE: dict[str, dict[str, Any]] = {}


class ProviderRequestBudgetExceeded(RuntimeError):
    pass


@dataclass
class _ProviderRequestBudget:
    remaining: int
    consumed: int = 0

    def consume(self) -> None:
        if self.remaining <= 0:
            raise ProviderRequestBudgetExceeded("Provider request budget exhausted.")
        self.remaining -= 1
        self.consumed += 1


_ACTIVE_PROVIDER_REQUEST_BUDGET: ContextVar[_ProviderRequestBudget | None] = ContextVar(
    "marketlens_provider_request_budget",
    default=None,
)


@dataclass(frozen=True)
class JobSearchIntent:
    query: str
    job_function: RoleFamily | None
    industry: Industry | None
    level: JobLevel
    location: str | None


@dataclass(frozen=True)
class ExternalJobResult:
    id: str
    source: str
    company: str
    title: str
    location: str | None
    description: str
    apply_url: str
    updated_at: str | None = None


@dataclass(frozen=True)
class SourceCoverageSummary:
    provider: str
    label: str
    status: str
    fetched_count: int
    matched_count: int
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExternalSearchLink:
    label: str
    url: str
    note: str


@dataclass(frozen=True)
class JobSearchResults:
    query: str
    location: str | None
    level: JobLevel
    providers_searched: list[str]
    results: list[ExternalJobResult]
    warnings: list[str]
    role_family: str | None = None
    industry: str | None = None
    source_coverage: list[SourceCoverageSummary] = field(default_factory=list)
    search_suggestions: list[str] = field(default_factory=list)
    external_search_links: list[ExternalSearchLink] = field(default_factory=list)


@dataclass(frozen=True)
class _ProviderOutcome:
    provider: str
    label: str
    fetched_count: int
    scored_jobs: list[tuple[int, ExternalJobResult]]
    status: str = "searched"
    notes: list[str] = field(default_factory=list)

    @property
    def matched_count(self) -> int:
        return len(self.scored_jobs)


def _configured_greenhouse_boards() -> list[str]:
    return list(
        configured_source_identifiers(
            "greenhouse",
            os.getenv("JOB_SEARCH_GREENHOUSE_BOARDS"),
        )
    )


def _configured_lever_sites() -> list[str]:
    return list(
        configured_source_identifiers(
            "lever",
            os.getenv("JOB_SEARCH_LEVER_SITES"),
        )
    )


def _remoteok_enabled() -> bool:
    return os.getenv("JOB_SEARCH_REMOTEOK_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}


def _remotive_enabled() -> bool:
    return os.getenv("JOB_SEARCH_REMOTIVE_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}




def _bounded_env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        parsed = int(raw_value)
    except ValueError:
        return default
    return max(minimum, min(parsed, maximum))


def _provider_request_limit() -> int:
    return _bounded_env_int(
        "JOB_SEARCH_MAX_PROVIDER_REQUESTS",
        DEFAULT_MAX_PROVIDER_REQUESTS_PER_SEARCH,
        MIN_PROVIDER_REQUESTS_PER_SEARCH,
        MAX_PROVIDER_REQUESTS_PER_SEARCH,
    )


def _provider_cache_seconds() -> int:
    return _bounded_env_int(
        "JOB_SEARCH_PROVIDER_CACHE_SECONDS",
        DEFAULT_PROVIDER_CACHE_SECONDS,
        60,
        3_600,
    )


def _consume_provider_request() -> None:
    budget = _ACTIVE_PROVIDER_REQUEST_BUDGET.get()
    if budget is not None:
        budget.consume()


def _cached_ats_jobs(cache_key: str) -> list[dict[str, Any]] | None:
    cached = _ATS_PROVIDER_CACHE.get(cache_key)
    if not cached or time.monotonic() >= float(cached.get("expires_at", 0.0)):
        return None
    jobs = cached.get("jobs")
    if not isinstance(jobs, list):
        return None
    return jobs


def _store_ats_jobs(cache_key: str, jobs: list[dict[str, Any]]) -> None:
    _ATS_PROVIDER_CACHE[cache_key] = {
        "expires_at": time.monotonic() + _provider_cache_seconds(),
        "jobs": jobs,
    }


def _build_provider_client() -> httpx.Client:
    # Provider APIs are already HTTPS. Do not follow an unexpected redirect to
    # a different host; a 3xx response is treated as a failed provider request.
    return httpx.Client(timeout=8.0, follow_redirects=False)


def clean_job_description(value: str | None) -> str:
    """Turn provider HTML into plain text that is safe to display and analyze."""
    if not value:
        return ""

    decoded = unescape(value)
    no_scripts = re.sub(
        r"<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>",
        " ",
        decoded,
        flags=re.IGNORECASE,
    )
    no_styles = re.sub(
        r"<style\b[^<]*(?:(?!</style>)<[^<]*)*</style>",
        " ",
        no_scripts,
        flags=re.IGNORECASE,
    )
    with_section_spacing = re.sub(
        r"</?(p|div|li|ul|ol|br|h[1-6])\b[^>]*>",
        " ",
        no_styles,
        flags=re.IGNORECASE,
    )
    no_tags = re.sub(r"<[^>]+>", " ", with_section_spacing)
    cleaned = unescape(no_tags)
    return re.sub(r"\s+", " ", cleaned).strip()


def _query_terms(query: str) -> list[str]:
    normalized = query.lower().strip()
    expansions = {
        "swe": ["software", "engineer", "developer"],
        "computer science": ["software", "data", "cybersecurity", "analytics"],
        "software engineering": ["software", "engineer"],
        "backend": ["backend"],
        "back end": ["backend"],
        "front end": ["frontend"],
        "full stack": ["full", "stack"],
        "ml": ["machine", "learning"],
        "ai": ["ai"],
        "fp&a": ["finance", "financial"],
        "fpa": ["finance", "financial"],
        "intern": ["intern"],
        "internship": ["intern"],
        "entry level": ["entry", "level"],
        "entry-level": ["entry", "level"],
        "new grad": ["new", "grad"],
    }

    terms = re.findall(r"[a-z0-9+#&.]+", normalized)
    for phrase, extra_terms in expansions.items():
        if phrase in normalized:
            terms.extend(extra_terms)

    return sorted(set(term for term in terms if len(term) > 1))


def _core_query_terms(query: str) -> set[str]:
    return {term for term in _query_terms(query) if term not in LEVEL_QUERY_TERMS}


def _contains_phrase(value: str, phrase: str) -> bool:
    """Match whole words/phrases, so 'intern' does not match 'internal'."""
    cleaned_phrase = phrase.strip().lower()
    if not cleaned_phrase:
        return False

    escaped_words = [re.escape(part) for part in re.split(r"[\s,./()\-]+", cleaned_phrase) if part]
    if not escaped_words:
        return False

    separator = r"[\s,./()\-]+"
    pattern = r"(?<![a-z0-9])" + separator.join(escaped_words) + r"(?![a-z0-9])"
    return bool(re.search(pattern, value.lower()))


def _contains_any(value: str, terms: set[str]) -> bool:
    return any(_contains_phrase(value, term) for term in terms)


def _normalize_location_text(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"\s+", " ", value)
    return value.replace(",", "")


def _normalize_level(level: str | None) -> JobLevel | None:
    if level is None or not level.strip():
        return None

    normalized = level.strip().lower()
    if normalized not in VALID_JOB_LEVELS:
        raise ValueError(f"Unsupported job level '{level}'. Expected one of: any, intern, entry, mid, senior.")

    return normalized  # type: ignore[return-value]


def _infer_level_from_query(query: str) -> JobLevel:
    normalized = query.lower()
    if _contains_any(normalized, INTERN_TERMS):
        return "intern"
    if _contains_any(normalized, ENTRY_TITLE_TERMS):
        return "entry"
    if _contains_any(normalized, SENIOR_TERMS) or SENIOR_NUMBERED_TITLE_PATTERN.search(normalized):
        return "senior"
    if _contains_any(normalized, MID_TERMS) or MID_LEVEL_TITLE_PATTERN.search(normalized):
        return "mid"
    return "any"


def resolve_job_level(query: str, level: str | None = None) -> JobLevel:
    normalized_level = _normalize_level(level)
    inferred_level = _infer_level_from_query(query)

    if normalized_level and normalized_level != "any":
        return normalized_level

    if inferred_level != "any":
        return inferred_level

    return normalized_level or "any"


def _query_role_family(query: str) -> RoleFamily | None:
    normalized = query.lower()
    for family, terms in ROLE_FAMILY_QUERY_TERMS.items():
        if _contains_any(normalized, terms):
            return family
    return None


def _query_job_function(query: str) -> RoleFamily | None:
    normalized = query.lower()

    # Keep job function independent from industry classification. This helper
    # is deliberately separate from _query_role_family because the application
    # bootstrap wraps that legacy function with compatibility behavior.
    for family, terms in CROSS_INDUSTRY_FUNCTION_QUERY_TERMS.items():
        if _contains_any(normalized, terms):
            return family
    return _query_role_family(query)


def _query_industry(query: str) -> Industry | None:
    normalized = query.lower()
    for industry, terms in INDUSTRY_QUERY_TERMS.items():
        if _contains_any(normalized, terms):
            return industry
    return None


def parse_job_search_intent(
    query: str,
    location: str | None = None,
    level: str | None = None,
) -> JobSearchIntent:
    cleaned_query = query.strip()
    cleaned_location = location.strip() if location and location.strip() else None
    return JobSearchIntent(
        query=cleaned_query,
        job_function=_query_job_function(cleaned_query),
        industry=_query_industry(cleaned_query),
        level=resolve_job_level(cleaned_query, level),
        location=cleaned_location,
    )


def _sports_title_or_company_matches(title: str, company: str | None = None) -> bool:
    title_and_company = f"{title} {company or ''}".lower()
    return _contains_any(title_and_company, SPORTS_TITLE_OR_COMPANY_TERMS)


def _sports_description_evidence_score(description: str) -> int:
    normalized = description.lower()
    if _contains_any(normalized, SPORTS_DESCRIPTION_STRONG_PHRASES):
        return 3

    if not _contains_any(normalized, SPORTS_DESCRIPTION_ANCHOR_TERMS):
        return 0

    signal_groups = sum(
        1 for terms in SPORTS_DESCRIPTION_SIGNAL_GROUPS if _contains_any(normalized, terms)
    )
    return 3 if signal_groups >= 3 else signal_groups


def _matches_requested_industry(
    title: str,
    description: str,
    query: str,
    company: str | None = None,
) -> bool:
    industry = _query_industry(query)
    if industry is None:
        return True

    if industry == "sports":
        if _sports_title_or_company_matches(title, company=company):
            return True
        return _sports_description_evidence_score(description) >= 3

    return True


def _is_software_role_query(query: str) -> bool:
    return _query_role_family(query) == "software"


def _is_strict_software_query(query: str) -> bool:
    normalized = query.lower().strip()
    return _contains_phrase(normalized, "swe") or _contains_phrase(normalized, "software engineer") or _contains_phrase(normalized, "software engineering")


def _title_matches_role_family(title: str, family: RoleFamily) -> bool:
    normalized_title = title.lower()
    if family == "software" and any(term in normalized_title for term in NON_SOFTWARE_TITLE_TERMS):
        return False
    return _contains_any(normalized_title, ROLE_FAMILY_TITLE_TERMS[family])


def _text_matches_role_family(value: str, family: RoleFamily) -> bool:
    return _contains_any(value.lower(), ROLE_FAMILY_TITLE_TERMS[family])


STRICT_DESCRIPTION_ONLY_ROLE_FAMILIES: set[RoleFamily] = {
    "legal",
    "compliance",
    "policy",
    "legal_operations",
    "contracts",
}


def _title_matches_other_role_family(title: str, requested_family: RoleFamily) -> bool:
    return any(
        family not in {requested_family, "technology"}
        and _title_matches_role_family(title, family)
        for family in ROLE_FAMILY_TITLE_TERMS
    )


def _looks_like_software_role(title: str) -> bool:
    return _title_matches_role_family(title, "software")


def _title_contains_core_query_term(title: str, query: str) -> bool:
    title_lower = title.lower()
    core_terms = _core_query_terms(query)
    if _is_strict_software_query(query):
        core_terms = core_terms - GENERIC_SOFTWARE_QUERY_TERMS
    return any(_contains_phrase(title_lower, term) for term in core_terms if len(term) > 2)


def _matches_requested_role(title: str, description: str, query: str, level: JobLevel | None = None) -> bool:
    canonical_family = _query_job_function(query)
    legacy_family = _query_role_family(query)
    family = (
        canonical_family
        if canonical_family in STRICT_DESCRIPTION_ONLY_ROLE_FAMILIES
        else legacy_family
    )
    if family is None:
        return True

    title_matches_requested_family = _title_matches_role_family(title, family)
    if (
        family in STRICT_DESCRIPTION_ONLY_ROLE_FAMILIES
        and not title_matches_requested_family
        and _title_matches_other_role_family(title, family)
    ):
        return False

    if title_matches_requested_family:
        return True

    # SWE/software-engineer searches should feel narrow. Do not let generic
    # terms like "engineer" or "developer" admit Analytics Engineer, Sales
    # Engineer, Solutions Engineer, etc. Broader queries such as "computer
    # science jobs" intentionally use the technology family instead.
    if family != "software" and _title_contains_core_query_term(title, query):
        return True
    if family == "software" and not _is_strict_software_query(query) and _title_contains_core_query_term(title, query):
        return True

    title_lower = title.lower()
    description_lower = description.lower()
    is_generic_early_career_title = _contains_any(
        title_lower,
        {"intern", "internship", "summer analyst", "analyst intern", "rotational program", "graduate program"},
    )
    if (
        family in STRICT_DESCRIPTION_ONLY_ROLE_FAMILIES
        and _title_matches_other_role_family(title, family)
    ):
        return False
    return bool(
        (level in {"intern", "entry"} or _infer_level_from_query(query) in {"intern", "entry"})
        and is_generic_early_career_title
        and _text_matches_role_family(description_lower, family)
    )


def _max_required_years(description: str) -> int:
    years = [int(match.group(1)) for match in EXPERIENCE_YEARS_PATTERN.finditer(description)]
    return max(years, default=0)


def _title_has_senior_signal(title: str) -> bool:
    return _contains_any(title.lower(), SENIOR_TERMS) or SENIOR_NUMBERED_TITLE_PATTERN.search(title) is not None


def _title_has_mid_signal(title: str) -> bool:
    return _contains_any(title.lower(), MID_TERMS) or MID_LEVEL_TITLE_PATTERN.search(title) is not None


def _looks_like_intern_role(title: str, description: str) -> bool:
    searchable = f"{title} {description}".lower()
    return _contains_any(searchable, INTERN_TERMS)


def _looks_like_senior_role(title: str, description: str) -> bool:
    searchable = f"{title} {description}".lower()
    if _title_has_senior_signal(title) or _contains_any(searchable, SENIOR_TERMS):
        return True

    return _max_required_years(description) >= 5


def _looks_like_entry_role(title: str, description: str) -> bool:
    title_lower = title.lower()
    description_lower = description.lower()

    if _looks_like_intern_role(title, description):
        return False

    if _title_has_senior_signal(title) or _title_has_mid_signal(title):
        return False

    if _contains_any(title_lower, ENTRY_TITLE_TERMS) or ENTRY_NUMBERED_TITLE_PATTERN.search(title):
        return True

    if _contains_any(description_lower, ENTRY_DESCRIPTION_TERMS):
        return True

    max_years = _max_required_years(description)
    return 0 < max_years <= 3 and not _looks_like_senior_role(title, description)


def _looks_like_mid_role(title: str, description: str) -> bool:
    if _looks_like_intern_role(title, description) or _looks_like_entry_role(title, description):
        return False
    if _title_has_mid_signal(title):
        return True

    max_years = _max_required_years(description)
    return 3 <= max_years <= 5 and not _looks_like_senior_role(title, description)


def _matches_level(title: str, description: str, level: JobLevel) -> bool:
    if level == "any":
        return True
    if level == "intern":
        return _looks_like_intern_role(title, description)
    if level == "entry":
        return _looks_like_entry_role(title, description)
    if level == "mid":
        return _looks_like_mid_role(title, description)
    if level == "senior":
        return _looks_like_senior_role(title, description)

    return True


def _level_score_bonus(title: str, description: str, level: JobLevel) -> int:
    if level == "any" or not _matches_level(title, description, level):
        return 0
    title_lower = title.lower()
    if level == "intern" and _contains_any(title_lower, INTERN_TERMS):
        return 10
    if level == "entry" and (_contains_any(title_lower, ENTRY_TITLE_TERMS) or ENTRY_NUMBERED_TITLE_PATTERN.search(title)):
        return 8
    if level == "mid" and _title_has_mid_signal(title):
        return 8
    if level == "senior" and _title_has_senior_signal(title):
        return 8
    return 4


def _has_non_us_location(job_location: str | None) -> bool:
    if not job_location:
        return False
    normalized_location = job_location.lower()
    return _contains_any(normalized_location, NON_US_LOCATION_TERMS)


def _is_default_us_market_location(job_location: str | None) -> bool:
    if not job_location:
        return True

    normalized_location = job_location.lower()
    if _has_non_us_location(job_location):
        return False

    if "worldwide" in normalized_location:
        return True

    if "remote" in normalized_location:
        return _contains_any(normalized_location, US_LOCATION_TERMS)

    return _contains_any(normalized_location, US_LOCATION_TERMS)


def _requested_location_terms(requested_location: str) -> set[str]:
    requested = requested_location.lower().strip()
    requested = re.sub(r"\s+", " ", requested)
    normalized_no_punctuation = _normalize_location_text(requested)

    terms = {requested, normalized_no_punctuation}
    terms.update(LOCATION_ALIASES.get(requested, set()))
    terms.update(LOCATION_ALIASES.get(normalized_no_punctuation, set()))

    city_part = requested.split(",", maxsplit=1)[0].strip()
    normalized_city_part = _normalize_location_text(city_part)
    if normalized_city_part != normalized_no_punctuation:
        terms.add(normalized_city_part)
        terms.update(LOCATION_ALIASES.get(normalized_city_part, set()))

    if " " not in normalized_no_punctuation:
        terms.add(normalized_no_punctuation)

    return {term for term in terms if term}


def _is_us_remote_location(job_location: str | None) -> bool:
    if not job_location or _has_non_us_location(job_location):
        return False

    normalized = job_location.lower()
    return ("remote" in normalized or "worldwide" in normalized) and _is_default_us_market_location(job_location)


def _is_us_city_or_state_request(requested_location: str) -> bool:
    terms = _requested_location_terms(requested_location)
    known_terms = set(US_LOCATION_TERMS)
    for aliases in LOCATION_ALIASES.values():
        known_terms.update(aliases)
    known_terms.update(LOCATION_ALIASES.keys())
    return bool(terms & known_terms)


def _matches_location(job_location: str | None, requested_location: str | None) -> bool:
    if not requested_location:
        return _is_default_us_market_location(job_location)

    if not job_location:
        return False

    requested = requested_location.lower().strip()
    location = job_location.lower()
    if requested == "remote":
        return ("remote" in location or "worldwide" in location) and not _has_non_us_location(job_location)

    requested_terms = _requested_location_terms(requested_location)
    if _contains_any(location, requested_terms):
        return True

    return _is_us_city_or_state_request(requested_location) and _is_us_remote_location(job_location)


def _location_score_bonus(job_location: str | None, requested_location: str | None) -> int:
    if not requested_location or not job_location:
        return 0

    requested = requested_location.lower().strip()
    location = job_location.lower()
    if requested == "remote" and ("remote" in location or "worldwide" in location):
        return 6
    if _contains_any(location, _requested_location_terms(requested_location)):
        return 8
    if _is_us_remote_location(job_location):
        return 2
    return 0


def _score_job(
    title: str,
    description: str,
    query: str,
    level: str | None = None,
    company: str | None = None,
) -> int:
    resolved_level = resolve_job_level(query, level)
    if not _matches_requested_industry(title, description, query, company=company):
        return 0
    if not _matches_requested_role(title, description, query, resolved_level):
        return 0

    if not _matches_level(title, description, resolved_level):
        return 0

    canonical_family = _query_job_function(query)
    legacy_family = _query_role_family(query)
    family = (
        canonical_family
        if canonical_family in STRICT_DESCRIPTION_ONLY_ROLE_FAMILIES
        else legacy_family
    )
    industry = _query_industry(query)
    terms = _query_terms(query)
    searchable_title = title.lower()
    searchable_description = description.lower()
    score = _level_score_bonus(title, description, resolved_level)

    if family and _title_matches_role_family(title, family):
        score += 8

    if industry == "sports":
        score += 10 if _sports_title_or_company_matches(title, company=company) else 6

    for term in terms:
        if term in searchable_title:
            score += 4
        if term in searchable_description:
            score += 1

    if "swe" in query.lower() and _looks_like_software_role(title):
        score += 10
    if "swe" in query.lower() and "software" in searchable_title and "engineer" in searchable_title:
        score += 4

    return score


def _provider_company_name(provider_token: str) -> str:
    return organization_name(provider_token)


def _normalize_greenhouse_job(board_token: str, raw_job: dict[str, Any]) -> ExternalJobResult | None:
    job_id = raw_job.get("id")
    title = str(raw_job.get("title") or "").strip()
    apply_url = sanitize_external_https_url(str(raw_job.get("absolute_url") or ""))
    if not job_id or not title or apply_url is None:
        return None

    location_payload = raw_job.get("location")
    location = None
    if isinstance(location_payload, dict):
        raw_location = location_payload.get("name")
        location = str(raw_location).strip() if raw_location else None

    description = clean_job_description(str(raw_job.get("content") or "")) or title
    return ExternalJobResult(
        id=f"greenhouse:{board_token}:{job_id}",
        source="greenhouse",
        company=_provider_company_name(board_token),
        title=title,
        location=location,
        description=description[:50_000],
        apply_url=apply_url,
        updated_at=str(raw_job.get("updated_at") or "").strip() or None,
    )


def _lever_location(raw_job: dict[str, Any]) -> str | None:
    categories = raw_job.get("categories")
    if not isinstance(categories, dict):
        return None

    all_locations = categories.get("allLocations")
    if isinstance(all_locations, list) and all_locations:
        values = [str(location).strip() for location in all_locations if str(location).strip()]
        if values:
            return "; ".join(values)

    raw_location = categories.get("location")
    return str(raw_location).strip() if raw_location else None


def _lever_description(raw_job: dict[str, Any], title: str) -> str:
    parts: list[str] = []
    for key in ("descriptionPlain", "description", "additionalPlain", "additional"):
        value = raw_job.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value)

    lists = raw_job.get("lists")
    if isinstance(lists, list):
        for item in lists:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            content = item.get("content")
            if isinstance(text, str) and text.strip():
                parts.append(text)
            if isinstance(content, str) and content.strip():
                parts.append(content)

    return clean_job_description(" ".join(parts)) or title


def _normalize_lever_job(site_name: str, raw_job: dict[str, Any]) -> ExternalJobResult | None:
    job_id = str(raw_job.get("id") or "").strip()
    title = str(raw_job.get("text") or "").strip()
    apply_url = sanitize_external_https_url(
        str(raw_job.get("hostedUrl") or raw_job.get("applyUrl") or "")
    )
    if not job_id or not title or apply_url is None:
        return None

    return ExternalJobResult(
        id=f"lever:{site_name}:{job_id}",
        source="lever",
        company=_provider_company_name(site_name),
        title=title,
        location=_lever_location(raw_job),
        description=_lever_description(raw_job, title)[:50_000],
        apply_url=apply_url,
        updated_at=str(raw_job.get("createdAt") or "").strip() or None,
    )


def _normalize_remoteok_job(raw_job: dict[str, Any]) -> ExternalJobResult | None:
    job_id = str(raw_job.get("id") or raw_job.get("slug") or "").strip()
    title = str(raw_job.get("position") or raw_job.get("title") or "").strip()
    company = str(raw_job.get("company") or "").strip()
    apply_url = sanitize_external_https_url(
        str(raw_job.get("url") or raw_job.get("apply_url") or "")
    )
    if not job_id or not title or not company or apply_url is None:
        return None

    raw_location = str(raw_job.get("location") or "").strip()
    location = f"Remote ({raw_location})" if raw_location else "Remote"
    description = clean_job_description(str(raw_job.get("description") or "")) or title
    return ExternalJobResult(
        id=f"remoteok:{job_id}",
        source="remoteok",
        company=company,
        title=title,
        location=location,
        description=description[:50_000],
        apply_url=apply_url,
        updated_at=str(raw_job.get("date") or raw_job.get("epoch") or "").strip() or None,
    )


def _normalize_remotive_job(raw_job: dict[str, Any]) -> ExternalJobResult | None:
    job_id = str(raw_job.get("id") or "").strip()
    title = str(raw_job.get("title") or "").strip()
    company = str(raw_job.get("company_name") or "").strip()
    apply_url = sanitize_external_https_url(str(raw_job.get("url") or ""))
    if not job_id or not title or not company or apply_url is None:
        return None

    raw_location = str(raw_job.get("candidate_required_location") or "").strip()
    location = f"Remote ({raw_location})" if raw_location else "Remote"
    description_parts = [str(raw_job.get("description") or "")]
    for key in ("job_type", "category", "salary"):
        value = str(raw_job.get(key) or "").strip()
        if value:
            description_parts.append(value)
    description = clean_job_description(" ".join(description_parts)) or title

    return ExternalJobResult(
        id=f"remotive:{job_id}",
        source="remotive",
        company=company,
        title=title,
        location=location,
        description=description[:50_000],
        apply_url=apply_url,
        updated_at=str(raw_job.get("publication_date") or "").strip() or None,
    )




def _greenhouse_jobs_for_board(
    client: httpx.Client,
    board_token: str,
) -> list[dict[str, Any]]:
    cache_key = f"greenhouse:{board_token}"
    cached = _cached_ats_jobs(cache_key)
    if cached is not None:
        return cached

    _consume_provider_request()
    response = client.get(
        f"{GREENHOUSE_BASE_URL}/{board_token}/jobs",
        params={"content": "true"},
    )
    response.raise_for_status()
    payload = response.json()
    raw_jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    jobs = [job for job in raw_jobs if isinstance(job, dict)] if isinstance(raw_jobs, list) else []
    _store_ats_jobs(cache_key, jobs)
    return jobs


def _lever_jobs_for_site(
    client: httpx.Client,
    site_name: str,
) -> list[dict[str, Any]]:
    cache_key = f"lever:{site_name}"
    cached = _cached_ats_jobs(cache_key)
    if cached is not None:
        return cached

    _consume_provider_request()
    response = client.get(
        f"{LEVER_BASE_URL}/{site_name}",
        params={"mode": "json", "limit": str(MAX_PROVIDER_RESULTS_PER_BOARD)},
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    payload = response.json()
    jobs = [job for job in payload if isinstance(job, dict)] if isinstance(payload, list) else []
    _store_ats_jobs(cache_key, jobs)
    return jobs


def _search_greenhouse_boards(
    client: httpx.Client,
    board_tokens: list[str],
    query: str,
    location: str | None,
    level: JobLevel,
) -> _ProviderOutcome:
    scored_jobs: list[tuple[int, ExternalJobResult]] = []
    fetched_count = 0
    errors = 0
    budget_exhausted = False

    for board_token in board_tokens:
        try:
            raw_jobs = _greenhouse_jobs_for_board(client, board_token)
        except ProviderRequestBudgetExceeded:
            budget_exhausted = True
            break
        except (httpx.HTTPError, ValueError):
            errors += 1
            continue
        fetched_count += len(raw_jobs)

        for raw_job in raw_jobs[:MAX_PROVIDER_RESULTS_PER_BOARD]:
            if not isinstance(raw_job, dict):
                continue
            job = _normalize_greenhouse_job(board_token, raw_job)
            if job is None or not _matches_location(job.location, location):
                continue
            score = _score_job(job.title, job.description, query, level, company=job.company)
            if score > 0:
                scored_jobs.append((score + _location_score_bonus(job.location, location), job))

    notes = ["Configured company ATS boards; coverage depends on the selected company tokens."]
    if errors:
        notes.append(f"{errors} Greenhouse board request{'s' if errors != 1 else ''} failed or returned invalid data.")
    if budget_exhausted:
        notes.append("Stopped Greenhouse requests after the per-search provider budget was reached.")
    return _ProviderOutcome("greenhouse", "Greenhouse company boards", fetched_count, scored_jobs, notes=notes)


def _search_lever_sites(
    client: httpx.Client,
    site_names: list[str],
    query: str,
    location: str | None,
    level: JobLevel,
) -> _ProviderOutcome:
    scored_jobs: list[tuple[int, ExternalJobResult]] = []
    fetched_count = 0
    errors = 0
    budget_exhausted = False

    for site_name in site_names:
        try:
            raw_jobs = _lever_jobs_for_site(client, site_name)
        except ProviderRequestBudgetExceeded:
            budget_exhausted = True
            break
        except (httpx.HTTPError, ValueError):
            errors += 1
            continue
        fetched_count += len(raw_jobs)

        for raw_job in raw_jobs[:MAX_PROVIDER_RESULTS_PER_BOARD]:
            if not isinstance(raw_job, dict):
                continue
            job = _normalize_lever_job(site_name, raw_job)
            if job is None or not _matches_location(job.location, location):
                continue
            score = _score_job(job.title, job.description, query, level, company=job.company)
            if score > 0:
                scored_jobs.append((score + _location_score_bonus(job.location, location), job))

    notes = ["Configured company ATS boards; coverage depends on the selected company tokens."]
    if errors:
        notes.append(f"{errors} Lever site request{'s' if errors != 1 else ''} failed or returned invalid data.")
    if budget_exhausted:
        notes.append("Stopped Lever requests after the per-search provider budget was reached.")
    return _ProviderOutcome("lever", "Lever company boards", fetched_count, scored_jobs, notes=notes)


def _remoteok_jobs(client: httpx.Client, query: str) -> list[dict[str, Any]]:
    now = time.monotonic()
    family = _query_role_family(query)
    cache_key = family or "all"
    cached_jobs = _REMOTEOK_CACHE.get(f"jobs:{cache_key}")
    if isinstance(cached_jobs, list) and now < float(_REMOTEOK_CACHE.get(f"expires_at:{cache_key}", 0.0)):
        return cached_jobs

    params: dict[str, str] = {}
    if family in {"software", "technology"}:
        params["tag"] = "dev"

    _consume_provider_request()
    response = client.get(
        REMOTEOK_BASE_URL,
        params=params,
        headers={"Accept": "application/json", "User-Agent": "MarketLens Career Intelligence"},
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        return []

    jobs = [item for item in payload if isinstance(item, dict) and item.get("id")]
    _REMOTEOK_CACHE[f"jobs:{cache_key}"] = jobs
    _REMOTEOK_CACHE[f"expires_at:{cache_key}"] = now + REMOTEOK_CACHE_SECONDS
    return jobs


def _search_remoteok(client: httpx.Client, query: str, location: str | None, level: JobLevel) -> _ProviderOutcome:
    try:
        raw_jobs = _remoteok_jobs(client, query)
    except (httpx.HTTPError, ValueError, ProviderRequestBudgetExceeded) as exc:
        return _ProviderOutcome(
            "remoteok",
            "Remote OK remote feed",
            0,
            [],
            status="failed",
            notes=[f"Remote OK request failed: {exc.__class__.__name__}."],
        )

    scored_jobs: list[tuple[int, ExternalJobResult]] = []
    for raw_job in raw_jobs[:MAX_PROVIDER_RESULTS_PER_BOARD]:
        job = _normalize_remoteok_job(raw_job)
        if job is None or not _matches_location(job.location, location):
            continue
        score = _score_job(job.title, job.description, query, level, company=job.company)
        if score > 0:
            scored_jobs.append((score + _location_score_bonus(job.location, location), job))

    return _ProviderOutcome(
        "remoteok",
        "Remote OK remote feed",
        len(raw_jobs),
        scored_jobs,
        notes=["Remote-first feed. Stronger for remote tech roles than local internship coverage."],
    )


def _remotive_search_terms(query: str, level: JobLevel) -> list[str | None]:
    family = _query_role_family(query)
    core_terms = sorted(_core_query_terms(query))
    normalized = query.lower().strip()

    terms: list[str | None] = []
    if normalized:
        terms.append(normalized)

    if family == "technology":
        terms.extend(["software", "data", "analytics", "cybersecurity", "developer"])
    elif family == "software":
        if "backend" in normalized:
            terms.extend(["backend", "backend developer"])
        elif "frontend" in normalized or "front end" in normalized:
            terms.extend(["frontend", "frontend developer"])
        elif "full stack" in normalized or "full-stack" in normalized:
            terms.extend(["full stack", "full stack developer"])
        else:
            terms.extend(["software", "developer"])
    elif family == "finance":
        terms.extend(["finance", "accounting", "financial analyst", "audit", "tax"])
        if level == "intern":
            terms.extend(["finance intern", "finance internship", "accounting intern", "accounting internship", "summer analyst", "intern"])
        elif level == "entry":
            terms.extend(["junior financial analyst", "entry level finance", "junior accountant"])
    elif family == "data":
        terms.extend(["data analyst", "analytics", "business intelligence"])
        if level == "intern":
            terms.extend(["data intern", "data analyst intern", "analytics intern"])
    elif family == "cybersecurity":
        terms.extend(["cybersecurity", "security analyst", "information security"])
        if level == "intern":
            terms.extend(["cybersecurity intern", "security intern"])
    elif family:
        terms.extend(core_terms)
        if level == "intern":
            terms.extend([f"{term} intern" for term in core_terms if len(term) > 2])
    elif level == "intern":
        terms.extend(["intern", "internship"])
    elif level == "entry":
        terms.extend(["junior", "entry level"])

    if family in {"software", "finance", "technology"}:
        terms.append(None)

    seen: set[str | None] = set()
    unique_terms: list[str | None] = []
    for term in terms:
        normalized_term = term.strip().lower() if isinstance(term, str) else None
        if normalized_term in seen:
            continue
        seen.add(normalized_term)
        unique_terms.append(normalized_term)
        if len(unique_terms) >= 8:
            break
    return unique_terms


def _remotive_category_for_family(family: RoleFamily | None) -> str | None:
    if family == "software":
        return "software-dev"
    if family == "finance":
        return "finance"
    return None


def _remotive_jobs_for_params(client: httpx.Client, params: dict[str, str]) -> list[dict[str, Any]]:
    cache_key = "&".join(f"{key}={value}" for key, value in sorted(params.items())) or "all"
    now = time.monotonic()
    cached = _REMOTIVE_CACHE.get(cache_key)
    if cached and now < float(cached.get("expires_at", 0.0)):
        cached_jobs = cached.get("jobs")
        if isinstance(cached_jobs, list):
            return cached_jobs

    _consume_provider_request()
    response = client.get(
        REMOTIVE_BASE_URL,
        params=params,
        headers={"Accept": "application/json", "User-Agent": "MarketLens Career Intelligence"},
    )
    response.raise_for_status()
    payload = response.json()
    raw_jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    if not isinstance(raw_jobs, list):
        return []

    jobs = [item for item in raw_jobs if isinstance(item, dict) and item.get("id")]
    _REMOTIVE_CACHE[cache_key] = {"jobs": jobs, "expires_at": now + REMOTIVE_CACHE_SECONDS}
    return jobs


def _remotive_jobs(client: httpx.Client, query: str, level: JobLevel) -> tuple[list[dict[str, Any]], list[str]]:
    family = _query_role_family(query)
    category = _remotive_category_for_family(family)
    search_terms = _remotive_search_terms(query, level)
    raw_jobs_by_id: dict[str, dict[str, Any]] = {}
    failed_searches = 0
    budget_exhausted = False

    for search_term in search_terms:
        params: dict[str, str] = {"limit": str(MAX_PROVIDER_RESULTS_PER_BOARD)}
        if category:
            params["category"] = category
        if search_term:
            params["search"] = search_term

        try:
            for raw_job in _remotive_jobs_for_params(client, params):
                raw_jobs_by_id[str(raw_job.get("id"))] = raw_job
        except ProviderRequestBudgetExceeded:
            budget_exhausted = True
            break
        except (httpx.HTTPError, ValueError):
            failed_searches += 1

    notes = [
        f"Tried {len(search_terms)} Remotive search pass{'es' if len(search_terms) != 1 else ''} for this role family."
    ]
    if failed_searches:
        notes.append(f"{failed_searches} Remotive search pass{'es' if failed_searches != 1 else ''} failed.")
    if budget_exhausted:
        notes.append("Stopped Remotive requests after the per-search provider budget was reached.")
    notes.append("Remotive is remote-first; it may not cover local or campus internship postings.")
    return list(raw_jobs_by_id.values()), notes


def _search_remotive(client: httpx.Client, query: str, location: str | None, level: JobLevel) -> _ProviderOutcome:
    raw_jobs, notes = _remotive_jobs(client, query, level)
    scored_jobs: list[tuple[int, ExternalJobResult]] = []
    for raw_job in raw_jobs[:MAX_PROVIDER_RESULTS_PER_BOARD]:
        job = _normalize_remotive_job(raw_job)
        if job is None or not _matches_location(job.location, location):
            continue
        score = _score_job(job.title, job.description, query, level, company=job.company)
        if score > 0:
            scored_jobs.append((score + _location_score_bonus(job.location, location), job))

    return _ProviderOutcome("remotive", "Remotive remote feed", len(raw_jobs), scored_jobs, notes=notes)


def _coverage_from_outcome(outcome: _ProviderOutcome) -> SourceCoverageSummary:
    return SourceCoverageSummary(
        provider=outcome.provider,
        label=outcome.label,
        status=outcome.status,
        fetched_count=outcome.fetched_count,
        matched_count=outcome.matched_count,
        notes=outcome.notes,
    )


def _external_search_query(query: str, location: str | None, level: JobLevel) -> str:
    query_parts = [query.strip()]
    if level == "intern" and not _contains_any(query.lower(), INTERN_TERMS):
        query_parts.append("internship")
    elif level == "entry" and not _contains_any(query.lower(), ENTRY_TITLE_TERMS):
        query_parts.append("entry level")

    if location and location.lower().strip() != "remote":
        query_parts.append(location.strip())
    elif location and location.lower().strip() == "remote":
        query_parts.append("remote")

    return " ".join(part for part in query_parts if part).strip()


def _external_search_links(query: str, location: str | None, level: JobLevel) -> list[ExternalSearchLink]:
    external_query = _external_search_query(query, location, level)
    query_param = quote_plus(external_query)
    location_param = quote_plus(location or "United States")

    links = [
        ExternalSearchLink(
            label="Google Jobs search",
            url=f"https://www.google.com/search?q={quote_plus(external_query + ' jobs')}",
            note="Broad fallback when API-friendly sources are thin.",
        ),
        ExternalSearchLink(
            label="Indeed search",
            url=f"https://www.indeed.com/jobs?q={query_param}&l={location_param}",
            note="Useful for local, finance, accounting, healthcare, and operations roles.",
        ),
        ExternalSearchLink(
            label="LinkedIn Jobs search",
            url=f"https://www.linkedin.com/jobs/search/?keywords={query_param}&location={location_param}",
            note="Useful for professional internships and company-posted roles.",
        ),
    ]

    if level == "intern":
        links.append(
            ExternalSearchLink(
                label="Handshake search",
                url=f"https://app.joinhandshake.com/stu/postings?query={query_param}",
                note="Often stronger for campus internships, but usually requires a school login.",
            )
        )

    return links


def _search_suggestions(query: str, location: str | None, level: JobLevel, role_family: RoleFamily | None) -> list[str]:
    suggestions: list[str] = []
    if role_family == "software" and _is_strict_software_query(query):
        suggestions.append("SWE/software engineer searches stay narrow; use 'computer science jobs' for broader technical roles like analytics engineer, data engineer, or security analyst.")
    if role_family == "technology":
        suggestions.append("Computer science searches are intentionally broader than SWE and may include software, data, analytics, and cybersecurity roles.")
    if role_family == "finance" and level == "intern":
        suggestions.extend([
            "Finance and accounting internships are often posted on Handshake, Workday-backed company career sites, LinkedIn, and Indeed rather than free remote-job APIs.",
            "Try broader terms such as 'finance', 'accounting', 'financial analyst', 'audit', 'tax', or 'summer analyst'.",
            "Try a broader location like 'PA', blank location, or 'Remote' depending on the user's flexibility.",
        ])
    elif role_family and level == "intern":
        suggestions.append("Internship coverage depends heavily on current postings in the configured public sources; use the fallback links when results are thin.")
    elif role_family is None:
        suggestions.append("Use a role-family phrase like finance internship, data analyst internship, marketing intern, computer science jobs, or software engineer to improve filtering.")

    if location and location.lower().strip() not in {"remote", "pa", "pennsylvania"}:
        suggestions.append("City searches stay city-specific but include U.S.-remote roles; use a state/region for broader local coverage.")

    suggestions.append("Manual Smart Fit comparison still works for any job posting copied from outside MarketLens search.")
    return suggestions


def _warnings_for_no_results(query: str, location: str | None, level: JobLevel, role_family: RoleFamily | None) -> list[str]:
    family_text = f" {role_family}" if role_family else ""
    level_text = "" if level == "any" else f" {level}"
    warning = (
        f"No matching{level_text}{family_text} jobs were found in MarketLens' configured API-friendly public sources. "
        "This does not mean no such jobs exist; it means the current public sources did not return a matching posting."
    )

    if role_family == "finance" and level == "intern":
        warning += " Finance/accounting internships are especially likely to live on campus boards, Workday/company career pages, LinkedIn, or Indeed."

    if location and location.lower() != "remote" and _is_us_city_or_state_request(location):
        warning += " U.S.-remote roles are included for city searches, but no matching results were found."

    return [warning]


def search_external_jobs(
    query: str,
    location: str | None = None,
    limit: int = 15,
    level: str | None = None,
) -> JobSearchResults:
    intent = parse_job_search_intent(query=query, location=location, level=level)
    cleaned_query = intent.query
    cleaned_location = intent.location
    resolved_level = intent.level
    role_family = intent.job_function
    industry = intent.industry
    configured_greenhouse_boards = _configured_greenhouse_boards()
    configured_lever_sites = _configured_lever_sites()
    routing_plan = build_source_routing_plan(
        greenhouse_identifiers=configured_greenhouse_boards,
        lever_identifiers=configured_lever_sites,
        industry=industry,
        job_function=role_family,
        level=resolved_level,
        location=cleaned_location,
    )
    greenhouse_boards = list(routing_plan.greenhouse_identifiers)
    lever_sites = list(routing_plan.lever_identifiers)
    remoteok_enabled = _remoteok_enabled()
    remotive_enabled = _remotive_enabled()

    providers_searched = [f"greenhouse:{board}" for board in greenhouse_boards]
    providers_searched.extend(f"lever:{site}" for site in lever_sites)
    if remoteok_enabled:
        providers_searched.append("remoteok")
    if remotive_enabled:
        providers_searched.append("remotive")

    outcomes: list[_ProviderOutcome] = []
    budget_token = _ACTIVE_PROVIDER_REQUEST_BUDGET.set(
        _ProviderRequestBudget(_provider_request_limit())
    )

    try:
        with _build_provider_client() as client:
            greenhouse_outcome = _search_greenhouse_boards(
                client,
                greenhouse_boards,
                cleaned_query,
                cleaned_location,
                resolved_level,
            )
            greenhouse_outcome.notes.insert(0, routing_plan.greenhouse_note)
            outcomes.append(greenhouse_outcome)

            lever_outcome = _search_lever_sites(
                client,
                lever_sites,
                cleaned_query,
                cleaned_location,
                resolved_level,
            )
            lever_outcome.notes.insert(0, routing_plan.lever_note)
            outcomes.append(lever_outcome)

            if remoteok_enabled:
                outcomes.append(_search_remoteok(client, cleaned_query, cleaned_location, resolved_level))
            else:
                outcomes.append(_ProviderOutcome("remoteok", "Remote OK remote feed", 0, [], status="disabled", notes=["Disabled by configuration."]))

            if remotive_enabled:
                outcomes.append(_search_remotive(client, cleaned_query, cleaned_location, resolved_level))
            else:
                outcomes.append(_ProviderOutcome("remotive", "Remotive remote feed", 0, [], status="disabled", notes=["Disabled by configuration."]))
    finally:
        _ACTIVE_PROVIDER_REQUEST_BUDGET.reset(budget_token)

    scored_results: list[tuple[int, ExternalJobResult]] = []
    for outcome in outcomes:
        scored_results.extend(outcome.scored_jobs)

    seen_ids: set[str] = set()
    ranked_results: list[ExternalJobResult] = []
    for _, job in sorted(scored_results, key=lambda item: (-item[0], item[1].company, item[1].title)):
        if job.id in seen_ids:
            continue
        seen_ids.add(job.id)
        ranked_results.append(job)
        if len(ranked_results) >= limit:
            break

    warnings: list[str] = []
    if not ranked_results:
        warnings.extend(_warnings_for_no_results(cleaned_query, cleaned_location, resolved_level, role_family))

    if all(outcome.status == "failed" for outcome in outcomes if outcome.provider in {"remoteok", "remotive"}) and not ranked_results:
        warnings.append("Remote public job feeds failed to respond. Try again later or use manual pasted-job comparison.")

    return JobSearchResults(
        query=cleaned_query,
        location=cleaned_location,
        level=resolved_level,
        role_family=role_family,
        industry=industry,
        providers_searched=providers_searched,
        source_coverage=[_coverage_from_outcome(outcome) for outcome in outcomes],
        results=ranked_results,
        warnings=warnings,
        search_suggestions=_search_suggestions(cleaned_query, cleaned_location, resolved_level, role_family),
        external_search_links=_external_search_links(cleaned_query, cleaned_location, resolved_level),
    )
