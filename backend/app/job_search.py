import os
import re
import time
from dataclasses import dataclass
from html import unescape
from typing import Any, Literal

import httpx

GREENHOUSE_BASE_URL = "https://boards-api.greenhouse.io/v1/boards"
LEVER_BASE_URL = "https://api.lever.co/v0/postings"
REMOTEOK_BASE_URL = "https://remoteok.com/api"

DEFAULT_GREENHOUSE_BOARDS = (
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
MAX_PROVIDER_RESULTS_PER_BOARD = 100
REMOTEOK_CACHE_SECONDS = 15 * 60

JobLevel = Literal["any", "intern", "entry", "mid", "senior"]
VALID_JOB_LEVELS: set[str] = {"any", "intern", "entry", "mid", "senior"}

EXPERIENCE_YEARS_PATTERN = re.compile(r"\b(\d{1,2})\s*\+?\s*(?:years?|yrs?)\b", re.IGNORECASE)
MID_LEVEL_TITLE_PATTERN = re.compile(
    r"\b(?:software\s+)?(?:engineer|developer)\s+(?:ii|iii|2|3)\b",
    re.IGNORECASE,
)
SENIOR_NUMBERED_TITLE_PATTERN = re.compile(
    r"\b(?:software\s+)?(?:engineer|developer)\s+(?:iv|v|4|5)\b",
    re.IGNORECASE,
)
SOFTWARE_ENGINEER_I_PATTERN = re.compile(
    r"\b(?:software\s+)?(?:engineer|developer)\s+(?:i|1)\b",
    re.IGNORECASE,
)

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
    # Keep city searches city-specific. Philadelphia should not match every PA job.
    "philadelphia": {"philadelphia", "philly"},
    "philly": {"philadelphia", "philly"},
    "pittsburgh": {"pittsburgh"},
    "pennsylvania": {"pennsylvania", "pa", "philadelphia", "pittsburgh"},
    "pa": {"pennsylvania", "pa", "philadelphia", "pittsburgh"},
    "new york": {"new york", "nyc", "new york city", "ny"},
    "new york city": {"new york", "nyc", "new york city", "ny"},
    "nyc": {"new york", "nyc", "new york city", "ny"},
    "washington dc": {"washington", "washington dc", "washington, dc", "dc", "d.c."},
    "washington, dc": {"washington", "washington dc", "washington, dc", "dc", "d.c."},
    "dc": {"washington", "washington dc", "washington, dc", "dc", "d.c."},
    "san francisco": {"san francisco", "sf", "bay area", "california", "ca"},
    "bay area": {"san francisco", "sf", "bay area", "california", "ca"},
    "seattle": {"seattle", "washington", "wa"},
    "boston": {"boston", "massachusetts", "ma"},
    "chicago": {"chicago", "illinois", "il"},
    "austin": {"austin", "texas", "tx"},
    "denver": {"denver", "colorado", "co"},
}
NON_SOFTWARE_TITLE_TERMS = {
    "account executive",
    "business development",
    "customer success",
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
    "back-end engineer",
    "frontend engineer",
    "front-end engineer",
    "full stack engineer",
    "full-stack engineer",
    "mobile engineer",
    "ios engineer",
    "android engineer",
    "platform engineer",
    "infrastructure engineer",
    "forward deployed software engineer",
}
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
    "engineer ii",
    "engineer iii",
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
class JobSearchResults:
    query: str
    location: str | None
    level: JobLevel
    providers_searched: list[str]
    results: list[ExternalJobResult]
    warnings: list[str]


def _configured_greenhouse_boards() -> list[str]:
    raw_boards = os.getenv("JOB_SEARCH_GREENHOUSE_BOARDS")
    if raw_boards:
        boards = [board.strip() for board in raw_boards.split(",") if board.strip()]
        return boards or list(DEFAULT_GREENHOUSE_BOARDS)

    return list(DEFAULT_GREENHOUSE_BOARDS)


def _configured_lever_sites() -> list[str]:
    raw_sites = os.getenv("JOB_SEARCH_LEVER_SITES")
    if raw_sites:
        sites = [site.strip() for site in raw_sites.split(",") if site.strip()]
        return sites or list(DEFAULT_LEVER_SITES)

    return list(DEFAULT_LEVER_SITES)


def _remoteok_enabled() -> bool:
    return os.getenv("JOB_SEARCH_REMOTEOK_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}


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
        "swe": ["software", "engineer"],
        "software engineering": ["software", "engineer"],
        "backend": ["backend"],
        "back end": ["backend"],
        "front end": ["frontend"],
        "full stack": ["full", "stack"],
        "ml": ["machine", "learning"],
        "ai": ["ai"],
        "intern": ["intern"],
        "internship": ["intern"],
        "entry level": ["entry", "level"],
        "entry-level": ["entry", "level"],
        "new grad": ["new", "grad"],
    }

    terms = re.findall(r"[a-z0-9+#.]+", normalized)
    for phrase, extra_terms in expansions.items():
        if phrase in normalized:
            terms.extend(extra_terms)

    return sorted(set(term for term in terms if len(term) > 1))


def _contains_phrase(value: str, phrase: str) -> bool:
    """Match whole words/phrases, so 'intern' does not match 'internal'."""
    cleaned_phrase = phrase.strip().lower()
    if not cleaned_phrase:
        return False

    escaped_words = [re.escape(part) for part in re.split(r"[\s,.-]+", cleaned_phrase) if part]
    if not escaped_words:
        return False

    separator = r"[\s,.-]+"
    pattern = r"(?<![a-z0-9])" + separator.join(escaped_words) + r"(?![a-z0-9])"
    return bool(re.search(pattern, value.lower()))


def _contains_any(value: str, terms: set[str]) -> bool:
    return any(_contains_phrase(value, term) for term in terms)


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


def _is_software_role_query(query: str) -> bool:
    normalized = query.lower()
    return any(
        phrase in normalized
        for phrase in (
            "swe",
            "software",
            "backend",
            "back end",
            "frontend",
            "front end",
            "full stack",
            "developer",
            "engineer",
        )
    )


def _looks_like_software_role(title: str) -> bool:
    normalized_title = title.lower()
    if any(term in normalized_title for term in NON_SOFTWARE_TITLE_TERMS):
        return False

    return any(term in normalized_title for term in SOFTWARE_TITLE_TERMS)


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

    # A requested Entry filter should not allow senior/staff/principal/lead or Engineer II/III+ titles.
    if _title_has_senior_signal(title) or _title_has_mid_signal(title):
        return False

    if _contains_any(title_lower, ENTRY_TITLE_TERMS) or SOFTWARE_ENGINEER_I_PATTERN.search(title):
        return True

    # Description signals can help, but keep them conservative. Generic words like
    # "associate" often appear in HR/legal text and should not make a senior role entry-level.
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
    if level == "any":
        return 0

    if not _matches_level(title, description, level):
        return 0

    title_lower = title.lower()
    if level == "intern" and _contains_any(title_lower, INTERN_TERMS):
        return 10
    if level == "entry" and (_contains_any(title_lower, ENTRY_TITLE_TERMS) or SOFTWARE_ENGINEER_I_PATTERN.search(title)):
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
    return any(term in normalized_location for term in NON_US_LOCATION_TERMS)


def _is_default_us_market_location(job_location: str | None) -> bool:
    if not job_location:
        return True

    normalized_location = job_location.lower()
    if _has_non_us_location(job_location):
        return False

    if "remote" in normalized_location or "worldwide" in normalized_location:
        return True

    return any(term in normalized_location for term in US_LOCATION_TERMS)


def _requested_location_terms(requested_location: str) -> set[str]:
    requested = requested_location.lower().strip()
    requested = re.sub(r"\s+", " ", requested)
    normalized_no_punctuation = requested.replace(",", "")
    words = [part for part in re.split(r"[\s,]+", requested) if len(part) > 2]

    terms = {requested, normalized_no_punctuation, *words}
    terms.update(LOCATION_ALIASES.get(requested, set()))
    terms.update(LOCATION_ALIASES.get(normalized_no_punctuation, set()))
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

    # When someone searches a U.S. city, U.S.-remote roles are still useful and
    # avoid making city searches look empty when companies only label roles as Remote-US.
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


def _score_job(title: str, description: str, query: str, level: str | None = None) -> int:
    resolved_level = resolve_job_level(query, level)

    # Search should find jobs, not decide whether a candidate is qualified.
    # For software queries, only block obvious non-software roles. Fit happens later.
    if _is_software_role_query(query) and not _looks_like_software_role(title):
        return 0

    if not _matches_level(title, description, resolved_level):
        return 0

    terms = _query_terms(query)
    searchable_title = title.lower()
    searchable_description = description.lower()
    score = _level_score_bonus(title, description, resolved_level)

    for term in terms:
        if term in searchable_title:
            score += 4
        if term in searchable_description:
            score += 1

    # Common shorthand: SWE should strongly favor software engineering titles.
    if "swe" in query.lower() and "software" in searchable_title and "engineer" in searchable_title:
        score += 12

    return score


def _provider_company_name(provider_token: str) -> str:
    special_names = {
        "addepar": "Addepar",
        "affirm": "Affirm",
        "algolia": "Algolia",
        "asana": "Asana",
        "benchling": "Benchling",
        "box": "Box",
        "brex": "Brex",
        "cloudflare": "Cloudflare",
        "coinbase": "Coinbase",
        "coursera": "Coursera",
        "datadog": "Datadog",
        "doordash": "DoorDash",
        "duolingo": "Duolingo",
        "figma": "Figma",
        "fivetran": "Fivetran",
        "github": "GitHub",
        "gusto": "Gusto",
        "hubspot": "HubSpot",
        "intercom": "Intercom",
        "lyft": "Lyft",
        "mixpanel": "Mixpanel",
        "mongodb": "MongoDB",
        "notion": "Notion",
        "okta": "Okta",
        "openai": "OpenAI",
        "pinterest": "Pinterest",
        "plaid": "Plaid",
        "postman": "Postman",
        "ramp": "Ramp",
        "reddit": "Reddit",
        "rippling": "Rippling",
        "roblox": "Roblox",
        "scaleai": "Scale AI",
        "snap": "Snap",
        "twitch": "Twitch",
        "verkada": "Verkada",
        "webflow": "Webflow",
        "zapier": "Zapier",
    }
    return special_names.get(provider_token, provider_token.replace("-", " ").replace("_", " ").title())


def _normalize_greenhouse_job(board_token: str, raw_job: dict[str, Any]) -> ExternalJobResult | None:
    job_id = raw_job.get("id")
    title = str(raw_job.get("title") or "").strip()
    apply_url = str(raw_job.get("absolute_url") or "").strip()
    if not job_id or not title or not apply_url:
        return None

    location_payload = raw_job.get("location")
    location = None
    if isinstance(location_payload, dict):
        raw_location = location_payload.get("name")
        location = str(raw_location).strip() if raw_location else None

    description = clean_job_description(str(raw_job.get("content") or ""))
    if not description:
        description = title

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

    description = clean_job_description(" ".join(parts))
    return description or title


def _normalize_lever_job(site_name: str, raw_job: dict[str, Any]) -> ExternalJobResult | None:
    job_id = str(raw_job.get("id") or "").strip()
    title = str(raw_job.get("text") or "").strip()
    apply_url = str(raw_job.get("hostedUrl") or raw_job.get("applyUrl") or "").strip()
    if not job_id or not title or not apply_url:
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
    apply_url = str(raw_job.get("url") or raw_job.get("apply_url") or "").strip()
    if not job_id or not title or not company or not apply_url:
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


def _search_greenhouse_board(
    client: httpx.Client,
    board_token: str,
    query: str,
    location: str | None,
    level: JobLevel,
) -> list[tuple[int, ExternalJobResult]]:
    response = client.get(
        f"{GREENHOUSE_BASE_URL}/{board_token}/jobs",
        params={"content": "true"},
    )
    response.raise_for_status()
    payload = response.json()
    raw_jobs = payload.get("jobs", [])
    if not isinstance(raw_jobs, list):
        return []

    scored_jobs: list[tuple[int, ExternalJobResult]] = []
    for raw_job in raw_jobs[:MAX_PROVIDER_RESULTS_PER_BOARD]:
        if not isinstance(raw_job, dict):
            continue

        job = _normalize_greenhouse_job(board_token, raw_job)
        if job is None or not _matches_location(job.location, location):
            continue

        score = _score_job(job.title, job.description, query, level)
        if score > 0:
            scored_jobs.append((score + _location_score_bonus(job.location, location), job))

    return scored_jobs


def _search_lever_site(
    client: httpx.Client,
    site_name: str,
    query: str,
    location: str | None,
    level: JobLevel,
) -> list[tuple[int, ExternalJobResult]]:
    response = client.get(
        f"{LEVER_BASE_URL}/{site_name}",
        params={"mode": "json", "limit": str(MAX_PROVIDER_RESULTS_PER_BOARD)},
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    raw_jobs = response.json()
    if not isinstance(raw_jobs, list):
        return []

    scored_jobs: list[tuple[int, ExternalJobResult]] = []
    for raw_job in raw_jobs[:MAX_PROVIDER_RESULTS_PER_BOARD]:
        if not isinstance(raw_job, dict):
            continue

        job = _normalize_lever_job(site_name, raw_job)
        if job is None or not _matches_location(job.location, location):
            continue

        score = _score_job(job.title, job.description, query, level)
        if score > 0:
            scored_jobs.append((score + _location_score_bonus(job.location, location), job))

    return scored_jobs


def _remoteok_jobs(client: httpx.Client) -> list[dict[str, Any]]:
    now = time.monotonic()
    cached_jobs = _REMOTEOK_CACHE.get("jobs")
    if isinstance(cached_jobs, list) and now < float(_REMOTEOK_CACHE.get("expires_at", 0.0)):
        return cached_jobs

    response = client.get(
        REMOTEOK_BASE_URL,
        params={"tag": "dev"},
        headers={"Accept": "application/json", "User-Agent": "MarketLens Career Intelligence"},
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        return []

    jobs = [item for item in payload if isinstance(item, dict) and item.get("id")]
    _REMOTEOK_CACHE["jobs"] = jobs
    _REMOTEOK_CACHE["expires_at"] = now + REMOTEOK_CACHE_SECONDS
    return jobs


def _search_remoteok(
    client: httpx.Client,
    query: str,
    location: str | None,
    level: JobLevel,
) -> list[tuple[int, ExternalJobResult]]:
    scored_jobs: list[tuple[int, ExternalJobResult]] = []
    for raw_job in _remoteok_jobs(client)[:MAX_PROVIDER_RESULTS_PER_BOARD]:
        job = _normalize_remoteok_job(raw_job)
        if job is None or not _matches_location(job.location, location):
            continue

        score = _score_job(job.title, job.description, query, level)
        if score > 0:
            scored_jobs.append((score + _location_score_bonus(job.location, location), job))

    return scored_jobs


def search_external_jobs(
    query: str,
    location: str | None = None,
    limit: int = 15,
    level: str | None = None,
) -> JobSearchResults:
    cleaned_query = query.strip()
    cleaned_location = location.strip() if location and location.strip() else None
    resolved_level = resolve_job_level(cleaned_query, level)
    greenhouse_boards = _configured_greenhouse_boards()
    lever_sites = _configured_lever_sites()
    remoteok_enabled = _remoteok_enabled()

    providers_searched = [f"greenhouse:{board}" for board in greenhouse_boards]
    providers_searched.extend(f"lever:{site}" for site in lever_sites)
    if remoteok_enabled:
        providers_searched.append("remoteok")

    warnings: list[str] = []
    provider_errors: list[str] = []
    successful_provider_count = 0
    scored_results: list[tuple[int, ExternalJobResult]] = []

    with httpx.Client(timeout=6.0, follow_redirects=True) as client:
        for board in greenhouse_boards:
            try:
                scored_results.extend(_search_greenhouse_board(client, board, cleaned_query, cleaned_location, resolved_level))
                successful_provider_count += 1
            except (httpx.HTTPError, ValueError) as exc:
                provider_errors.append(f"greenhouse:{board}:{exc.__class__.__name__}")

        for site in lever_sites:
            try:
                scored_results.extend(_search_lever_site(client, site, cleaned_query, cleaned_location, resolved_level))
                successful_provider_count += 1
            except (httpx.HTTPError, ValueError) as exc:
                provider_errors.append(f"lever:{site}:{exc.__class__.__name__}")

        if remoteok_enabled:
            try:
                scored_results.extend(_search_remoteok(client, cleaned_query, cleaned_location, resolved_level))
                successful_provider_count += 1
            except (httpx.HTTPError, ValueError) as exc:
                provider_errors.append(f"remoteok:{exc.__class__.__name__}")

    seen_ids: set[str] = set()
    ranked_results: list[ExternalJobResult] = []
    for _, job in sorted(scored_results, key=lambda item: (-item[0], item[1].company, item[1].title)):
        if job.id in seen_ids:
            continue
        seen_ids.add(job.id)
        ranked_results.append(job)
        if len(ranked_results) >= limit:
            break

    if not ranked_results:
        level_hint = "" if resolved_level == "any" else f" for level '{resolved_level}'"
        location_hint = ""
        if cleaned_location and cleaned_location.lower() != "remote" and _is_us_city_or_state_request(cleaned_location):
            location_hint = " U.S.-remote roles are included for city searches, but no matching results were found."
        warnings.append(
            f"No matching external jobs were found{level_hint} in the configured public Greenhouse/Lever/Remote OK job sources."
            f" Try a broader query, a different location, or manual pasted-job comparison.{location_hint}"
        )

    if successful_provider_count == 0 and provider_errors:
        warnings.append("All configured external job providers failed to respond. Check provider configuration or try again later.")

    return JobSearchResults(
        query=cleaned_query,
        location=cleaned_location,
        level=resolved_level,
        providers_searched=providers_searched,
        results=ranked_results,
        warnings=warnings,
    )
