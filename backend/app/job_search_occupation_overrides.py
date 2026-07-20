"""Resolve occupation queries that collide with broad role-family keywords.

The general intent engine handles known role families and unknown occupations.
Some real occupation names contain a word that also belongs to a broad family;
for example, ``court reporting`` contains ``reporting``, which otherwise looks
like a data/analytics query. These explicit phrase overrides keep the complete
occupation meaning intact instead of classifying from one token.
"""

from __future__ import annotations

import re
from typing import Any


OCCUPATION_TITLE_OVERRIDES: dict[str, set[str]] = {
    "court reporting": {"court reporter", "court reporting"},
}


def _contains_phrase(value: str, phrase: str) -> bool:
    escaped_words = [
        re.escape(part)
        for part in re.split(r"[\s,./()\-]+", phrase.strip().lower())
        if part
    ]
    if not escaped_words:
        return False
    separator = r"[\s,./()\-]+"
    pattern = r"(?<![a-z0-9])" + separator.join(escaped_words) + r"(?![a-z0-9])"
    return bool(re.search(pattern, value.lower()))


def _occupation_override(query: str) -> set[str] | None:
    normalized = query.lower().strip()
    for phrase, title_terms in OCCUPATION_TITLE_OVERRIDES.items():
        if _contains_phrase(normalized, phrase):
            return title_terms
    return None


def apply_job_search_occupation_overrides(job_search: Any) -> None:
    """Apply narrow phrase-first overrides after the main intent patch."""

    if getattr(job_search, "_OCCUPATION_OVERRIDES_APPLIED", False):
        return

    original_query_role_family = job_search._query_role_family
    original_matches_requested_role = job_search._matches_requested_role

    def _query_role_family(query: str) -> str | None:
        if _occupation_override(query) is not None:
            return None
        return original_query_role_family(query)

    def _matches_requested_role(
        title: str,
        description: str,
        query: str,
        level: str | None = None,
    ) -> bool:
        title_terms = _occupation_override(query)
        if title_terms is not None:
            return any(_contains_phrase(title, term) for term in title_terms)
        return original_matches_requested_role(title, description, query, level)

    job_search._query_role_family = _query_role_family
    job_search._matches_requested_role = _matches_requested_role
    job_search._OCCUPATION_OVERRIDES_APPLIED = True
