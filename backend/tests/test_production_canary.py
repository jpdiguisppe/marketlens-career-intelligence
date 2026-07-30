from __future__ import annotations

import httpx
import pytest

from app.production_canary import (
    ProductionCareerPlanCanary,
    ProductionCanaryError,
    parse_frontend_config,
)

REVISION = "1234567890abcdef1234567890abcdef12345678"
FRONTEND_URL = "https://frontend.example"
BACKEND_URL = "https://backend.example"


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if request.url.host == "frontend.example":
        if path == "/config.js":
            return httpx.Response(
                200,
                text=(
                    "window.__MARKETLENS_CONFIG__ = {"
                    f'apiBaseUrl: "{BACKEND_URL}", '
                    f'deploymentRevision: "{REVISION}"'
                    "};"
                ),
            )
        if path == "/":
            return httpx.Response(200, text='<html><div id="root"></div><script src="/assets/app.js"></script></html>')
        if path == "/assets/app.js":
            return httpx.Response(
                200,
                text=(
                    'Seven-step workflow '
                    'Inspect every candidate decision before approval '
                    'fetch("/career-plans")'
                ),
            )
    if request.url.host == "backend.example":
        if path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if path == "/deployment/status":
            return httpx.Response(
                200,
                json={
                    "status": "ok",
                    "service": "marketlens-backend",
                    "revision": REVISION,
                    "branch": "main",
                    "environment": "production",
                },
            )
        if path == "/analysis/model-status":
            return httpx.Response(200, json={"enabled": False, "status": "not_configured"})
        if path == "/career-plans" and request.method == "GET":
            return httpx.Response(401, json={"detail": "Not authenticated"})
        if path == "/jobs/search":
            return httpx.Response(
                200,
                json={
                    "results": [],
                    "source_coverage": [{"provider": "greenhouse", "status": "searched"}],
                    "providers_searched": ["greenhouse:example"],
                    "warnings": [],
                },
            )
        if path == "/analysis/smart":
            return httpx.Response(
                200,
                json={
                    "fit_summary": {"score": 74},
                    "analysis_engine": "deterministic",
                    "model_assisted_status": "not_requested",
                    "coaching_status": "not_requested",
                    "provider_telemetry": None,
                },
            )
    return httpx.Response(404, json={"detail": "not found"})


def _canary() -> ProductionCareerPlanCanary:
    client = httpx.Client(transport=httpx.MockTransport(_handler), follow_redirects=True)
    return ProductionCareerPlanCanary(
        frontend_url=FRONTEND_URL,
        backend_url=BACKEND_URL,
        expected_revision=REVISION,
        client=client,
    )


def test_public_canary_contract_passes_with_exact_revision() -> None:
    canary = _canary()

    canary.wait_for_exact_revision()
    canary.run_public()
    report = canary.report(mode="public", authenticated_configured=False)

    assert report["passed"] is True
    assert report["failed_check_count"] == 0
    assert report["check_count"] == 8
    assert {item["name"] for item in report["checks"]} == {
        "backend_health",
        "backend_revision",
        "frontend_revision",
        "frontend_career_plan_bundle",
        "model_status",
        "private_route_auth_boundary",
        "live_job_search",
        "deterministic_smart_fit",
    }
    bundle_check = next(item for item in report["checks"] if item["name"] == "frontend_career_plan_bundle")
    assert bundle_check["details"]["markers"] == [
        "Seven-step workflow",
        "Inspect every candidate decision before approval",
        "/career-plans",
    ]


def test_full_canary_cannot_pass_without_authenticated_identity() -> None:
    canary = _canary()
    canary.run_public()

    report = canary.report(mode="full", authenticated_configured=False)

    assert report["passed"] is False
    assert report["failed_check_count"] == 0
    assert report["authenticated_configured"] is False


def test_frontend_config_parser_rejects_missing_revision() -> None:
    with pytest.raises(ProductionCanaryError) as exc_info:
        parse_frontend_config('window.__MARKETLENS_CONFIG__ = {apiBaseUrl: "https://api.example"};')

    assert exc_info.value.code == "frontend_config_invalid"
