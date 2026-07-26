"""Precision patch for role-domain title classification.

Generic titles such as ``Coordinator`` should not override a more specific job
function that appears in the same title. This module keeps the existing role
classifier intact while giving explicit sales/marketing title evidence priority
before the generic operations/administration fallback.
"""

from __future__ import annotations

import app.analysis.role_aware as _role_aware

_ORIGINAL_CLASSIFY_JOB_DOMAIN = _role_aware._classify_job_domain


def _classify_job_domain_with_specific_title_priority(job_text: str) -> str | None:
    first_line = _role_aware._first_meaningful_line(job_text).lower()

    if any(
        _role_aware._contains_phrase(first_line, term)
        for term in _role_aware._ROLE_TERMS["sales_marketing"]
    ):
        return "sales_marketing"

    return _ORIGINAL_CLASSIFY_JOB_DOMAIN(job_text)


def install_role_domain_priority_patch() -> None:
    _role_aware._classify_job_domain = _classify_job_domain_with_specific_title_priority
