from app.job_search import _score_job


def test_finance_internship_query_matches_finance_roles_not_generic_internships() -> None:
    assert _score_job(
        title="Finance Intern",
        description="Support budgeting, forecasting, and Excel-based financial reporting.",
        query="finance internship",
    ) > 0

    assert _score_job(
        title="Accounting Intern",
        description="Support month-end close, audit preparation, and financial statements.",
        query="finance internship",
    ) > 0

    assert _score_job(
        title="Investment Banking Intern",
        description="Build valuation models and support transaction analysis.",
        query="finance internship",
    ) > 0

    assert _score_job(
        title="Sales Intern",
        description="Work with customers and coordinate pipeline updates.",
        query="finance internship",
    ) == 0


def test_data_and_cybersecurity_queries_use_their_own_role_families() -> None:
    assert _score_job(
        title="Data Analyst Intern",
        description="Use SQL, dashboards, and analytics to support business decisions.",
        query="data analyst internship",
    ) > 0

    assert _score_job(
        title="Cybersecurity Intern",
        description="Support SOC triage, vulnerability tracking, and incident response.",
        query="cybersecurity internship",
    ) > 0

    assert _score_job(
        title="Software Engineer Intern",
        description="Build backend APIs with Python.",
        query="finance internship",
    ) == 0
