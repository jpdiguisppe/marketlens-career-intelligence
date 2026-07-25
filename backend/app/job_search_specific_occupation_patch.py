"""Precision guards discovered through live cross-sector search review."""

from __future__ import annotations

import re
from typing import Any

from . import job_search_intent_patch as intent_patch


ELEMENTARY_QUERY_TERMS = {
    "elementary school teacher",
    "elementary teacher",
    "primary school teacher",
    "primary teacher",
}
ELEMENTARY_TITLE_TERMS = {
    "elementary",
    "primary school",
    "grade school",
    "kindergarten",
    "k-5",
    "k–5",
}
ELEMENTARY_OCCUPATION_TERMS = {
    "teacher",
    "educator",
    "instructor",
}
ELEMENTARY_GRADE_PATTERN = re.compile(
    r"\b(?:grades?\s*[1-5]|[1-5](?:st|nd|rd|th)\s+grade)\b",
    re.IGNORECASE,
)

JOURNALISM_QUERY_TERMS = {
    "journalism",
    "journalist",
    "news reporter",
}
NON_JOURNALISM_EDITOR_TERMS = {
    "cinematic",
    "film editor",
    "motion graphics",
    "video editor",
    "video editing",
}
JOURNALISM_CONTEXT_TERMS = {
    "assignment desk",
    "assignment editor",
    "broadcast",
    "correspondent",
    "editorial",
    "journalism",
    "journalist",
    "news",
    "newsroom",
    "reporter",
}


def _query_contains_any(job_search: Any, query: str, terms: set[str]) -> bool:
    normalized = query.lower()
    return any(job_search._contains_phrase(normalized, term) for term in terms)


def _elementary_title_match(job_search: Any, title: str) -> bool:
    title_lower = title.lower()
    has_elementary_level = bool(
        job_search._contains_any(title_lower, ELEMENTARY_TITLE_TERMS)
        or ELEMENTARY_GRADE_PATTERN.search(title_lower)
    )
    has_teaching_occupation = job_search._contains_any(
        title_lower,
        ELEMENTARY_OCCUPATION_TERMS,
    )
    return has_elementary_level and has_teaching_occupation


def _is_non_journalism_editor_title(job_search: Any, title: str) -> bool:
    title_lower = title.lower()
    if not job_search._contains_any(title_lower, NON_JOURNALISM_EDITOR_TERMS):
        return False
    return not job_search._contains_any(title_lower, JOURNALISM_CONTEXT_TERMS)


def apply_job_search_specific_occupation_patch(job_search: Any) -> None:
    """Apply title-level precision without narrowing broad career searches."""

    if getattr(job_search, "_SPECIFIC_OCCUPATION_PATCH_APPLIED", False):
        return

    original_matches_requested_role = job_search._matches_requested_role
    original_occupation_match_strength = intent_patch._occupation_match_strength

    def _matches_requested_role(
        title: str,
        description: str,
        query: str,
        level: str | None = None,
    ) -> bool:
        # Grade-number titles such as "3rd Grade Teacher" are legitimate curated
        # aliases for elementary-school teaching even though they do not repeat
        # the word elementary. This branch must run before the generic specific-
        # occupation guard, which intentionally requires title-level evidence.
        if _query_contains_any(job_search, query, ELEMENTARY_QUERY_TERMS):
            return _elementary_title_match(job_search, title)

        base_match = original_matches_requested_role(
            title,
            description,
            query,
            level,
        )
        if not base_match:
            return False

        if (
            _query_contains_any(job_search, query, JOURNALISM_QUERY_TERMS)
            and _is_non_journalism_editor_title(job_search, title)
        ):
            return False

        return True

    def _occupation_match_strength(title: str, query: str) -> int:
        if (
            _query_contains_any(job_search, query, ELEMENTARY_QUERY_TERMS)
            and _elementary_title_match(job_search, title)
        ):
            # Exact elementary phrases receive the generic matcher’s stronger
            # score. Grade-level aliases receive a deliberately smaller but still
            # substantial score so exact titles continue to rank first.
            title_lower = title.lower()
            if job_search._contains_any(title_lower, ELEMENTARY_TITLE_TERMS):
                return max(45, original_occupation_match_strength(title, query))
            return 40
        return original_occupation_match_strength(title, query)

    job_search._matches_requested_role = _matches_requested_role
    intent_patch._occupation_match_strength = _occupation_match_strength
    job_search._SPECIFIC_OCCUPATION_PATCH_APPLIED = True
