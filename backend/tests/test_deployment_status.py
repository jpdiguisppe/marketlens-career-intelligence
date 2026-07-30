from __future__ import annotations

from fastapi.testclient import TestClient

from app.deployment_status import deployment_revision
from app.main import app

client = TestClient(app)


def test_deployment_status_reports_normalized_railway_revision(monkeypatch) -> None:
    revision = "ABCDEF0123456789ABCDEF0123456789ABCDEF01"
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", revision)
    monkeypatch.setenv("RAILWAY_GIT_BRANCH", "main")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")

    response = client.get("/deployment/status")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "marketlens-backend",
        "revision": revision.lower(),
        "branch": "main",
        "environment": "production",
    }

    legacy = client.get("/saved-jobs/deployment-status")
    assert legacy.status_code == 200
    assert legacy.json() == {"status": "ok", "revision": revision.lower()}


def test_deployment_revision_uses_safe_fallback_order(monkeypatch) -> None:
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", "not-a-sha")
    monkeypatch.setenv("GITHUB_SHA", "1234567890abcdef1234567890abcdef12345678")

    assert deployment_revision() == "1234567890abcdef1234567890abcdef12345678"


def test_deployment_status_does_not_expose_unvalidated_environment_values(monkeypatch) -> None:
    monkeypatch.delenv("RAILWAY_GIT_COMMIT_SHA", raising=False)
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.delenv("MARKETLENS_REVISION", raising=False)
    monkeypatch.setenv("RAILWAY_GIT_BRANCH", "main;echo secret")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production\nTOKEN=value")

    response = client.get("/deployment/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["revision"] == "unknown"
    assert payload["branch"] == "mainechosecret"
    assert payload["environment"] == "productionTOKENvalue"
