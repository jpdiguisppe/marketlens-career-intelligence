from app.job_search import (
    _matches_location,
    _normalize_greenhouse_job,
    _normalize_lever_job,
    _score_job,
    clean_job_description,
)


def test_clean_job_description_removes_provider_html() -> None:
    cleaned = clean_job_description(
        '<div><p>Build <strong>Python</strong> APIs.</p><script>alert("x")</script></div>'
    )

    assert cleaned == "Build Python APIs."
    assert "<" not in cleaned
    assert "script" not in cleaned.lower()


def test_clean_job_description_removes_escaped_provider_html() -> None:
    cleaned = clean_job_description(
        '&lt;div&gt;&lt;p&gt;Build &lt;strong&gt;Python&lt;/strong&gt; APIs.&lt;/p&gt;&lt;/div&gt;'
    )

    assert cleaned == "Build Python APIs."
    assert "<" not in cleaned
    assert "&lt;" not in cleaned


def test_greenhouse_normalization_returns_plain_text_description() -> None:
    job = _normalize_greenhouse_job(
        "exampleco",
        {
            "id": 123,
            "title": "Software Engineer I",
            "absolute_url": "https://example.com/jobs/123",
            "location": {"name": "Remote, United States"},
            "content": "<p>Build <strong>Python</strong> services with SQL.</p>",
            "updated_at": "2026-07-01T00:00:00-04:00",
        },
    )

    assert job is not None
    assert job.description == "Build Python services with SQL."
    assert "<p>" not in job.description


def test_greenhouse_normalization_returns_plain_text_from_escaped_html() -> None:
    job = _normalize_greenhouse_job(
        "exampleco",
        {
            "id": 124,
            "title": "Software Engineer I",
            "absolute_url": "https://example.com/jobs/124",
            "location": {"name": "Remote, United States"},
            "content": "&lt;p&gt;Build &lt;strong&gt;Python&lt;/strong&gt; services.&lt;/p&gt;",
            "updated_at": "2026-07-01T00:00:00-04:00",
        },
    )

    assert job is not None
    assert job.description == "Build Python services."
    assert "<" not in job.description


def test_lever_normalization_returns_plain_text_description() -> None:
    job = _normalize_lever_job(
        "exampleco",
        {
            "id": "abc-123",
            "text": "Software Engineer Intern",
            "hostedUrl": "https://jobs.lever.co/exampleco/abc-123",
            "categories": {"location": "Remote, USA", "commitment": "Intern"},
            "description": "<p>Build <strong>Python</strong> services.</p>",
            "lists": [
                {"text": "Qualifications", "content": "<ul><li>0-1 years of experience.</li></ul>"},
            ],
            "additional": "<p>Apply with your resume.</p>",
            "createdAt": 1780000000000,
        },
    )

    assert job is not None
    assert job.source == "lever"
    assert job.title == "Software Engineer Intern"
    assert job.location == "Remote, USA"
    assert "Build Python services." in job.description
    assert "Qualifications" in job.description
    assert "<" not in job.description


def test_swe_query_rejects_non_software_titles_even_when_description_mentions_software() -> None:
    assert _score_job(
        title="Business Development Representative",
        description="Sell technical software products to engineering teams.",
        query="SWE",
    ) == 0

    assert _score_job(
        title="Software Engineer I",
        description="Build product features with Python and Java.",
        query="SWE",
    ) > 0


def test_swe_query_rejects_senior_level_roles_unless_requested() -> None:
    assert _score_job(
        title="Principal Software Engineer, Performance",
        description="Build high-scale infrastructure with Python.",
        query="SWE",
    ) == 0

    assert _score_job(
        title="Senior Software Engineer, Backend",
        description="Build backend systems with Python.",
        query="SWE",
    ) == 0

    assert _score_job(
        title="Senior Software Engineer, Backend",
        description="Build backend systems with Python.",
        query="senior SWE",
    ) > 0


def test_swe_query_rejects_numbered_mid_level_roles_by_default() -> None:
    assert _score_job(
        title="Software Engineer II, Backend",
        description="Build backend systems with Python and Java.",
        query="SWE",
    ) == 0

    assert _score_job(
        title="Software Engineer III, Backend",
        description="Build backend systems with Python and Java.",
        query="SWE",
    ) == 0

    assert _score_job(
        title="Software Engineer II, Backend",
        description="Build backend systems with Python and Java.",
        query="software engineer II",
    ) > 0


def test_swe_query_rejects_roles_requiring_too_many_years_by_default() -> None:
    assert _score_job(
        title="Forward Deployed Software Engineer",
        description="Required: 5+ years of software engineering experience with Python.",
        query="SWE",
    ) == 0

    assert _score_job(
        title="Software Engineer I",
        description="Required: 0-1 years of software engineering experience with Python.",
        query="SWE",
    ) > 0

    assert _score_job(
        title="Forward Deployed Software Engineer",
        description="Required: 5+ years of software engineering experience with Python.",
        query="senior SWE",
    ) > 0


def test_default_search_market_excludes_obvious_non_us_locations() -> None:
    assert _matches_location("Remote, Brazil", None) is False
    assert _matches_location("Beijing, China", None) is False
    assert _matches_location("Lisbon, Portugal", None) is False
    assert _matches_location("Remote, United States", None) is True
    assert _matches_location("Washington, DC", None) is True


def test_remote_filter_excludes_country_specific_non_us_remote_roles() -> None:
    assert _matches_location("Remote, Brazil", "Remote") is False
    assert _matches_location("Remote, United States", "Remote") is True
