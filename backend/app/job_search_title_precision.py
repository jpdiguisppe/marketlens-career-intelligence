"""Title-level precision guards discovered by the production occupation audit."""

from __future__ import annotations

import re
from typing import Any


_ACCOUNTANT_FALSE_POSITIVE_PATTERNS = (
    re.compile(r"\baccountant\s+partner\s+program\b"),
    re.compile(r"\bhead\s+of\s+accountant\b"),
)
_FINANCE_ANALYST_SIGNALS = (
    re.compile(r"\bfinance\b"),
    re.compile(r"\bfinancial\b"),
    re.compile(r"\btreasury\b"),
    re.compile(r"\binvestment\b"),
    re.compile(r"\bcredit\b"),
    re.compile(r"\bbudget\b"),
    re.compile(r"\bfp\s*a\b"),
)
_REGISTERED_NURSE_CONFLICTS = (
    re.compile(r"\blpn\b"),
    re.compile(r"\blvn\b"),
    re.compile(r"\blicensed\s+practical\s+nurse\b"),
    re.compile(r"\blicensed\s+vocational\s+nurse\b"),
    re.compile(r"\bnurse\s+practitioner\b"),
    re.compile(r"\bnurse\s+anesthetist\b"),
)


def title_satisfies_occupation_precision(
    title: str,
    query: str,
    occupation_runtime: Any,
) -> bool:
    """Require title evidence for production-observed occupation conflicts.

    The universal runtime still owns occupation interpretation. These bounded
    rules only prevent a related description from admitting a title that names
    a different occupation or a generic program.
    """

    interpretation = occupation_runtime.interpret_occupation_query(query)
    concept_key = interpretation.concept_key
    if interpretation.status != "recognized" or concept_key is None:
        return True

    normalized_title = occupation_runtime.normalize_occupation_text(title)

    if concept_key == "accountant":
        if not re.search(r"\baccountant\b", normalized_title):
            return False
        return not any(
            pattern.search(normalized_title)
            for pattern in _ACCOUNTANT_FALSE_POSITIVE_PATTERNS
        )

    if concept_key == "financial_analyst":
        return bool(
            re.search(r"\banalyst\b", normalized_title)
            and any(pattern.search(normalized_title) for pattern in _FINANCE_ANALYST_SIGNALS)
        )

    if concept_key == "registered_nurse":
        has_registered_nurse_title = bool(
            re.search(r"\bnurse\b", normalized_title)
            or re.search(r"\brn\b", normalized_title)
        )
        if not has_registered_nurse_title:
            return False
        return not any(
            pattern.search(normalized_title)
            for pattern in _REGISTERED_NURSE_CONFLICTS
        )

    if concept_key == "medical_assistant":
        return bool(re.search(r"\bmedical\s+assistant\b", normalized_title))

    return True


def apply_job_search_title_precision(
    job_search: Any,
    occupation_runtime: Any,
) -> None:
    """Install title-only precision after the complete established search stack."""

    if getattr(job_search, "_TITLE_PRECISION_APPLIED", False):
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
        if not title_satisfies_occupation_precision(
            title,
            query,
            occupation_runtime,
        ):
            return False
        return original_matches_requested_role(title, description, query, level)

    def score_job(
        title: str,
        description: str,
        query: str,
        level: str | None = None,
        company: str | None = None,
    ) -> int:
        if not title_satisfies_occupation_precision(
            title,
            query,
            occupation_runtime,
        ):
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
        result = original_search(
            query=query,
            location=location,
            limit=limit,
            level=level,
        )
        filtered_results = [
            posting
            for posting in result.results
            if title_satisfies_occupation_precision(
                posting.title,
                query,
                occupation_runtime,
            )
        ]
        if len(filtered_results) == len(result.results):
            return result

        warnings = list(result.warnings)
        removed_count = len(result.results) - len(filtered_results)
        warnings.insert(
            0,
            f"MarketLens removed {removed_count} posting(s) whose titles named a different occupation or a generic program.",
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
    job_search.title_satisfies_occupation_precision = (
        lambda title, query: title_satisfies_occupation_precision(
            title,
            query,
            occupation_runtime,
        )
    )
    job_search._TITLE_PRECISION_APPLIED = True


__all__ = [
    "apply_job_search_title_precision",
    "title_satisfies_occupation_precision",
]
