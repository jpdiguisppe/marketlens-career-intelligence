import pytest

from app.job_search import (
    _matches_location,
    _matches_requested_role,
    _score_job,
)


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Electrical Engineer I", True),
        ("Electrical Design Engineer", True),
        ("Analytics Engineer", False),
        ("Marketing Assistant", False),
        ("Electrical Engineering Recruiter", False),
    ],
)
def test_electrical_engineer_search_preserves_the_full_occupation(
    title: str,
    expected: bool,
) -> None:
    assert (
        _matches_requested_role(
            title,
            "Entry-level role requiring 1 year of experience.",
            "Electrical Engineer",
            "entry",
        )
        is expected
    )


def test_explicit_city_search_does_not_silently_include_remote_jobs() -> None:
    assert _matches_location("Philadelphia, PA", "Philadelphia")
    assert _matches_location("Philly", "Philadelphia")
    assert not _matches_location("Remote - USA", "Philadelphia")
    assert not _matches_location("Remote (California, United States)", "Philadelphia")
    assert not _matches_location("New York, NY", "Philadelphia")


def test_remote_search_is_an_explicit_location_choice() -> None:
    assert _matches_location("Remote", "Remote")
    assert _matches_location("Remote - USA", "Remote")
    assert _matches_location("Worldwide", "Remote")
    assert not _matches_location("Remote - Europe", "Remote")


def test_exact_occupation_outranks_shared_head_and_unrelated_titles() -> None:
    exact = _score_job(
        "Electrical Engineer I",
        "Electrical design role requiring 1 year of experience.",
        "Electrical Engineer",
        "entry",
    )
    shared_head = _score_job(
        "Analytics Engineer",
        "Build analytics pipelines with 1 year of experience.",
        "Electrical Engineer",
        "entry",
    )
    unrelated = _score_job(
        "Marketing Assistant",
        "Support campaigns with 1 year of experience.",
        "Electrical Engineer",
        "entry",
    )

    assert exact > 0
    assert shared_head == 0
    assert unrelated == 0


@pytest.mark.parametrize(
    ("query", "matching_title", "unrelated_title"),
    [
        ("elementary school teacher", "Elementary Teacher", "Education Data Analyst"),
        ("laboratory technician", "Lab Technician I", "IT Support Technician"),
        ("accountant", "Accountant I", "Marketing Analyst"),
        ("social worker", "Social Worker I", "Social Media Manager"),
        ("journalism", "Junior Reporter", "Marketing Coordinator"),
        ("librarian", "Assistant Librarian", "Library Software Engineer"),
        ("electrician", "Electrician I", "Electrical Engineer I"),
        ("welding", "Welder I", "Welding Sales Representative"),
        ("graphic designer", "Junior Graphic Designer", "Product Manager"),
        ("physical therapy", "Physical Therapist", "Physical Therapy Sales Representative"),
        ("pharmacy", "Pharmacist I", "Pharmacy Sales Specialist"),
    ],
)
def test_representative_cross_sector_searches_reject_other_occupations(
    query: str,
    matching_title: str,
    unrelated_title: str,
) -> None:
    description = "Entry-level position requiring 1 year of experience."
    assert _score_job(matching_title, description, query, "entry") > 0
    assert _score_job(unrelated_title, description, query, "entry") == 0
