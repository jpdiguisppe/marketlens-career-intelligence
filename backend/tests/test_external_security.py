import pytest
from pydantic import ValidationError

from app.external_urls import sanitize_external_https_url
from app.job_search import (
    ProviderRequestBudgetExceeded,
    _ACTIVE_PROVIDER_REQUEST_BUDGET,
    _ATS_PROVIDER_CACHE,
    _ProviderRequestBudget,
    _build_provider_client,
    _greenhouse_jobs_for_board,
    _normalize_greenhouse_job,
)
from app.saved_jobs import SavedJobCreate


class _FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, list[dict[str, object]]]:
        return {
            "jobs": [
                {
                    "id": 1,
                    "title": "Software Engineer",
                    "absolute_url": "https://boards.greenhouse.io/example/jobs/1",
                    "location": {"name": "Remote"},
                    "content": "Python",
                }
            ]
        }


class _FakeClient:
    def __init__(self) -> None:
        self.calls = 0

    def get(self, *args: object, **kwargs: object) -> _FakeResponse:
        self.calls += 1
        return _FakeResponse()


def test_external_links_must_be_public_https_urls() -> None:
    assert sanitize_external_https_url("https://example.com/jobs/1") == "https://example.com/jobs/1"
    assert sanitize_external_https_url("http://example.com/jobs/1") is None
    assert sanitize_external_https_url("javascript:alert(1)") is None
    assert sanitize_external_https_url("https://user:password@example.com/jobs/1") is None
    assert sanitize_external_https_url("https://localhost/jobs/1") is None
    assert sanitize_external_https_url("https://127.0.0.1/jobs/1") is None
    assert sanitize_external_https_url("https://10.0.0.1/jobs/1") is None
    assert sanitize_external_https_url("https://example.com:8443/jobs/1") is None


def test_saved_job_payload_rejects_unsafe_application_url() -> None:
    with pytest.raises(ValidationError):
        SavedJobCreate(
            company="Example",
            title="Engineer",
            description="Python",
            apply_url="javascript:alert(1)",
        )


def test_provider_payload_with_unsafe_url_is_dropped() -> None:
    assert _normalize_greenhouse_job(
        "example",
        {
            "id": 1,
            "title": "Engineer",
            "absolute_url": "http://example.com/job/1",
            "location": {"name": "Remote"},
            "content": "Python",
        },
    ) is None


def test_ats_payload_cache_avoids_repeated_network_fanout() -> None:
    _ATS_PROVIDER_CACHE.clear()
    client = _FakeClient()
    token = _ACTIVE_PROVIDER_REQUEST_BUDGET.set(_ProviderRequestBudget(remaining=1))
    try:
        first = _greenhouse_jobs_for_board(client, "example")
        second = _greenhouse_jobs_for_board(client, "example")
    finally:
        _ACTIVE_PROVIDER_REQUEST_BUDGET.reset(token)

    assert first == second
    assert client.calls == 1


def test_provider_request_budget_fails_closed() -> None:
    _ATS_PROVIDER_CACHE.clear()
    client = _FakeClient()
    token = _ACTIVE_PROVIDER_REQUEST_BUDGET.set(_ProviderRequestBudget(remaining=0))
    try:
        with pytest.raises(ProviderRequestBudgetExceeded):
            _greenhouse_jobs_for_board(client, "uncached-example")
    finally:
        _ACTIVE_PROVIDER_REQUEST_BUDGET.reset(token)

    assert client.calls == 0


def test_provider_client_does_not_follow_redirects() -> None:
    client = _build_provider_client()
    try:
        assert client.follow_redirects is False
    finally:
        client.close()
