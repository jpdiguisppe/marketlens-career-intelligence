from app.job_search import (
    _matches_location,
    _query_role_family,
    _remotive_search_terms,
    _score_job,
    _warnings_for_no_results,
)


def test_computer_science_blocks_clerical_data_entry_roles() -> None:
    assert _score_job(
        title="Entry Level Data Entry Clerk Fully Remote",
        description="Administrative assistant work, scheduling, records, Microsoft Office, and daily office operations.",
        query="computer science",
        level="entry",
    ) == 0

    assert _score_job(
        title="Data Entry Clerk Data Entry Specialist",
        description="Maintain records and enter customer information into spreadsheets.",
        query="computer science",
        level="entry",
    ) == 0


def test_specific_data_entry_query_is_admin_operations_not_data_analytics() -> None:
    assert _query_role_family("data entry") == "operations"
    assert _score_job(
        title="Entry Level Data Entry Clerk",
        description="Entry level administrative operations role entering records and maintaining office data.",
        query="data entry",
        level="entry",
    ) > 0


def test_computer_science_still_allows_real_entry_technical_roles() -> None:
    assert _score_job(
        title="Analytics Engineer",
        description="Entry level role. Build data pipelines with SQL and Python.",
        query="computer science",
        level="entry",
    ) > 0

    assert _score_job(
        title="Insider Threat Analyst",
        description="Entry level security role. Investigate security signals and suspicious account behavior.",
        query="computer science",
        level="entry",
    ) > 0


def test_entry_level_filter_still_requires_entry_evidence_for_technical_roles() -> None:
    assert _score_job(
        title="Analytics Engineer",
        description="Build data pipelines with SQL and Python.",
        query="computer science",
        level="entry",
    ) == 0


def test_data_analyst_requires_data_or_analytics_signal() -> None:
    assert _score_job(
        title="Compliance Analyst I",
        description="Review customer accounts and policy compliance.",
        query="data analyst",
        level="entry",
    ) == 0

    assert _score_job(
        title="Derivative Sales Analyst",
        description="Support sales workflows for derivatives products.",
        query="data analyst",
        level="entry",
    ) == 0

    assert _score_job(
        title="Data Entry Clerk",
        description="Enter records into spreadsheets and support office operations.",
        query="data analyst",
        level="entry",
    ) == 0

    assert _score_job(
        title="Data Analyst I",
        description="Analyze datasets with SQL and build dashboards.",
        query="data analyst",
        level="entry",
    ) > 0

    assert _score_job(
        title="Analytics Engineer",
        description="Entry level role. Build analytics models and data pipelines with Python and SQL.",
        query="data analyst",
        level="entry",
    ) > 0


def test_technical_searches_reject_sales_and_support_engineering_titles() -> None:
    assert _score_job(
        title="Sales Engineer",
        description="Entry level role partnering with customers and supporting sales demos.",
        query="SWE",
        level="entry",
    ) == 0

    assert _score_job(
        title="Solutions Engineer",
        description="Entry level role supporting customer demos and pre-sales workflows.",
        query="computer science",
        level="entry",
    ) == 0


def test_internship_matching_accepts_common_internship_variants() -> None:
    assert _score_job(
        title="Software Engineer Apprentice",
        description="Apprenticeship program building backend services with Python.",
        query="SWE",
        level="intern",
    ) > 0

    assert _score_job(
        title="Data Analyst Intern",
        description="Summer internship analyzing datasets with SQL and dashboards.",
        query="data analyst",
        level="intern",
    ) > 0

    assert _score_job(
        title="Sales Intern",
        description="Summer internship supporting sales outreach and customer calls.",
        query="data analyst",
        level="intern",
    ) == 0


def test_remote_filter_excludes_poland_specific_remote_roles() -> None:
    assert _matches_location("Remote Poland", "Remote") is False
    assert _matches_location("Remote (Poland)", "Philadelphia") is False


def test_internship_remotive_search_terms_are_internship_specific() -> None:
    software_terms = _remotive_search_terms("SWE", "intern")
    assert "software intern" in software_terms
    assert "software internship" in software_terms
    assert "intern" in software_terms

    data_terms = _remotive_search_terms("data analyst", "intern")
    assert "data analyst intern" in data_terms
    assert "analytics intern" in data_terms


def test_no_result_warning_uses_natural_accounting_internship_wording() -> None:
    warning = _warnings_for_no_results("accounting internship", "Remote", "intern", "finance")[0]
    assert "finance/accounting internship jobs" in warning
    assert "intern finance jobs" not in warning
