"""Apply the MarketLens job-intent engine to the provider search layer.

The fetch/normalization code still lives in app.job_search. This adapter keeps
that provider code stable while centralizing the actual product matching rules
in app.job_intent_engine.
"""

from __future__ import annotations

from typing import Any

from . import job_intent_engine as intent_engine


def apply_job_search_intent_patch(job_search: Any) -> None:
    """Patch app.job_search helpers with centralized intent behavior.

    This is intentionally idempotent. It lets Milestone 2 use a single reusable
    intent engine without rewriting the public-source provider integration in the
    same change.
    """

    if getattr(job_search, "_INTENT_PATCH_APPLIED", False):
        return

    original_query_role_family = job_search._query_role_family
    original_title_matches_role_family = job_search._title_matches_role_family
    original_matches_requested_role = job_search._matches_requested_role

    job_search.NON_US_LOCATION_TERMS.update(intent_engine.EXTRA_NON_US_LOCATION_TERMS)
    job_search.INTERN_TERMS.update(intent_engine.INTERN_TITLE_TERMS)

    def _query_role_family(query: str) -> str | None:
        intent = intent_engine.classify_search_intent(query)
        if intent.role_family in job_search.ROLE_FAMILY_TITLE_TERMS:
            return intent.role_family
        return original_query_role_family(query)

    def _title_matches_role_family(title: str, family: str) -> bool:
        if family in intent_engine.ENGINE_HANDLED_FAMILIES:
            return intent_engine.title_matches_search_family(title, family)
        return original_title_matches_role_family(title, family)

    def _matches_requested_role(title: str, description: str, query: str, level: str | None = None) -> bool:
        resolved_level = level or job_search.resolve_job_level(query)
        intent = intent_engine.classify_search_intent(query, resolved_level)
        if intent.role_family in intent_engine.ENGINE_HANDLED_FAMILIES:
            return intent_engine.job_matches_search_intent(title, description, intent)
        return original_matches_requested_role(title, description, query, level)

    def _remotive_search_terms(query: str, level: str) -> list[str | None]:
        return intent_engine.remotive_search_terms(query, level)

    def _warnings_for_no_results(query: str, location: str | None, level: str, role_family: str | None) -> list[str]:
        return [intent_engine.no_results_warning(query, location, level, role_family)]

    job_search._query_role_family = _query_role_family
    job_search._title_matches_role_family = _title_matches_role_family
    job_search._matches_requested_role = _matches_requested_role
    job_search._remotive_search_terms = _remotive_search_terms
    job_search._warnings_for_no_results = _warnings_for_no_results
    job_search._INTENT_PATCH_APPLIED = True
