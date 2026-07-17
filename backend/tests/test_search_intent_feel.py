from app.job_search import _score_job


def test_swe_search_is_narrower_than_computer_science_search() -> None:
    analytics_description = "Entry-level role building analytics models, dashboards, and data pipelines with SQL."

    assert _score_job(
        title="Analytics Engineer",
        description=analytics_description,
        query="SWE",
        level="entry",
    ) == 0

    assert _score_job(
        title="Analytics Engineer",
        description=analytics_description,
        query="computer science jobs",
        level="entry",
    ) > 0


def test_swe_still_accepts_real_entry_level_software_roles() -> None:
    assert _score_job(
        title="Associate Software Engineer",
        description="Entry-level role building Python APIs with SQL and Git.",
        query="SWE",
        level="entry",
    ) > 0

    assert _score_job(
        title="Junior Backend Developer",
        description="Entry-level role building backend services with Python and SQL.",
        query="SWE",
        level="entry",
    ) > 0


def test_computer_science_search_accepts_adjacent_technical_roles() -> None:
    assert _score_job(
        title="Data Engineer I",
        description="Entry-level role building data pipelines with Python and SQL.",
        query="computer science jobs",
        level="entry",
    ) > 0

    assert _score_job(
        title="Cybersecurity Analyst I",
        description="Entry-level role triaging security alerts and vulnerabilities.",
        query="computer science jobs",
        level="entry",
    ) > 0
