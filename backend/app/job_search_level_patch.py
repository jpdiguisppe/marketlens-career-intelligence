"""Final level semantics for ambiguous cross-sector titles."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

from . import job_search_intent_patch as intent_patch
from .job_search_correctness_patch import (
    BROAD_FAMILY_ONLY_TERMS,
    _is_non_senior_staff_title,
)


QUALITATIVE_EXPERIENCE_REQUIREMENTS = {
    "extensive experience",
    "significant experience",
    "substantial experience",
    "several years of experience",
    "many years of experience",
    "seasoned professional",
    "experienced professional",
    "proven track record in a senior",
}

_ALLOW_UNLEVELED_ENTRY: ContextVar[bool] = ContextVar(
    "marketlens_allow_unleveled_entry",
    default=False,
)


def _is_specific_occupation_query(query: str) -> bool:
    normalized = " ".join(query.lower().split()).strip()
    return bool(
        normalized
        and normalized not in BROAD_FAMILY_ONLY_TERMS
        and intent_patch._should_apply_specific_occupation_guard(query)
    )


def _is_unleveled_entry_compatible(
    job_search: Any,
    title: str,
    description: str,
) -> bool:
    """Accept plain occupation titles when no experience evidence contradicts entry."""

    if job_search._looks_like_intern_role(title, description):
        return False
    if job_search._title_has_senior_signal(title) or job_search._title_has_mid_signal(title):
        return False
    if job_search._max_required_years(description) != 0:
        return False

    searchable = f"{title} {description}".lower()
    if job_search._contains_any(searchable, QUALITATIVE_EXPERIENCE_REQUIREMENTS):
        return False

    # An unqualified title such as Teacher, Electrical Engineer, Policy Analyst,
    # Lab Technician, or Graphic Designer is entry-compatible when the posting
    # supplies no contrary seniority or experience requirement. This does not
    # declare the role junior; it keeps an unknown-but-compatible role visible
    # below explicitly labeled entry jobs instead of producing a false zero.
    return True


def apply_job_search_level_patch(job_search: Any) -> None:
    """Handle occupational ``Staff`` titles and unlabeled entry-compatible work."""

    if getattr(job_search, "_LEVEL_PATCH_APPLIED", False):
        return

    original_matches_level = job_search._matches_level
    original_score_job = job_search._score_job

    def _matches_level(title: str, description: str, level: str) -> bool:
        # Staff Accountant, Staff Reporter, Staff Pharmacist, and similar titles
        # are common occupational levels rather than universal seniority signals.
        # Explicit senior/lead language or substantial experience still passes
        # through the existing level classifier.
        if level == "senior" and _is_non_senior_staff_title(
            job_search,
            title,
            description,
        ):
            return False

        if original_matches_level(title, description, level):
            return True

        if level == "entry" and _ALLOW_UNLEVELED_ENTRY.get():
            return _is_unleveled_entry_compatible(
                job_search,
                title,
                description,
            )

        return False

    def _score_job(
        title: str,
        description: str,
        query: str,
        level: str | None = None,
        company: str | None = None,
    ) -> int:
        allow_unleveled_entry = (
            job_search.resolve_job_level(query, level) == "entry"
            and _is_specific_occupation_query(query)
        )
        token = _ALLOW_UNLEVELED_ENTRY.set(allow_unleveled_entry)
        try:
            return original_score_job(
                title=title,
                description=description,
                query=query,
                level=level,
                company=company,
            )
        finally:
            _ALLOW_UNLEVELED_ENTRY.reset(token)

    job_search._matches_level = _matches_level
    job_search._score_job = _score_job
    job_search._LEVEL_PATCH_APPLIED = True
