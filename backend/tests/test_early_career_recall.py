import pytest

from app.job_search import (
    _matches_level,
    _remotive_search_terms,
    _score_job,
    resolve_job_level,
)


@pytest.mark.parametrize(
    ("query", "expected_level"),
    [
        ("software engineering co-op", "intern"),
        ("public policy fellowship", "intern"),
        ("legal summer associate", "intern"),
        ("finance rotational program", "entry"),
        ("recent graduate data analyst", "entry"),
        ("early talent cybersecurity", "entry"),
    ],
)
def test_resolve_job_level_recognizes_broader_early_career_language(
    query: str,
    expected_level: str,
) -> None:
    assert resolve_job_level(query) == expected_level


@pytest.mark.parametrize(
    ("title", "description"),
    [
        ("2027 Software Engineering Co-op", "Students rotate through backend engineering teams."),
        ("Public Policy Fellowship", "Fellows support policy research and advocacy."),
        ("Summer 2027 Software Engineering", "Candidates must be currently enrolled and returning to school."),
        ("Technology Apprentice", "Apprentices receive structured software engineering training."),
    ],
)
def test_intern_matching_recalls_coops_fellowships_and_seasonal_programs(
    title: str,
    description: str,
) -> None:
    assert _matches_level(title, description, "intern") is True


def test_intern_matching_rejects_roles_that_only_mention_interns() -> None:
    assert _matches_level(
        "Senior Software Engineer",
        "Lead platform architecture and mentor interns during the summer program.",
        "intern",
    ) is False
    assert _matches_level(
        "Software Engineer",
        "Partner internally with recruiting and occasionally support the internship program.",
        "intern",
    ) is False


@pytest.mark.parametrize(
    ("title", "description"),
    [
        ("Software Engineer I", "Build backend services with Python and SQL."),
        ("Associate Software Engineer", "Early career role for recent graduates."),
        ("Technology Rotational Program", "Recent graduates rotate through software engineering and data teams."),
        ("Software Engineer", "No prior professional experience required. Training is provided."),
        ("Data Analyst", "Candidates should have 0-2 years of analytics experience."),
    ],
)
def test_entry_matching_recalls_numbered_program_and_low_experience_roles(
    title: str,
    description: str,
) -> None:
    assert _matches_level(title, description, "entry") is True


def test_entry_matching_rejects_senior_titles_and_high_experience_requirements() -> None:
    assert _matches_level(
        "Senior Software Engineer",
        "Join an early career mentorship initiative while requiring 7+ years of experience.",
        "entry",
    ) is False
    assert _matches_level(
        "Software Engineer",
        "This entry-level branded role requires 5+ years of production experience.",
        "entry",
    ) is False


def test_scoring_accepts_generic_program_only_with_requested_role_evidence() -> None:
    assert _score_job(
        "Technology Rotational Program",
        "Recent graduates rotate through software engineering, backend, and data platform teams.",
        "software engineer entry level",
        level="entry",
    ) > 0
    assert _score_job(
        "Business Rotational Program",
        "Recent graduates rotate through sales, recruiting, and account management.",
        "software engineer entry level",
        level="entry",
    ) == 0


def test_scoring_rejects_intern_mentions_in_unrelated_experienced_roles() -> None:
    assert _score_job(
        "Senior Software Engineer",
        "Own backend systems and mentor software engineering interns.",
        "software engineering internship",
        level="intern",
    ) == 0


def test_remote_search_terms_include_early_career_aliases() -> None:
    intern_terms = _remotive_search_terms("software engineering co-op", "intern")
    entry_terms = _remotive_search_terms("software engineer entry level", "entry")

    assert "software co-op" in intern_terms
    assert "software fellowship" in intern_terms
    assert "new grad software engineer" in entry_terms
    assert "software engineer i" in entry_terms
