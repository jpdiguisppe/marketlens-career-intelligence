"""Small production-discovered precision guards for job search.

These guards intentionally sit after the established search stack. They cover
only failures observed in production and do not broaden occupation matching.
"""

from __future__ import annotations

import re
from typing import Any


_SHORT_ACRONYM = re.compile(r"^[a-z]{2,5}$")
_SEARCH_MODIFIERS = frozenset(
    {
        "career",
        "careers",
        "entry",
        "entry-level",
        "grad",
        "graduate",
        "intern",
        "internship",
        "internships",
        "job",
        "jobs",
        "junior",
        "level",
        "mid",
        "new",
        "opening",
        "openings",
        "position",
        "positions",
        "role",
        "roles",
        "senior",
        "sr",
        "staff",
    }
)
_ACCOUNTANT_PROGRAM_PATTERNS = (
    re.compile(r"\baccountant\s+partner\s+program\b"),
    re.compile(r"\bhead\s+of\s+accountant\b"),
)


def _unknown_short_acronym(query: str, occupation_runtime: Any) -> str | None:
    normalized = occupation_runtime.normalize_occupation_text(query)
    core_tokens = [
        token for token in normalized.split() if token not in _SEARCH_MODIFIERS
    ]
    if len(core_tokens) != 1:
        return None
    acronym = core_tokens[0]
    return acronym if _SHORT_ACRONYM.fullmatch(acronym) else None


def _is_accountant_program_title(
    title: str,
    query: str,
    occupation_runtime: Any,
) -> bool:
    interpretation = occupation_runtime.interpret_occupation_query(query)
    if interpretation.concept_key != "accountant":
        return False
    normalized_title = occupation_runtime.normalize_occupation_text(title)
    return any(pattern.search(normalized_title) for pattern in _ACCOUNTANT_PROGRAM_PATTERNS)


def _unknown_acronym_result(
    job_search: Any,
    query: str,
    location: str | None,
    level: str | None,
    acronym: str,
) -> Any:
    resolved_level = job_search.resolve_job_level(query, level)
    return job_search.JobSearchResults(
        query=query.strip(),
        location=location.strip() if location and location.strip() else None,
        level=resolved_level,
        providers_searched=[],
        results=[],
        warnings=[
            f"MarketLens could not safely identify the occupation abbreviation '{acronym.upper()}'. "
            "No providers were searched because guessing could return unrelated jobs."
        ],
        role_family=None,
        industry=None,
        source_coverage=[],
        search_suggestions=[
            "Spell out the complete occupation title.",
            "Include a discipline or function, such as 'civil engineer', 'financial analyst', or 'registered nurse'.",
            "Manual Smart Fit comparison still works for any posting copied from another job board.",
        ],
        external_search_links=[],
    )


def apply_job_search_production_hotfix(
    job_search: Any,
    occupation_runtime: Any,
) -> None:
    """Install bounded guards for production-observed search regressions."""

    if getattr(job_search, "_PRODUCTION_SEARCH_HOTFIX_APPLIED", False):
        return

    original_matches_requested_role = job_search._matches_requested_role
    original_score_job = job_search._score_job
    original_search = job_search.search_external_jobs

    def matches_requested_role(
        title: str,
        description: str,
        query: str,
        level: Any = None,
    ) -> bool:
        if _is_accountant_program_title(title, query, occupation_runtime):
            return False
        return original_matches_requested_role(title, description, query, level)

    def score_job(
        title: str,
        description: str,
        query: str,
        level: str | None = None,
        company: str | None = None,
    ) -> int:
        if _is_accountant_program_title(title, query, occupation_runtime):
            return 0
        return original_score_job(
            title=title,
            description=description,
            query=query,
            level=level,
            company=company,
        )

    def search_external_jobs(
        query: str,
        location: str | None = None,
        limit: int = 15,
        level: str | None = None,
    ) -> Any:
        interpretation = occupation_runtime.interpret_occupation_query(query)
        acronym = _unknown_short_acronym(query, occupation_runtime)
        if interpretation.status == "unrecognized" and acronym is not None:
            return _unknown_acronym_result(
                job_search,
                query,
                location,
                level,
                acronym,
            )

        result = original_search(
            query=query,
            location=location,
            limit=limit,
            level=level,
        )
        filtered_results = [
            posting
            for posting in result.results
            if not _is_accountant_program_title(
                posting.title,
                query,
                occupation_runtime,
            )
        ]
        if len(filtered_results) == len(result.results):
            return result

        warnings = list(result.warnings)
        if not filtered_results:
            warnings.insert(
                0,
                "MarketLens removed postings where 'accountant' described a partner program "
                "rather than an accounting occupation. No current matching accounting posting remained.",
            )

        return job_search.JobSearchResults(
            query=result.query,
            location=result.location,
            level=result.level,
            providers_searched=result.providers_searched,
            results=filtered_results,
            warnings=warnings,
            role_family=result.role_family,
            industry=result.industry,
            source_coverage=result.source_coverage,
            search_suggestions=result.search_suggestions,
            external_search_links=result.external_search_links,
        )

    job_search._matches_requested_role = matches_requested_role
    job_search._score_job = score_job
    job_search.search_external_jobs = search_external_jobs
    job_search._PRODUCTION_SEARCH_HOTFIX_APPLIED = True


__all__ = ["apply_job_search_production_hotfix"]
