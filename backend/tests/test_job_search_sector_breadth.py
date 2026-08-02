from __future__ import annotations

from app import job_search
from app.job_search_sector_breadth import SECTOR_QUERIES, sector_for_query


def test_required_friend_career_spheres_are_supported() -> None:
    expected = {
        "finance",
        "accounting",
        "law enforcement",
        "healthcare",
        "business",
        "skilled trades",
        "engineering",
        "education",
        "law",
        "marketing",
        "sports",
        "economics",
    }
    assert expected.issubset({sector.canonical for sector in SECTOR_QUERIES.values()})


def test_sector_queries_accept_common_search_modifiers() -> None:
    assert sector_for_query("entry level accounting jobs") == SECTOR_QUERIES["accounting"]
    assert sector_for_query("engineering internships") == SECTOR_QUERIES["engineering"]
    assert sector_for_query("senior marketing roles") == SECTOR_QUERIES["marketing"]
    assert sector_for_query("new grad healthcare careers") == SECTOR_QUERIES["healthcare"]


def test_sector_queries_resolve_to_existing_search_families() -> None:
    expected = {
        "finance jobs": "finance",
        "accounting careers": "finance",
        "law enforcement jobs": "operations",
        "healthcare jobs": "healthcare",
        "business roles": "operations",
        "skilled trades jobs": "operations",
        "engineering careers": "technology",
        "education jobs": "operations",
        "law careers": "legal",
        "marketing jobs": "marketing",
        "sports careers": "marketing",
        "economics jobs": "data",
    }
    for query, family in expected.items():
        intent = job_search.parse_job_search_intent(query=query, level="any")
        assert intent.job_function == family, query


def test_engineering_sector_admits_multiple_disciplines_but_rejects_non_engineering() -> None:
    assert job_search._score_job(
        "Civil Engineer",
        "Design transportation systems.",
        "engineering jobs",
        "any",
    ) > 0
    assert job_search._score_job(
        "Mechanical Design Engineer",
        "Design mechanical systems.",
        "engineering jobs",
        "any",
    ) > 0
    assert job_search._score_job(
        "Human Resources Specialist",
        "Recruit employees.",
        "engineering jobs",
        "any",
    ) == 0


def test_law_enforcement_sector_remains_distinct_from_private_security() -> None:
    assert job_search._score_job(
        "Police Officer",
        "Patrol and enforce laws.",
        "law enforcement jobs",
        "any",
    ) > 0
    assert job_search._score_job(
        "Detective",
        "Investigate crimes.",
        "law enforcement jobs",
        "any",
    ) > 0
    assert job_search._score_job(
        "Security Guard",
        "Monitor a private building.",
        "law enforcement jobs",
        "any",
    ) == 0


def test_education_sector_does_not_admit_education_software_sales() -> None:
    assert job_search._score_job(
        "High School Teacher",
        "Teach mathematics.",
        "education jobs",
        "any",
    ) > 0
    assert job_search._score_job(
        "School Counselor",
        "Support students.",
        "education jobs",
        "any",
    ) > 0
    assert job_search._score_job(
        "Education Software Account Executive",
        "Sell software to school districts.",
        "education jobs",
        "any",
    ) == 0


def test_skilled_trades_sector_admits_multiple_trades() -> None:
    for title in (
        "Journeyman Electrician",
        "Commercial Plumber",
        "HVAC Technician",
        "Welder Fabricator",
        "Automotive Mechanic",
    ):
        assert job_search._score_job(
            title,
            "Hands-on skilled trade work.",
            "skilled trades jobs",
            "any",
        ) > 0, title


def test_broad_sector_search_is_explicitly_broader_than_occupation_search() -> None:
    assert sector_for_query("engineering jobs") is not None
    assert sector_for_query("civil engineer") is None
    assert sector_for_query("registered nurse") is None
    assert sector_for_query("staff accountant") is None
