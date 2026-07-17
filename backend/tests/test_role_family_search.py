from app.job_search import _score_job, search_external_jobs


def test_finance_internship_matches_finance_and_accounting_not_unrelated_internships() -> None:
    assert _score_job(
        title="Finance Intern",
        description="Support budgeting, forecasting, Excel reporting, and accounting close work.",
        query="finance internship",
        level="intern",
    ) > 0

    assert _score_job(
        title="Accounting Intern",
        description="Help with audit schedules, reconciliations, tax support, and month-end close.",
        query="finance internship",
        level="intern",
    ) > 0

    assert _score_job(
        title="Investment Banking Summer Analyst",
        description="Internship program focused on valuation, financial modeling, and banking clients.",
        query="finance internship",
        level="intern",
    ) > 0

    assert _score_job(
        title="Sales Intern",
        description="Prospect customers and support account executives.",
        query="finance internship",
        level="intern",
    ) == 0

    assert _score_job(
        title="Software Engineer Intern",
        description="Build APIs with Python and React.",
        query="finance internship",
        level="intern",
    ) == 0


def test_data_and_cybersecurity_role_families_filter_unrelated_internships() -> None:
    assert _score_job(
        title="Data Analyst Intern",
        description="Build dashboards and reports with SQL, Excel, and BI tools.",
        query="data analyst internship",
        level="intern",
    ) > 0

    assert _score_job(
        title="Cybersecurity Intern",
        description="Support SOC alerts, vulnerability management, and information security reporting.",
        query="cybersecurity internship",
        level="intern",
    ) > 0

    assert _score_job(
        title="Marketing Intern",
        description="Create social media campaigns and brand content.",
        query="data analyst internship",
        level="intern",
    ) == 0


def test_no_result_response_includes_transparency_and_fallback_links(monkeypatch) -> None:
    monkeypatch.setenv("JOB_SEARCH_GREENHOUSE_BOARDS", "definitely-not-a-real-board")
    monkeypatch.setenv("JOB_SEARCH_LEVER_SITES", "definitely-not-a-real-site")
    monkeypatch.setenv("JOB_SEARCH_REMOTEOK_ENABLED", "false")
    monkeypatch.setenv("JOB_SEARCH_REMOTIVE_ENABLED", "false")

    results = search_external_jobs(query="finance internship", location="Remote", level="intern", limit=5)

    assert results.results == []
    assert results.role_family == "finance"
    assert results.warnings
    assert "API-friendly public sources" in results.warnings[0]
    assert results.search_suggestions
    assert any(link.label == "Indeed search" for link in results.external_search_links)
    assert any(coverage.provider == "greenhouse" for coverage in results.source_coverage)
