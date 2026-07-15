import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["ADMIN_API_KEY"] = "test-admin-key"

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite://"
ADMIN_HEADERS = {"X-Admin-API-Key": "test-admin-key"}

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _sample_job_posting_payload() -> dict[str, str]:
    return {
        "company": "Comcast",
        "title": "Backend Software Engineer",
        "location": "Philadelphia, PA",
        "role_category": "Backend SWE",
        "experience_level": "Entry-Level",
        "description": "Build REST APIs with Python, SQL, Docker, Git, and Agile practices.",
    }


def test_create_job_posting_requires_admin_api_key() -> None:
    response = client.post("/job-postings", json=_sample_job_posting_payload())

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing admin API key."


def test_create_job_posting_extracts_and_persists_skills() -> None:
    response = client.post(
        "/job-postings",
        json=_sample_job_posting_payload(),
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 201
    created_posting = response.json()
    assert created_posting["company"] == "Comcast"
    assert created_posting["extracted_skills"] == [
        "Agile",
        "Docker",
        "Git",
        "Python",
        "REST APIs",
        "SQL",
    ]

    list_response = client.get("/job-postings")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_csv_import_requires_admin_api_key() -> None:
    csv_content = (
        "company,title,location,role_category,experience_level,description\n"
        "Lockheed Martin,Software Engineer Associate,King of Prussia PA,Systems/SWE,Entry-Level,Python Linux Git Agile testing\n"
    )

    response = client.post(
        "/job-postings/import-csv",
        files={"file": ("jobs.csv", csv_content.encode("utf-8"), "text/csv")},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing admin API key."


def test_csv_import_creates_multiple_postings() -> None:
    csv_content = (
        "company,title,location,role_category,experience_level,description\n"
        "Lockheed Martin,Software Engineer Associate,King of Prussia PA,Systems/SWE,Entry-Level,Python Linux Git Agile testing\n"
        "Leidos,Cloud Automation Engineer,Remote,Cloud/SWE,Entry-Level,Python AWS Docker CI/CD automation scripting\n"
    )

    response = client.post(
        "/job-postings/import-csv",
        files={"file": ("jobs.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["imported_count"] == 2
    assert body["failed_count"] == 0
    assert len(body["created_postings"]) == 2

    top_skills_response = client.get("/skills/top")
    assert top_skills_response.status_code == 200
    top_skills = top_skills_response.json()
    assert top_skills["Python"] == 2
    assert top_skills["Docker"] == 1
    assert top_skills["AWS"] == 1


def test_resume_analysis_compares_resume_against_target_role_category() -> None:
    client.post(
        "/job-postings",
        json={
            "company": "Comcast",
            "title": "Backend Software Engineer",
            "location": "Philadelphia, PA",
            "role_category": "Backend SWE",
            "experience_level": "Entry-Level",
            "description": "Backend role using Python, SQL, Docker, and REST APIs.",
        },
        headers=ADMIN_HEADERS,
    )
    client.post(
        "/job-postings",
        json={
            "company": "UHS",
            "title": "Systems Engineer Intern",
            "location": "King of Prussia, PA",
            "role_category": "Systems/Cloud",
            "experience_level": "Internship",
            "description": "Systems role using Azure, Windows Server, scripting, and troubleshooting.",
        },
        headers=ADMIN_HEADERS,
    )

    response = client.post(
        "/resume/analyze",
        json={
            "resume_text": "Python, SQL, Git, Agile, and backend development projects.",
            "target_role_category": "Backend SWE",
        },
    )

    assert response.status_code == 200
    analysis = response.json()
    assert analysis["postings_analyzed"] == 1
    assert analysis["target_role_category"] == "Backend SWE"
    assert analysis["matched_skills"] == ["Python", "SQL"]
    assert analysis["missing_skills"] == ["Docker", "REST APIs"]
    assert analysis["match_percentage"] == 50.0
    assert analysis["learning_priorities"] == ["Docker", "REST APIs"]


def test_resume_analysis_returns_error_when_target_role_has_no_postings() -> None:
    response = client.post(
        "/resume/analyze",
        json={
            "resume_text": "Python, SQL, and Docker",
            "target_role_category": "AI Engineer",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "No saved job postings found for that target role category."


def test_resume_analysis_rejects_overly_long_resume_text() -> None:
    response = client.post(
        "/resume/analyze",
        json={"resume_text": "x" * 10_001},
    )

    assert response.status_code == 422


def test_custom_analysis_compares_resume_against_pasted_job_descriptions_without_saving() -> None:
    response = client.post(
        "/analysis/custom",
        json={
            "resume_text": "Python, SQL, Git, Agile, and backend development projects.",
            "job_descriptions": [
                "Backend role using Python, SQL, Docker, and REST APIs.",
            ],
        },
    )

    assert response.status_code == 200
    analysis = response.json()
    assert analysis["postings_analyzed"] == 1
    assert analysis["target_role_category"] is None
    assert analysis["matched_skills"] == ["Python", "SQL"]
    assert analysis["missing_skills"] == ["Docker", "REST APIs"]
    assert analysis["match_percentage"] == 50.0
    assert analysis["learning_priorities"] == ["Docker", "REST APIs"]

    saved_postings_response = client.get("/job-postings")
    assert saved_postings_response.status_code == 200
    assert saved_postings_response.json() == []


def test_custom_analysis_returns_error_when_no_target_skills_are_found() -> None:
    response = client.post(
        "/analysis/custom",
        json={
            "resume_text": "Python and SQL",
            "job_descriptions": ["Friendly team with strong communication and collaboration."],
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "No recognizable target skills found in the provided job descriptions."


def test_model_assisted_status_reports_disabled_without_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AI_ANALYSIS_ENABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    response = client.get("/analysis/model-status")

    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is False
    assert body["status"] == "not_configured"
    assert "OPENAI_API_KEY" in body["required_backend_settings"]
    assert "Provider keys must stay in backend environment variables only." in body["safety_notes"]


def test_model_assisted_status_never_exposes_backend_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "super-secret-test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")

    response = client.get("/analysis/model-status")

    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["status"] == "configured"
    assert "super-secret-test-key" not in str(body)


def test_resume_text_file_upload_extracts_text_without_saving() -> None:
    resume_text = "SKILLS\nPython, SQL, FastAPI\nPROJECTS\nBuilt REST APIs."

    response = client.post(
        "/analysis/resume-file/extract",
        files={"file": ("resume.txt", resume_text.encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "resume.txt"
    assert body["text"] == resume_text
    assert body["character_count"] == len(resume_text)
    assert "not saved" in " ".join(body["warnings"])

    saved_postings_response = client.get("/job-postings")
    assert saved_postings_response.status_code == 200
    assert saved_postings_response.json() == []


def test_resume_file_upload_rejects_unsupported_file_type() -> None:
    response = client.post(
        "/analysis/resume-file/extract",
        files={"file": ("resume.pdf", b"fake pdf bytes", "application/pdf")},
    )

    assert response.status_code == 400
    assert "currently supports .txt and .md" in response.json()["detail"]
