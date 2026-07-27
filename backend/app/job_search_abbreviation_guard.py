"""Bound specific occupation abbreviations after query canonicalization.

Provider routing may use broad role families to find candidate boards, but these
exact abbreviations must still preserve occupation-level title precision.
"""

from __future__ import annotations

from typing import Any

from . import job_intent_engine as intent_engine
from .job_search_query_interpretation import canonicalize_job_query


STRICT_CANONICAL_TITLE_ALIASES: dict[str, frozenset[str]] = {
    "site reliability engineer": frozenset({"site reliability engineer", "sre"}),
    "machine learning engineer": frozenset({"machine learning engineer", "ml engineer", "mle"}),
    "artificial intelligence": frozenset({"artificial intelligence", "ai engineer", "ai research", "ai scientist"}),
    "security operations center analyst": frozenset({"security operations center analyst", "soc analyst"}),
    "business intelligence": frozenset({"business intelligence", "bi analyst", "bi developer", "bi engineer"}),
    "user experience": frozenset({"user experience", "ux designer", "ux researcher", "ux engineer"}),
    "user interface": frozenset({"user interface", "ui designer", "ui engineer", "ui developer"}),
    "quality assurance": frozenset({"quality assurance", "qa engineer", "qa analyst", "test engineer", "software tester"}),
    "systems administrator": frozenset({"systems administrator", "system administrator", "sysadmin"}),
    "database administrator": frozenset({"database administrator", "dba"}),
    "information security": frozenset({"information security", "infosec"}),
    "security operations": frozenset({"security operations", "secops"}),
}

SOFTWARE_ABBREVIATION_TITLES = {
    "site reliability engineer",
    "sre",
    "software development engineer",
    "sde",
}
DATA_ABBREVIATION_TITLES = {
    "machine learning engineer",
    "ml engineer",
    "mle",
    "artificial intelligence engineer",
    "ai engineer",
    "artificial intelligence scientist",
    "ai scientist",
}
CYBERSECURITY_ABBREVIATION_TITLES = {
    "security operations center analyst",
    "soc analyst",
    "security operations",
    "secops",
}
DESIGN_ABBREVIATION_TITLES = {
    "user experience designer",
    "ux designer",
    "ux researcher",
    "user interface designer",
    "ui designer",
}


def _extend_title_taxonomies(job_search: Any) -> None:
    job_search.SOFTWARE_TITLE_TERMS.update(SOFTWARE_ABBREVIATION_TITLES)
    job_search.ROLE_FAMILY_TITLE_TERMS["software"].update(SOFTWARE_ABBREVIATION_TITLES)
    intent_engine.SOFTWARE_TITLE_TERMS.update(SOFTWARE_ABBREVIATION_TITLES)
    intent_engine.ROLE_TITLE_TERMS["software"].update(SOFTWARE_ABBREVIATION_TITLES)

    job_search.DATA_TITLE_TERMS.update(DATA_ABBREVIATION_TITLES)
    job_search.ROLE_FAMILY_TITLE_TERMS["data"].update(DATA_ABBREVIATION_TITLES)
    intent_engine.DATA_TITLE_TERMS.update(DATA_ABBREVIATION_TITLES)
    intent_engine.ROLE_TITLE_TERMS["data"].update(DATA_ABBREVIATION_TITLES)

    job_search.CYBERSECURITY_TITLE_TERMS.update(CYBERSECURITY_ABBREVIATION_TITLES)
    job_search.ROLE_FAMILY_TITLE_TERMS["cybersecurity"].update(CYBERSECURITY_ABBREVIATION_TITLES)
    intent_engine.CYBERSECURITY_TITLE_TERMS.update(CYBERSECURITY_ABBREVIATION_TITLES)
    intent_engine.ROLE_TITLE_TERMS["cybersecurity"].update(CYBERSECURITY_ABBREVIATION_TITLES)

    job_search.DESIGN_TITLE_TERMS.update(DESIGN_ABBREVIATION_TITLES)
    job_search.ROLE_FAMILY_TITLE_TERMS["design"].update(DESIGN_ABBREVIATION_TITLES)
    intent_engine.DESIGN_TITLE_TERMS.update(DESIGN_ABBREVIATION_TITLES)
    intent_engine.ROLE_TITLE_TERMS["design"].update(DESIGN_ABBREVIATION_TITLES)


def _strict_aliases_for_query(query: str) -> frozenset[str] | None:
    canonical = canonicalize_job_query(query)
    for canonical_phrase, aliases in STRICT_CANONICAL_TITLE_ALIASES.items():
        if canonical_phrase in canonical:
            return aliases
    return None


def _title_passes_strict_abbreviation_guard(job_search: Any, title: str, query: str) -> bool:
    aliases = _strict_aliases_for_query(query)
    if aliases is None:
        return True
    return job_search._contains_any(title.lower(), set(aliases))


def apply_job_search_abbreviation_guard(job_search: Any) -> None:
    if getattr(job_search, "_ABBREVIATION_GUARD_APPLIED", False):
        return

    _extend_title_taxonomies(job_search)
    original_matches_requested_role = job_search._matches_requested_role
    original_score_job = job_search._score_job

    def matches_requested_role(
        title: str,
        description: str,
        query: str,
        level: Any = None,
    ) -> bool:
        if not _title_passes_strict_abbreviation_guard(job_search, title, query):
            return False
        return original_matches_requested_role(title, description, query, level)

    def score_job(
        title: str,
        description: str,
        query: str,
        level: str | None = None,
        company: str | None = None,
    ) -> int:
        if not _title_passes_strict_abbreviation_guard(job_search, title, query):
            return 0
        return original_score_job(
            title=title,
            description=description,
            query=query,
            level=level,
            company=company,
        )

    job_search._matches_requested_role = matches_requested_role
    job_search._score_job = score_job
    job_search._ABBREVIATION_GUARD_APPLIED = True
