from __future__ import annotations

from app import job_search


def test_unknown_acronym_with_search_modifier_short_circuits() -> None:
    result = job_search.search_external_jobs("XYZ jobs", level="any")

    assert result.results == []
    assert result.providers_searched == []
    assert result.source_coverage == []
    assert any("XYZ" in warning for warning in result.warnings)
    assert any("could not safely identify" in warning.lower() for warning in result.warnings)


def test_accountant_partner_program_is_not_an_accountant_job() -> None:
    assert not job_search._matches_requested_role(
        "Head of Accountant Partner Program",
        "Lead a partner enablement and go-to-market program.",
        "accountant",
        "any",
    )
    assert job_search._score_job(
        "Head of Accountant Partner Program",
        "Lead a partner enablement and go-to-market program.",
        "accountant",
        "any",
    ) == 0


def test_real_accountant_titles_remain_valid() -> None:
    assert job_search._matches_requested_role(
        "Senior Accountant, Capital Markets",
        "Prepare reconciliations, financial statements, and accounting reports.",
        "accountant",
        "any",
    )
    assert job_search._score_job(
        "Staff Accountant",
        "Own general ledger entries, reconciliations, and month-end close.",
        "accountant",
        "any",
    ) > 0
