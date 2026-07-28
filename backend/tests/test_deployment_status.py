from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_deployment_status_reports_valid_railway_revision(monkeypatch) -> None:
    revision = "A" * 40
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", revision)

    response = client.get("/saved-jobs/deployment-status")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "revision": revision.lower(),
    }


def test_deployment_status_hides_invalid_revision(monkeypatch) -> None:
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", "not-a-safe-revision\nlog-injection")

    response = client.get("/saved-jobs/deployment-status")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "revision": "unknown",
    }
