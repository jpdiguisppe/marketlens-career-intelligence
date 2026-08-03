"""Preserve proven search behavior while adding universal occupation fallback.

The existing search stack has product-specific rules for early-career programs,
regulated legal roles, healthcare aliases, grade-level teaching, sports industry
matching, and safe abbreviations. The universal catalog fills unsupported
occupation gaps; it does not replace those established paths.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Callable

from .occupation_catalog_runtime import (
    interpret_occupation_query,
    is_ambiguous_occupation_query,
    normalize_occupation_text,
)


@dataclass(frozen=True)
class LegacySearchFunctions:
    query_role_family: Callable[..., Any]
    query_job_function: Callable[..., Any]
    parse_intent: Callable[..., Any]
    query_terms: Callable[..., Any]
    matches_requested_role: Callable[..., Any]
    score_job: Callable[..., Any]
    source_search_terms: Callable[..., Any]
    search_external_jobs: Callable[..., Any]


_FORCE_UNIVERSAL_CONCEPTS = frozenset({"systems_application_engineer"})
_FORCE_UNIVERSAL_PHRASES = frozenset(
    {
        "application systems engineer",
        "system application engineer",
        "systems application engineer",
        "systems applications engineer",
    }
)
_LEGACY_PROBE_DEPTH: ContextVar[int] = ContextVar(
    "marketlens_universal_legacy_probe_depth",
    default=0,
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
        search_external_jobs=job_search.search_external_jobs,
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
    universal_search = job_search.search_external_jobs

    @lru_cache(maxsize=1_024)
    def cached_should_use_universal(query: str) -> bool:
        normalized = normalize_occupation_text(query)
        if is_ambiguous_occupation_query(query):
            return True
        if any(phrase in normalized for phrase in _FORCE_UNIVERSAL_PHRASES):
            return True

        # Several proven legacy adapters call the currently installed role-family
        # helpers internally. Mark this probe so those callbacks route directly
        # through the captured legacy stack instead of recursively probing again.
        probe_token = _LEGACY_PROBE_DEPTH.set(_LEGACY_PROBE_DEPTH.get() + 1)
        try:
            legacy_understands_query = (
                legacy.query_job_function(query) is not None
                or legacy.query_role_family(query) is not None
            )
        finally:
            _LEGACY_PROBE_DEPTH.reset(probe_token)
        if legacy_understands_query:
            return False

        core_tokens = [
            token
            for token in normalized.split()
            if token not in {"career", "careers", "entry", "intern", "internship", "job", "jobs", "role", "roles"}
        ]
        if len(core_tokens) == 1 and core_tokens[0].isalpha() and 2 <= len(core_tokens[0]) <= 5:
            # Unsupported short abbreviations need an explicit clarification or
            # unknown-abbreviation response rather than a provider fan-out.
            return True

        interpretation = interpret_occupation_query(query)
        if interpretation.status == "ambiguous":
            return True
        if interpretation.concept_key in _FORCE_UNIVERSAL_CONCEPTS:
            return True
        return interpretation.recognized

    def should_use_universal(query: str) -> bool:
        # A callback reached while probing the captured legacy stack must stay on
        # that stack. Keeping this check outside the cached function prevents a
        # temporary recursion-break decision from being cached as product logic.
        if _LEGACY_PROBE_DEPTH.get() > 0:
            return False
        return cached_should_use_universal(query)

    def query_role_family(query: str) -> Any:
        return universal_query_role_family(query) if should_use_universal(query) else legacy.query_role_family(query)

    def query_job_function(query: str) -> Any:
        return universal_query_job_function(query) if should_use_universal(query) else legacy.query_job_function(query)

    def parse_intent(query: str, location: str | None = None, level: str | None = None) -> Any:
        return universal_parse_intent(query, location, level) if should_use_universal(query) else legacy.parse_intent(query, location, level)

    def query_terms(query: str) -> Any:
        return universal_query_terms(query) if should_use_universal(query) else legacy.query_terms(query)

    def matches_requested_role(title: str, description: str, query: str, level: Any = None) -> bool:
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
        return universal_source_terms(query) if should_use_universal(query) else legacy.source_search_terms(query)

    def search_external_jobs(
        query: str,
        location: str | None = None,
        limit: int = 15,
        level: str | None = None,
    ) -> Any:
        # Universal search interprets before provider fan-out. Proven legacy
        # queries bypass it entirely so established behavior and latency remain
        # unchanged.
        function = universal_search if should_use_universal(query) else legacy.search_external_jobs
        return function(query=query, location=location, limit=limit, level=level)

    job_search._query_role_family = query_role_family
    job_search._query_job_function = query_job_function
    job_search.parse_job_search_intent = parse_intent
    job_search._query_terms = query_terms
    job_search._matches_requested_role = matches_requested_role
    job_search._score_job = score_job
    source_expansion._search_terms = source_search_terms
    job_search.search_external_jobs = search_external_jobs
    job_search._should_use_universal_occupation = should_use_universal
    job_search._UNIVERSAL_COMPATIBILITY_APPLIED = True
