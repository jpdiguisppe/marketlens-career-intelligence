import pytest

import app.job_search as job_search
from app.job_search import _query_role_family, _score_job, _search_remoteok


def test_nursing_query_is_classified_as_healthcare() -> None:
    assert _query_role_family("Nursing jobs") == "healthcare"
    assert _query_role_family("RN positions") == "healthcare"
    assert _query_role_family("CNA openings") == "healthcare"


@pytest.mark.parametrize(
    ("query", "title"),
    [
        ("Nursing jobs", "Registered Nurse"),
        ("RN jobs", "Emergency Department RN"),
        ("RN jobs", "Clinical Nurse II"),
        ("RN jobs", "Staff Nurse - Medical Surgical"),
        ("LPN positions", "Licensed Practical Nurse"),
        ("CNA jobs", "Certified Nursing Assistant"),
        ("nurse practitioner careers", "Family Nurse Practitioner"),
        ("mechanical engineering jobs", "Mechanical Engineer"),
        ("electrical engineering careers", "Electrical Engineer I"),
        ("teaching jobs", "Elementary School Teacher"),
        ("law careers", "Associate Attorney"),
        ("psychology jobs", "Clinical Psychologist"),
        ("biology careers", "Research Biologist"),
        ("chemistry jobs", "Analytical Chemist"),
        ("architecture jobs", "Project Architect"),
        ("journalism careers", "Staff Journalist"),
        ("social work jobs", "Licensed Social Worker"),
        ("electrician jobs", "Journeyman Electrician"),
        ("plumbing jobs", "Commercial Plumber"),
        ("welding careers", "Structural Welder"),
        ("carpentry jobs", "Finish Carpenter"),
        ("culinary careers", "Sous Chef"),
    ],
)
def test_major_career_queries_match_real_occupation_titles(
    query: str,
    title: str,
) -> None:
    assert _score_job(
        title=title,
        description=f"{title} responsibilities and qualifications.",
        query=query,
    ) > 0


@pytest.mark.parametrize(
    ("query", "unrelated_title"),
    [
        ("Nursing jobs", "Software Engineer"),
        ("RN jobs", "Patient Care Specialist"),
        ("RN jobs", "Medical Scheduler"),
        ("RN jobs", "Patient Access Scheduler"),
        ("RN jobs", "Medical Assistant"),
        ("mechanical engineering jobs", "Marketing Coordinator"),
        ("teaching jobs", "Financial Analyst"),
        ("law careers", "Data Scientist"),
        ("electrician jobs", "Registered Nurse"),
    ],
)
def test_major_career_queries_reject_unrelated_titles(
    query: str,
    unrelated_title: str,
) -> None:
    assert _score_job(
        title=unrelated_title,
        description="A role in an unrelated professional field serving hospitals and patients.",
        query=query,
    ) == 0


def test_local_rn_search_excludes_remote_feed_results(monkeypatch: pytest.MonkeyPatch) -> None:
    raw_jobs = [
        {
            "id": 501,
            "position": "Registered Nurse - Telehealth",
            "company": "Example Health",
            "url": "https://example.com/jobs/501",
            "location": "USA",
            "description": "Registered nurse providing remote telehealth support.",
            "date": "2026-07-20T00:00:00Z",
        }
    ]
    monkeypatch.setattr(job_search, "_remoteok_jobs", lambda client, query: raw_jobs)

    local_outcome = _search_remoteok(object(), "RN", "Philadelphia", "any")
    remote_outcome = _search_remoteok(object(), "RN", "Remote", "any")

    assert local_outcome.scored_jobs == []
    assert local_outcome.matched_count == 0
    assert len(remote_outcome.scored_jobs) == 1
    assert remote_outcome.scored_jobs[0][1].title == "Registered Nurse - Telehealth"


def test_unknown_occupation_uses_generic_title_matching() -> None:
    assert _score_job(
        title="Marine Biologist",
        description="Study marine ecosystems and wildlife.",
        query="marine biology jobs",
    ) > 0

    assert _score_job(
        title="Insurance Underwriter",
        description="Evaluate insurance applications and risk.",
        query="underwriting careers",
    ) > 0

    assert _score_job(
        title="Court Reporter",
        description="Create official transcripts of legal proceedings.",
        query="court reporting jobs",
    ) > 0
