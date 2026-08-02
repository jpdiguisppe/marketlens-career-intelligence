"""Preserve proven search behavior while adding universal occupation fallback.

The existing search stack has product-specific rules for early-career programs,
regulated legal roles, healthcare aliases, grade-level teaching, sports industry
matching, and safe abbreviations. The universal catalog fills unsupported
occupation gaps; it does not replace those established paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Callable

from . import occupation_catalog as catalog


@dataclass(frozen=True)
class LegacySearchFunctions:
    query_role_family: Callable[..., Any]
    query_job_function: Callable[..., Any]
    parse_intent: Callable[..., Any]
    query_terms: Callable[..., Any]
    matches_requested_role: Callable[..., Any]
    score_job: Callable[..., Any]
    source_search_terms: Callable[..., Any]


_FORCE_UNIVERSAL_CONCEPTS = frozenset({"systems_application_engineer"})
_FORCE_UNIVERSAL_PHRASES = frozenset(
    {
        "application systems engineer",
        "system application engineer",
        "systems application engineer",
        "systems applications engineer",
    }
)


def capture_legacy_search_functions(job_search: Any, source_expansion: Any) -> None:
    if getattr(job_search, "_LEGACY_SEARCH_FUNCTIONS", None) is not None:
        return
    job_search._LEGACY_SEARCH_FUNCTIONS = LegacySearchFunctions(
        query_role_family=job_search._query_role_family,
        query_job_function=job_search._query_job_function,
        parse_intent=job_search.parse_job_search_intent,
        query_terms=job_search._query_terms,
        matches_requested_role=job_search._matches_requested_role,
        score_job=job_search._score_job,
        source_search_terms=source_expansion._search_terms,
    )


def apply_universal_compatibility(job_search: Any, source_expansion: Any) -> None:
    if getattr(job_search, "_UNIVERSAL_COMPATIBILITY_APPLIED", False):
        return
    legacy = getattr(job_search, "_LEGACY_SEARCH_FUNCTIONS", None)
    if not isinstance(legacy, LegacySearchFunctions):
        raise RuntimeError("Legacy search functions must be captured before universal search is applied.")

    universal_query_role_family = job_search._query_role_family
    universal_query_job_function = job_search._query_job_function
    universal_parse_intent = job_search.parse_job_search_intent
    universal_query_terms = job_search._query_terms
    universal_matches = job_search._matches_requested_role
    universal_score = job_search._score_job
    universal_source_terms = source_expansion._search_terms

    @lru_cache(maxsize=1_024)
    def should_use_universal(query: str) -> bool:
        normalized = catalog.normalize_occupation_text(query)
        if catalog._pure_acronym(query) is not None:
            return True
        if any(phrase in normalized for phrase in _FORCE_UNIVERSAL_PHRASES):
            return True

        # Fast path: the established engine already understands this role. Avoid
        # walking the larger occupation catalog for every benchmark candidate.
        if legacy.query_job_function(query) is not None or legacy.query_role_family(query) is not None:
            return False

        interpretation = catalog.interpret_occupation_query(query)
        if interpretation.status == "ambiguous":
            return True
        if interpretation.concept_key in _FORCE_UNIVERSAL_CONCEPTS:
            return True
        return interpretation.recognized

    def query_role_family(query: str) -> Any:
        return (
            universal_query_role_family(query)
            if should_use_universal(query)
            else legacy.query_role_family(query)
        )

    def query_job_function(query: str) -> Any:
        return (
            universal_query_job_function(query)
            if should_use_universal(query)
            else legacy.query_job_function(query)
        )

    def parse_intent(
        query: str,
        location: str | None = None,
        level: str | None = None,
    ) -> Any:
        return (
            universal_parse_intent(query, location, level)
            if should_use_universal(query)
            else legacy.parse_intent(query, location, level)
        )

    def query_terms(query: str) -> Any:
        return (
            universal_query_terms(query)
            if should_use_universal(query)
            else legacy.query_terms(query)
        )

    def matches_requested_role(
        title: str,
        description: str,
        query: str,
        level: Any = None,
    ) -> bool:
        function = universal_matches if should_use_universal(query) else legacy.matches_requested_role
        return function(title, description, query, level)

    def score_job(
        title: str,
        description: str,
        query: str,
        level: str | None = None,
        company: str | None = None,
    ) -> int:
        function = universal_score if should_use_universal(query) else legacy.score_job
        return function(
            title=title,
            description=description,
            query=query,
            level=level,
            company=company,
        )

    def source_search_terms(query: str) -> Any:
        return (
            universal_source_terms(query)
            if should_use_universal(query)
            else legacy.source_search_terms(query)
        )

    job_search._query_role_family = query_role_family
    job_search._query_job_function = query_job_function
    job_search.parse_job_search_intent = parse_intent
    job_search._query_terms = query_terms
    job_search._matches_requested_role = matches_requested_role
    job_search._score_job = score_job
    source_expansion._search_terms = source_search_terms
    job_search._should_use_universal_occupation = should_use_universal
    job_search._UNIVERSAL_COMPATIBILITY_APPLIED = True
