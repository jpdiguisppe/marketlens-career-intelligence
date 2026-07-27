"""Bound specific occupation abbreviations after query canonicalization.

Provider routing may use broad role families to find candidate boards, but these
exact abbreviations must still preserve occupation-level title precision.
"""

from __future__ import annotations

import re
from typing import Any

from . import job_intent_engine as intent_engine
from . import job_search_query_interpretation as query_interpretation
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

PROVIDER_FAMILY_HINTS: tuple[tuple[str, str], ...] = (
    ("artificial intelligence", "data"),
    ("machine learning engineer", "data"),
    ("quality assurance", "software"),
    ("software development engineer", "software"),
)

SOFTWARE_ABBREVIATION_TITLES = {
    "site reliability engineer",
    "sre",
    "software development engineer",
    "sde",
    "quality assurance engineer",
    "qa engineer",
    "qa analyst",
    "test engineer",
    "software tester",
}
DATA_ABBREVIATION_TITLES = {
    "machine learning engineer",
    "ml engineer",
    "mle",
    "artificial intelligence",
    "artificial intelligence engineer",
    "ai engineer",
    "artificial intelligence scientist",
    "ai scientist",
    "database administrator",
    "dba",
}
CYBERSECURITY_ABBREVIATION_TITLES = {
    "security operations center analyst",
    "soc analyst",
    "security operations",
    "secops",
}
DESIGN_ABBREVIATION_TITLES = {
    "user experience",
    "user experience designer",
    "ux designer",
    "ux researcher",
    "user interface",
    "user interface designer",
    "ui designer",
}
TECHNOLOGY_ADJACENT_ABBREVIATION_TITLES = {
    "systems administrator",
    "system administrator",
    "sysadmin",
}

_ALLOWED_REMAINDER_TOKENS = frozenset(
    {
        "analyst",
        "associate",
        "career",
        "careers",
        "developer",
        "engineer",
        "entry",
        "grad",
        "graduate",
        "intern",
        "internship",
        "job",
        "jobs",
        "junior",
        "lead",
        "level",
        "mid",
        "opening",
        "openings",
        "position",
        "positions",
        "principal",
        "research",
        "role",
        "roles",
        "scientist",
        "senior",
        "staff",
    }
)


def _extend_family_hints() -> None:
    existing = set(query_interpretation.CANONICAL_FAMILY_HINTS)
    query_interpretation.CANONICAL_FAMILY_HINTS = tuple(
        [*query_interpretation.CANONICAL_FAMILY_HINTS]
        + [hint for hint in PROVIDER_FAMILY_HINTS if hint not in existing]
    )


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

    intent_engine.TECHNOLOGY_ADJACENT_TITLE_TERMS.update(
        TECHNOLOGY_ADJACENT_ABBREVIATION_TITLES
    )
    job_search.ROLE_FAMILY_TITLE_TERMS["technology"].update(
        TECHNOLOGY_ADJACENT_ABBREVIATION_TITLES
    )


def _strict_rule_for_query(
    query: str,
) -> tuple[str, frozenset[str]] | None:
    canonical = canonicalize_job_query(query)
    for canonical_phrase, aliases in sorted(
        STRICT_CANONICAL_TITLE_ALIASES.items(),
        key=lambda item: (-len(item[0].split()), -len(item[0]), item[0]),
    ):
        if canonical_phrase in canonical:
            return canonical_phrase, aliases
    return None


def _title_passes_strict_abbreviation_guard(job_search: Any, title: str, query: str) -> bool:
    rule = _strict_rule_for_query(query)
    if rule is None:
        return True
    _, aliases = rule
    return job_search._contains_any(title.lower(), set(aliases))


def _is_pure_strict_occupation_query(query: str) -> bool:
    rule = _strict_rule_for_query(query)
    if rule is None:
        return False
    canonical_phrase, _ = rule
    canonical = canonicalize_job_query(query)
    remainder = canonical.replace(canonical_phrase, " ", 1)
    tokens = set(re.findall(r"[a-z0-9]+", remainder.lower()))
    return tokens.issubset(_ALLOWED_REMAINDER_TOKENS)


def _exact_alias_fallback_score(
    job_search: Any,
    title: str,
    description: str,
    query: str,
    level: str | None,
) -> int:
    if not _is_pure_strict_occupation_query(query):
        return 0
    resolved_level = job_search.resolve_job_level(query, level)
    if not job_search._matches_level(title, description, resolved_level):
        return 0
    return 30 + job_search._level_score_bonus(title, description, resolved_level)


def apply_job_search_abbreviation_guard(job_search: Any) -> None:
    if getattr(job_search, "_ABBREVIATION_GUARD_APPLIED", False):
        return

    _extend_family_hints()
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
        if original_matches_requested_role(title, description, query, level):
            return True
        return _exact_alias_fallback_score(
            job_search,
            title,
            description,
            query,
            level,
        ) > 0

    def score_job(
        title: str,
        description: str,
        query: str,
        level: str | None = None,
        company: str | None = None,
    ) -> int:
        if not _title_passes_strict_abbreviation_guard(job_search, title, query):
            return 0
        score = original_score_job(
            title=title,
            description=description,
            query=query,
            level=level,
            company=company,
        )
        if score > 0:
            return score
        return _exact_alias_fallback_score(
            job_search,
            title,
            description,
            query,
            level,
        )

    job_search._matches_requested_role = matches_requested_role
    job_search._score_job = score_job
    job_search._ABBREVIATION_GUARD_APPLIED = True
