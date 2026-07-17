import os
import re
from dataclasses import dataclass
from html import unescape
from typing import Any

import httpx

GREENHOUSE_BASE_URL = "https://boards-api.greenhouse.io/v1/boards"
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
)
MAX_PROVIDER_RESULTS_PER_BOARD = 75

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
    "philadelphia",
    "pittsburgh",
    "san francisco",
    "san jose",
    "seattle",
    "st. louis",
    "washington",
    "washington, dc",
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
}
SENIOR_TITLE_TERMS = {
    "principal",
    "staff",
    "senior",
    "sr.",
    "lead",
    "manager",
    "director",
    "architect",
}
SENIOR_QUERY_TERMS = {
    "principal",
    "staff",
    "senior",
    "sr",
    "lead",
    "manager",
    "director",
    "architect",
}


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
    providers_searched: list[str]
    results: list[ExternalJobResult]
    warnings: list[str]


def _configured_greenhouse_boards() -> list[str]:
    raw_boards = os.getenv("JOB_SEARCH_GREENHOUSE_BOARDS")
    if raw_boards:
        boards = [board.strip() for board in raw_boards.split(",") if board.strip()]
        return boards or list(DEFAULT_GREENHOUSE_BOARDS)

    return list(DEFAULT_GREENHOUSE_BOARDS)


def clean_job_description(value: str | None) -> str:
    """Turn provider HTML into plain text that is safe to display and analyze."""
    if not value:
        return ""

    # Some Greenhouse boards return actual HTML while others return escaped HTML.
    # Decode first, strip tags, then decode again for entities inside text nodes.
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
    }

    terms = re.findall(r"[a-z0-9+#.]+", normalized)
    for phrase, extra_terms in expansions.items():
        if phrase in normalized:
            terms.extend(extra_terms)

    return sorted(set(term for term in terms if len(term) > 1))


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


def _allows_senior_level(query: str) -> bool:
    query_terms = set(_query_terms(query))
    return bool(query_terms & SENIOR_QUERY_TERMS)


def _looks_like_senior_role(title: str) -> bool:
    normalized_title = title.lower()
    return any(term in normalized_title for term in SENIOR_TITLE_TERMS)


def _looks_like_software_role(title: str) -> bool:
    normalized_title = title.lower()
    if any(term in normalized_title for term in NON_SOFTWARE_TITLE_TERMS):
        return False

    return any(term in normalized_title for term in SOFTWARE_TITLE_TERMS)


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

    if "remote" in normalized_location:
        return True

    return any(term in normalized_location for term in US_LOCATION_TERMS)


def _matches_location(job_location: str | None, requested_location: str | None) -> bool:
    if not requested_location:
        return _is_default_us_market_location(job_location)

    if not job_location:
        return False

    requested = requested_location.lower().strip()
    location = job_location.lower()
    if requested == "remote":
        return "remote" in location and not _has_non_us_location(job_location)

    return requested in location


def _score_job(title: str, description: str, query: str) -> int:
    if _is_software_role_query(query):
        if not _looks_like_software_role(title):
            return 0
        if _looks_like_senior_role(title) and not _allows_senior_level(query):
            return 0

    terms = _query_terms(query)
    searchable_title = title.lower()
    searchable_description = description.lower()
    score = 0

    for term in terms:
        if term in searchable_title:
            score += 4
        if term in searchable_description:
            score += 1

    # Common student shorthand: SWE should strongly favor software engineering titles.
    if "swe" in query.lower() and "software" in searchable_title and "engineer" in searchable_title:
        score += 12

    return score


def _greenhouse_company_name(board_token: str) -> str:
    special_names = {
        "scaleai": "Scale AI",
    }
    return special_names.get(board_token, board_token.replace("-", " ").replace("_", " ").title())


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
        company=_greenhouse_company_name(board_token),
        title=title,
        location=location,
        description=description[:50_000],
        apply_url=apply_url,
        updated_at=str(raw_job.get("updated_at") or "").strip() or None,
    )


def _search_greenhouse_board(
    client: httpx.Client,
    board_token: str,
    query: str,
    location: str | None,
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

        score = _score_job(job.title, job.description, query)
        if score > 0:
            scored_jobs.append((score, job))

    return scored_jobs


def search_external_jobs(query: str, location: str | None = None, limit: int = 15) -> JobSearchResults:
    cleaned_query = query.strip()
    cleaned_location = location.strip() if location and location.strip() else None
    boards = _configured_greenhouse_boards()
    providers_searched = [f"greenhouse:{board}" for board in boards]
    warnings: list[str] = []
    scored_results: list[tuple[int, ExternalJobResult]] = []

    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        for board in boards:
            try:
                scored_results.extend(_search_greenhouse_board(client, board, cleaned_query, cleaned_location))
            except (httpx.HTTPError, ValueError) as exc:
                warnings.append(f"Greenhouse board '{board}' could not be searched: {exc.__class__.__name__}.")

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
        warnings.append(
            "No matching external jobs were found in the configured public job boards. Try a broader query, a different location, or configure more boards."
        )

    return JobSearchResults(
        query=cleaned_query,
        location=cleaned_location,
        providers_searched=providers_searched,
        results=ranked_results,
        warnings=warnings,
    )
