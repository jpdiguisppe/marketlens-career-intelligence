from app.job_search import (
    _matches_location,
    _normalize_greenhouse_job,
    _normalize_lever_job,
    _normalize_remoteok_job,
    _normalize_remotive_job,
    _score_job,
    clean_job_description,
    resolve_job_level,
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
    assert job.source == "greenhouse"


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
        "github",
        {
            "id": "abc123",
            "text": "Software Engineer I",
            "hostedUrl": "https://jobs.lever.co/github/abc123",
            "categories": {
                "location": "Remote - United States",
                "allLocations": ["Remote - United States"],
            },
            "descriptionPlain": "Build Python services.",
            "lists": [
                {
                    "text": "Requirements",
                    "content": "<ul><li>Use SQL and REST APIs.</li></ul>",
                }
            ],
            "createdAt": 1780000000000,
        },
    )

    assert job is not None
    assert job.id == "lever:github:abc123"
    assert job.source == "lever"
    assert job.company == "GitHub"
    assert job.location == "Remote - United States"
    assert "Build Python services." in job.description
    assert "Use SQL and REST APIs." in job.description
    assert "<li>" not in job.description


def test_remoteok_normalization_returns_remote_plain_text_description() -> None:
    job = _normalize_remoteok_job(
        {
            "id": 456,
            "position": "Junior Software Engineer",
            "company": "Example Remote Co",
            "url": "https://remoteok.com/remote-jobs/456",
            "location": "Worldwide",
            "description": "<p>Build <strong>Python</strong> APIs.</p>",
            "date": "2026-07-17T00:00:00Z",
        }
    )

    assert job is not None
    assert job.id == "remoteok:456"
    assert job.source == "remoteok"
    assert job.company == "Example Remote Co"
    assert job.location == "Remote (Worldwide)"
    assert job.description == "Build Python APIs."
    assert job.apply_url == "https://remoteok.com/remote-jobs/456"


def test_remotive_normalization_returns_remote_plain_text_description() -> None:
    job = _normalize_remotive_job(
        {
            "id": 789,
            "title": "Junior Backend Developer",
            "company_name": "Example Remotive Co",
            "url": "https://remotive.com/remote-jobs/software-dev/junior-backend-developer-789",
            "candidate_required_location": "USA Only",
            "job_type": "full_time",
            "category": "Software Development",
            "salary": "$70k-$90k",
            "description": "<p>Build <strong>Python</strong> APIs.</p>",
            "publication_date": "2026-07-17T00:00:00Z",
        }
    )

    assert job is not None
    assert job.id == "remotive:789"
    assert job.source == "remotive"
    assert job.company == "Example Remotive Co"
    assert job.title == "Junior Backend Developer"
    assert job.location == "Remote (USA Only)"
    assert "Build Python APIs." in job.description
    assert "Software Development" in job.description
    assert job.apply_url.startswith("https://remotive.com/")


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


def test_swe_query_accepts_developer_titles_from_non_greenhouse_sources() -> None:
    assert _score_job(
        title="Backend Developer",
        description="Build APIs with Python and PostgreSQL.",
        query="SWE",
    ) > 0

    assert _score_job(
        title="Full Stack Developer",
        description="Build React and Node applications.",
        query="SWE",
    ) > 0

    assert _score_job(
        title="Junior Backend Developer",
        description="Build APIs with Python and SQL.",
        query="SWE",
        level="entry",
    ) > 0


def test_swe_query_is_general_purpose_not_early_career_only() -> None:
    assert _score_job(
        title="Principal Software Engineer, Performance",
        description="Build high-scale infrastructure with Python.",
        query="SWE",
    ) > 0

    assert _score_job(
        title="Senior Software Engineer, Backend",
        description="Build backend systems with Python.",
        query="SWE",
    ) > 0

    assert _score_job(
        title="Software Engineer II, Backend",
        description="Build backend systems with Python and Java.",
        query="SWE",
    ) > 0

    assert _score_job(
        title="Forward Deployed Software Engineer",
        description="Required: 5+ years of software engineering experience with Python.",
        query="SWE",
    ) > 0


def test_query_terms_can_infer_level_when_specific() -> None:
    assert resolve_job_level("SWE") == "any"
    assert resolve_job_level("SWE Intern") == "intern"
    assert resolve_job_level("entry level SWE") == "entry"
    assert resolve_job_level("senior SWE") == "senior"
    assert resolve_job_level("SWE", "intern") == "intern"


def test_intern_level_filters_to_internship_roles() -> None:
    assert _score_job(
        title="Software Engineer Intern",
        description="Build backend services with Python during a summer internship.",
        query="SWE",
        level="intern",
    ) > 0

    assert _score_job(
        title="Software Engineer, Backend",
        description="Build backend services with Python.",
        query="SWE",
        level="intern",
    ) == 0

    assert _score_job(
        title="Software Engineer Intern",
        description="Build backend services with Python during a summer internship.",
        query="SWE Intern",
    ) > 0

    assert _score_job(
        title="Software Engineer, Backend",
        description="Build backend services with Python.",
        query="SWE Intern",
    ) == 0


def test_intern_level_does_not_match_internal_or_internally() -> None:
    assert _score_job(
        title="Software Engineer II, Backend",
        description="Collaborate with internal teams and improve internal developer platforms.",
        query="SWE",
        level="intern",
    ) == 0

    assert _score_job(
        title="Software Engineer II, Backend",
        description="You will learn new techniques internally and mentor others.",
        query="SWE Intern",
    ) == 0


def test_entry_level_filters_to_entry_friendly_roles() -> None:
    assert _score_job(
        title="Software Engineer I",
        description="Required: 0-1 years of software engineering experience with Python.",
        query="SWE",
        level="entry",
    ) > 0

    assert _score_job(
        title="Associate Software Engineer",
        description="Build APIs with Python and JavaScript.",
        query="SWE",
        level="entry",
    ) > 0

    assert _score_job(
        title="New Grad Software Engineer",
        description="Build backend services with Python.",
        query="SWE",
        level="entry",
    ) > 0

    assert _score_job(
        title="Senior Software Engineer, Backend",
        description="Required: 7+ years of software engineering experience with Python.",
        query="SWE",
        level="entry",
    ) == 0

    assert _score_job(
        title="Forward Deployed Software Engineer",
        description="Required: 5+ years of software engineering experience with Python.",
        query="entry level SWE",
    ) == 0


def test_entry_level_does_not_return_mid_senior_or_staff_roles() -> None:
    assert _score_job(
        title="Software Engineer II, Android",
        description="Our mission is to build education products. You will grow your career with us.",
        query="SWE",
        level="entry",
    ) == 0

    assert _score_job(
        title="Senior Software Engineer, Frontend",
        description="Ready to do the most impactful work of your career? Build React systems.",
        query="SWE",
        level="entry",
    ) == 0

    assert _score_job(
        title="Staff Software Engineer, AI Developer Tools",
        description="Build high-scale engineering systems with CI/CD and machine learning.",
        query="SWE",
        level="entry",
    ) == 0


def test_mid_and_senior_levels_filter_separately() -> None:
    assert _score_job(
        title="Software Engineer II, Backend",
        description="Build backend systems with Python and Java.",
        query="SWE",
        level="mid",
    ) > 0

    assert _score_job(
        title="Software Engineer I",
        description="Required: 0-1 years of software engineering experience with Python.",
        query="SWE",
        level="mid",
    ) == 0

    assert _score_job(
        title="Principal Software Engineer, Performance",
        description="Required: 10+ years of software engineering experience with Python.",
        query="SWE",
        level="senior",
    ) > 0

    assert _score_job(
        title="Software Engineer I",
        description="Required: 0-1 years of software engineering experience with Python.",
        query="SWE",
        level="senior",
    ) == 0


def test_default_search_market_excludes_obvious_non_us_locations() -> None:
    assert _matches_location("Remote, Brazil", None) is False
    assert _matches_location("Beijing, China", None) is False
    assert _matches_location("Lisbon, Portugal", None) is False
    assert _matches_location("Remote, United States", None) is True
    assert _matches_location("Washington, DC", None) is True


def test_remote_filter_excludes_country_specific_non_us_remote_roles() -> None:
    assert _matches_location("Remote, Brazil", "Remote") is False
    assert _matches_location("Remote, United States", "Remote") is True
    assert _matches_location("Remote (Worldwide)", "Remote") is True
    assert _matches_location("Remote (USA Only)", "Remote") is True


def test_us_city_search_includes_exact_aliases_and_us_remote_roles() -> None:
    assert _matches_location("Philadelphia, PA", "Philadelphia") is True
    assert _matches_location("Remote, United States", "Philadelphia") is True
    assert _matches_location("Remote-US", "Philadelphia") is True
    assert _matches_location("Remote (Worldwide)", "Philadelphia") is True
    assert _matches_location("Remote (USA Only)", "Philadelphia") is True
    assert _matches_location("Remote, Brazil", "Philadelphia") is False
    assert _matches_location("New York, NY", "Philadelphia") is False
    assert _matches_location("Pittsburgh, PA", "Philadelphia") is False
