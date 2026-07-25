"""Final level semantics for ambiguous cross-sector titles."""

from __future__ import annotations

from typing import Any

from .job_search_correctness_patch import _is_non_senior_staff_title


def apply_job_search_level_patch(job_search: Any) -> None:
    """Prevent occupational uses of ``Staff`` from implying seniority."""

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
        return original_matches_level(title, description, level)

    job_search._matches_level = _matches_level
    job_search._LEVEL_PATCH_APPLIED = True
