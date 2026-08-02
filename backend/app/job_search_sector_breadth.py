"""Broad career-sphere interpretation layered after occupation-level matching."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .occupation_catalog import normalize_occupation_text


@dataclass(frozen=True)
class SectorQuery:
    canonical: str
    search_family: str
    title_terms: frozenset[str]


SECTOR_QUERIES: dict[str, SectorQuery] = {
    "accounting": SectorQuery(
        "accounting",
        "finance",
        frozenset({"accountant", "auditor", "bookkeeper", "payroll", "billing", "controller"}),
    ),
    "business": SectorQuery(
        "business",
        "operations",
        frozenset({"business analyst", "manager", "operations", "coordinator", "human resources", "recruiter"}),
    ),
    "economics": SectorQuery(
        "economics",
        "data",
        frozenset({"economist", "economic analyst", "research economist", "policy analyst"}),
    ),
    "education": SectorQuery(
        "education",
        "operations",
        frozenset({"teacher", "professor", "instructor", "librarian", "school counselor", "academic advisor", "education administrator"}),
    ),
    "engineering": SectorQuery(
        "engineering",
        "technology",
        frozenset({"engineer", "engineering technician", "engineering technologist", "architect", "surveyor", "drafter"}),
    ),
    "finance": SectorQuery(
        "finance",
        "finance",
        frozenset({"financial analyst", "finance", "accountant", "auditor", "loan officer", "investment", "banking"}),
    ),
    "healthcare": SectorQuery(
        "healthcare",
        "healthcare",
        frozenset({"nurse", "physician", "medical", "therapist", "pharmacist", "dental", "health"}),
    ),
    "law": SectorQuery(
        "law",
        "legal",
        frozenset({"attorney", "lawyer", "paralegal", "legal assistant", "law clerk", "court reporter"}),
    ),
    "law enforcement": SectorQuery(
        "law enforcement",
        "operations",
        frozenset({"police officer", "law enforcement officer", "detective", "correctional officer", "probation officer"}),
    ),
    "marketing": SectorQuery(
        "marketing",
        "marketing",
        frozenset({"marketing", "market research", "communications", "public relations", "brand", "content"}),
    ),
    "public safety": SectorQuery(
        "public safety",
        "operations",
        frozenset({"police officer", "firefighter", "emergency medical technician", "dispatcher", "security officer"}),
    ),
    "skilled trades": SectorQuery(
        "skilled trades",
        "operations",
        frozenset({"electrician", "plumber", "carpenter", "hvac", "welder", "machinist", "mechanic", "maintenance technician"}),
    ),
    "sports": SectorQuery(
        "sports",
        "marketing",
        frozenset({"coach", "sports analyst", "athletic", "sports marketing", "sports media", "recreation"}),
    ),
    "trades": SectorQuery(
        "skilled trades",
        "operations",
        frozenset({"electrician", "plumber", "carpenter", "hvac", "welder", "machinist", "mechanic", "maintenance technician"}),
    ),
}


def sector_for_query(query: str) -> SectorQuery | None:
    normalized = normalize_occupation_text(query)
    ignored = {
        "career", "careers", "entry", "entry level", "intern", "internship",
        "job", "jobs", "junior", "new grad", "role", "roles", "senior",
    }
    for phrase in sorted(ignored, key=len, reverse=True):
        normalized = re.sub(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return SECTOR_QUERIES.get(normalized)


def _title_matches_sector(job_search: Any, title: str, sector: SectorQuery) -> bool:
    return job_search._contains_any(title.lower(), set(sector.title_terms))


def apply_broad_sector_search(job_search: Any) -> None:
    if getattr(job_search, "_BROAD_SECTOR_SEARCH_APPLIED", False):
        return

    original_query_role_family = job_search._query_role_family
    original_query_job_function = job_search._query_job_function
    original_parse = job_search.parse_job_search_intent
    original_matches = job_search._matches_requested_role
    original_score = job_search._score_job
    original_search = job_search.search_external_jobs

    def query_role_family(query: str) -> Any:
        sector = sector_for_query(query)
        return sector.search_family if sector else original_query_role_family(query)

    def query_job_function(query: str) -> Any:
        sector = sector_for_query(query)
        return sector.search_family if sector else original_query_job_function(query)

    def parse_job_search_intent(
        query: str,
        location: str | None = None,
        level: str | None = None,
    ) -> Any:
        parsed = original_parse(query, location, level)
        sector = sector_for_query(query)
        if sector is None:
            return parsed
        return job_search.JobSearchIntent(
            query=query.strip(),
            job_function=sector.search_family,
            industry=parsed.industry,
            level=parsed.level,
            location=parsed.location,
        )

    def matches_requested_role(
        title: str,
        description: str,
        query: str,
        level: Any = None,
    ) -> bool:
        sector = sector_for_query(query)
        if sector is None:
            return original_matches(title, description, query, level)
        resolved_level = level or job_search.resolve_job_level(query, None)
        return _title_matches_sector(job_search, title, sector) and job_search._matches_level(
            title,
            description,
            resolved_level,
        )

    def score_job(
        title: str,
        description: str,
        query: str,
        level: str | None = None,
        company: str | None = None,
    ) -> int:
        sector = sector_for_query(query)
        if sector is None:
            return original_score(
                title=title,
                description=description,
                query=query,
                level=level,
                company=company,
            )
        resolved_level = job_search.resolve_job_level(query, level)
        if not _title_matches_sector(job_search, title, sector):
            return 0
        if not job_search._matches_level(title, description, resolved_level):
            return 0
        score = 24 + job_search._level_score_bonus(title, description, resolved_level)
        normalized_title = title.lower()
        score += 4 * sum(term in normalized_title for term in sector.title_terms)
        return score

    def search_external_jobs(
        query: str,
        location: str | None = None,
        limit: int = 15,
        level: str | None = None,
    ) -> Any:
        result = original_search(query=query, location=location, limit=limit, level=level)
        sector = sector_for_query(query)
        if sector is None:
            return result
        suggestions = list(result.search_suggestions)
        suggestions.insert(
            0,
            f"Interpreted '{query.strip()}' as the broad {sector.canonical} career sphere; use a specific occupation title for narrower results.",
        )
        warnings = list(result.warnings)
        if not result.results:
            warnings = [warning for warning in warnings if not warning.startswith("No matching")]
            warnings.insert(
                0,
                f"MarketLens understood the broad {sector.canonical} career sphere, but its configured public sources did not return a current matching posting for these filters.",
            )
        return job_search.JobSearchResults(
            query=query.strip(),
            location=result.location,
            level=result.level,
            providers_searched=result.providers_searched,
            results=result.results,
            warnings=warnings,
            role_family=sector.search_family,
            industry=result.industry,
            source_coverage=result.source_coverage,
            search_suggestions=suggestions,
            external_search_links=result.external_search_links,
        )

    job_search._query_role_family = query_role_family
    job_search._query_job_function = query_job_function
    job_search.parse_job_search_intent = parse_job_search_intent
    job_search._matches_requested_role = matches_requested_role
    job_search._score_job = score_job
    job_search.search_external_jobs = search_external_jobs
    job_search._BROAD_SECTOR_SEARCH_APPLIED = True
