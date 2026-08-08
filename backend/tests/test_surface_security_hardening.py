from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.security import (
    EXPENSIVE_RATE_LIMIT,
    MAX_API_REQUEST_BODY_BYTES,
    SecurityHeadersMiddleware,
    _get_rate_limit_identifier,
    enforce_expensive_rate_limit,
    fastapi_docs_configuration,
    reset_rate_limit_state_for_tests,
)


def _request(client_host: str, *, forwarded_for: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode()))
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "https",
        "path": "/jobs/search",
        "raw_path": b"/jobs/search",
        "query_string": b"",
        "headers": headers,
        "client": (client_host, 43120),
        "server": ("marketlens.test", 443),
    }
    return Request(scope)


def test_untrusted_peer_cannot_spoof_rate_limit_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TRUSTED_PROXY_CIDRS", raising=False)
    request = _request("198.51.100.20", forwarded_for="203.0.113.99")
    assert _get_rate_limit_identifier(request) == "198.51.100.20"


def test_trusted_proxy_can_supply_valid_forwarded_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "10.0.0.0/8")
    request = _request("10.8.0.4", forwarded_for="203.0.113.99, 10.8.0.4")
    assert _get_rate_limit_identifier(request) == "203.0.113.99"


def test_expensive_rate_limit_blocks_after_policy_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TRUSTED_PROXY_CIDRS", raising=False)
    reset_rate_limit_state_for_tests()
    request = _request("198.51.100.21")
    for _ in range(EXPENSIVE_RATE_LIMIT.max_requests):
        enforce_expensive_rate_limit(request)
    with pytest.raises(HTTPException) as exc_info:
        enforce_expensive_rate_limit(request)
    assert exc_info.value.status_code == 429
    assert exc_info.value.headers == {"Retry-After": "60"}
    reset_rate_limit_state_for_tests()


def test_production_docs_are_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARKETLENS_ENVIRONMENT", "production")
    assert fastapi_docs_configuration() == {
        "docs_url": None,
        "redoc_url": None,
        "openapi_url": None,
    }


def test_local_docs_remain_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MARKETLENS_ENVIRONMENT", raising=False)
    for name in (
        "RAILWAY_PROJECT_ID",
        "RAILWAY_SERVICE_ID",
        "RAILWAY_ENVIRONMENT_ID",
        "RAILWAY_ENVIRONMENT_NAME",
    ):
        monkeypatch.delenv(name, raising=False)
    assert fastapi_docs_configuration()["docs_url"] == "/docs"


def test_security_headers_include_production_backend_csp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARKETLENS_ENVIRONMENT", "production")
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.headers["strict-transport-security"].startswith("max-age=")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "camera=()" in response.headers["permissions-policy"]
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert "no-store" in response.headers["cache-control"]


def test_main_app_rejects_oversized_request_before_json_parsing() -> None:
    from app.main import app

    payload = b"x" * (MAX_API_REQUEST_BODY_BYTES + 1)
    response = TestClient(app).post(
        "/skills/extract",
        content=payload,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json() == {"detail": "Request body is too large."}


def test_container_and_frontend_header_contracts() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    backend_docker = (repo_root / "backend" / "Dockerfile").read_text()
    frontend_docker = (repo_root / "frontend" / "Dockerfile").read_text()
    nginx = (repo_root / "frontend" / "nginx.conf").read_text()
    entrypoint = (repo_root / "frontend" / "docker-entrypoint.sh").read_text()

    assert "USER marketlens" in backend_docker
    assert "USER nginx" in frontend_docker
    assert "EXPOSE 8080" in frontend_docker
    assert "Content-Security-Policy" in nginx
    assert "frame-ancestors 'none'" in nginx
    assert "object-src 'none'" in nginx
    assert "server_tokens off" in nginx
    assert "__PORT__" in nginx
    assert "exec nginx" in entrypoint
