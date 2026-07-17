import pytest
from fastapi.testclient import TestClient

from app.job_search import ExternalJobResult, JobSearchResults
from app.main import _rate_limit_buckets, app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_rate_limit_buckets() -> None:
    _rate_limit_buckets.clear()


def test_external_job_search_returns_normalized_results(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_search_external_jobs(
        query: str,
        location: str | None,
        limit: int,
        level: str | None = None,
    ) -> JobSearchResults:
        assert query == "SWE intern"
        assert location == "Remote"
        assert level is None
        assert limit == 5
        return JobSearchResults(
            query=query,
            location=location,
            level="intern",
            providers_searched=["greenhouse:testcompany"],
            results=[
                ExternalJobResult(
                    id="greenhouse:testcompany:123",
                    source="greenhouse",
                    company="Testcompany",
                    title="Software Engineering Intern",
                    location="Remote",
                    description="Build Python REST APIs with SQL, Docker, and Git.",
                    apply_url="https://boards.greenhouse.io/testcompany/jobs/123",
                    updated_at="2026-07-16T12:00:00Z",
                )
            ],
            warnings=[],
        )

    monkeypatch.setattr("app.main.search_external_jobs", fake_search_external_jobs)

    response = client.get(
        "/jobs/search",
        params={"query": "SWE intern", "location": "Remote", "limit": 5},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "SWE intern"
    assert body["location"] == "Remote"
    assert body["level"] == "intern"
    assert body["providers_searched"] == ["greenhouse:testcompany"]
    assert body["result_count"] == 1
    result = body["results"][0]
    assert result["id"] == "greenhouse:testcompany:123"
    assert result["title"] == "Software Engineering Intern"
    assert result["apply_url"] == "https://boards.greenhouse.io/testcompany/jobs/123"
    assert {"Python", "REST APIs", "SQL", "Docker", "Git"}.issubset(set(result["extracted_skills"]))


def test_external_job_search_validates_limit() -> None:
    response = client.get("/jobs/search", params={"query": "SWE", "limit": 100})

    assert response.status_code == 422
