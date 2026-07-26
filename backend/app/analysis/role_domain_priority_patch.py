"""Precision corrections for role-aware Smart Fit classification.

The stable role-aware layer predates the formal Milestone 8 evaluation suite.
These narrowly scoped corrections preserve its existing behavior while fixing
false role and capability evidence discovered by the benchmark.
"""

from __future__ import annotations

from dataclasses import replace

import app.analysis.role_aware as _role_aware

_ORIGINAL_CLASSIFY_JOB_DOMAIN = _role_aware._classify_job_domain


def _classify_job_domain_with_specific_title_priority(job_text: str) -> str | None:
    """Prefer an explicit function over a generic shared title token."""
    first_line = _role_aware._first_meaningful_line(job_text).lower()

    if any(
        _role_aware._contains_phrase(first_line, term)
        for term in _role_aware._ROLE_TERMS["sales_marketing"]
    ):
        return "sales_marketing"

    return _ORIGINAL_CLASSIFY_JOB_DOMAIN(job_text)


def _tighten_operations_capability_evidence() -> None:
    """Do not treat an unrelated database project as records/data-entry proof."""
    _role_aware._CAPABILITY_GROUPS = tuple(
        replace(
            capability,
            resume_terms=tuple(
                term for term in capability.resume_terms if term != "database"
            ),
        )
        if capability.title == "Records, data entry, and process accuracy"
        else capability
        for capability in _role_aware._CAPABILITY_GROUPS
    )


def install_role_domain_priority_patch() -> None:
    _role_aware._classify_job_domain = _classify_job_domain_with_specific_title_priority
    _tighten_operations_capability_evidence()
