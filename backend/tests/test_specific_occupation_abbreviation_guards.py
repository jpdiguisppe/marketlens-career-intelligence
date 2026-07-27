from __future__ import annotations

import pytest

from app import job_search
from app.job_search_source_expansion import _search_terms


@pytest.mark.parametrize(
    ("query", "title"),
    [
        ("SRE", "Site Reliability Engineer"),
        ("SRE", "SRE"),
        ("MLE", "Machine Learning Engineer"),
        ("MLE", "ML Engineer"),
        ("AI Engineer", "AI Engineer"),
        ("AI Engineer", "Artificial Intelligence Engineer"),
        ("SOC analyst", "Security Operations Center Analyst"),
        ("BI", "Business Intelligence Analyst"),
        ("UX", "UX Designer"),
        ("UI", "User Interface Designer"),
        ("QA", "QA Engineer"),
        ("DBA", "Database Administrator"),
        ("sysadmin", "Systems Administrator"),
    ],
)
def test_specific_abbreviations_accept_literal_and_expanded_titles(
    query: str,
    title: str,
) -> None:
    assert job_search._score_job(
        title=title,
        description=f"{title} responsibilities and qualifications.",
        query=query,
        level="any",
    ) > 0


@pytest.mark.parametrize(
    ("query", "wrong_title"),
    [
        ("SRE", "Backend Developer"),
        ("MLE", "Data Analyst"),
        ("AI Engineer", "Data Analyst"),
        ("SOC analyst", "Security Engineer"),
        ("BI", "Data Scientist"),
        ("UX", "Graphic Designer"),
        ("UI", "Graphic Designer"),
        ("QA", "Backend Engineer"),
        ("DBA", "Data Analyst"),
        ("sysadmin", "Software Engineer"),
    ],
)
def test_specific_abbreviations_do_not_broaden_to_entire_role_family(
    query: str,
    wrong_title: str,
) -> None:
    assert job_search._score_job(
        title=wrong_title,
        description=f"{wrong_title} responsibilities and qualifications.",
        query=query,
        level="any",
    ) == 0


def test_provider_terms_expand_without_losing_literal_title_support() -> None:
    assert _search_terms("SRE")[0] == "site reliability engineer"
    assert _search_terms("MLE")[0] == "machine learning engineer"
    assert _search_terms("AI Engineer")[0] == "artificial intelligence engineer"
