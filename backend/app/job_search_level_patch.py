"""Final level semantics for ambiguous cross-sector titles."""

from __future__ import annotations

from typing import Any

from .job_search_correctness_patch import _is_non_senior_staff_title


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

        if level == "entry":
            return _is_unleveled_entry_compatible(
                job_search,
                title,
                description,
            )

        return False

    job_search._matches_level = _matches_level
    job_search._LEVEL_PATCH_APPLIED = True
