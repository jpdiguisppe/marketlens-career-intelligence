from __future__ import annotations

import httpx
import pytest

from app import job_search
from app.job_search_source_expansion import (
    MAX_DETAIL_REQUESTS,
    MAX_SEARCH_PASSES_PER_SOURCE,
    MAX_SOURCES_PER_SEARCH,
    _DETAIL_CACHE,
    _LIST_CACHE,
    _normalize_posting,
    _posting_location,
    _search_smartrecruiters,
    _search_terms,
    select_smartrecruiters_sources,
)
from app.smartrecruiters_sources import SMARTRECRUITERS_SOURCES




@pytest.fixture(autouse=True)
def clear_smartrecruiters_caches() -> None:
    _LIST_CACHE.clear()
    _DETAIL_CACHE.clear()

def _source(identifier: str):
    return next(source for source in SMARTRECRUITERS_SOURCES if source.identifier == identifier)


@pytest.mark.parametrize(
    ("query", "expected_sources"),
    [
        ("Electrical Engineer", {"AECOM2", "BoschGroup", "CRB"}),
        ("elementary school teacher", {"KIPP"}),
        ("social worker", {"CityofPhiladelphia", "HealthFederationOfPhiladelphia", "KIPP"}),
        ("librarian", {"CityofPhiladelphia", "KIPP"}),
        ("chemistry", {"Eurofins", "LGCGroup", "SGS"}),
        ("laboratory technician", {"Eurofins", "LGCGroup", "SGS"}),
        ("physical therapy", {"USPhysicalTherapy2"}),
        ("journalism", {"NBCUniversal3", "InformaGroupPlc"}),
        ("hvac technician", {"Bosch-HomeComfort", "CityofPhiladelphia"}),
        ("accountant", {"CityofPhiladelphia", "Experian", "Evolution"}),
        ("legal assistant", {"CityofPhiladelphia"}),
        ("policy analyst", {"CityofPhiladelphia"}),
    ],
)
def test_source_selection_spans_representative_sectors(
    query: str,
    expected_sources: set[str],
) -> None:
    selected = {
        source.identifier
        for source in select_smartrecruiters_sources(
            job_search,
            query,
            "Philadelphia",
            "entry",
        )
    }
    assert expected_sources.issubset(selected), (query, selected)
    assert len(selected) <= MAX_SOURCES_PER_SEARCH


def test_source_selection_does_not_claim_irrelevant_fallback_coverage() -> None:
    selected = select_smartrecruiters_sources(
        job_search,
        "translator",
        "Philadelphia",
        "entry",
    )
    assert selected == ()


def test_location_bound_public_employers_only_activate_for_their_region() -> None:
    philadelphia = {
        source.identifier
        for source in select_smartrecruiters_sources(
            job_search,
            "government policy analyst",
            "Philadelphia",
            "entry",
        )
    }
    new_york = {
        source.identifier
        for source in select_smartrecruiters_sources(
            job_search,
            "government policy analyst",
            "New York",
            "entry",
        )
    }
    assert "CityofPhiladelphia" in philadelphia
    assert "CityofPhiladelphia" not in new_york
    assert "CityAndCountyOfSanFrancisco1" not in new_york


def test_provider_search_terms_remove_level_noise_and_keep_occupation_aliases() -> None:
    assert _search_terms("entry level chemistry") == ("chemistry", "chemist")
    assert _search_terms("Electrical Engineer internship")[0] == "electrical engineer"
    assert len(_search_terms("physical therapy")) <= MAX_SEARCH_PASSES_PER_SOURCE


def test_location_normalization_keeps_remote_separate_from_city() -> None:
    assert _posting_location(
        {
            "location": {
                "city": "Philadelphia",
                "region": "PA",
                "country": "us",
                "remote": False,
            }
        }
    ) == "Philadelphia, PA, United States"
    assert _posting_location(
        {
            "location": {
                "city": "Philadelphia",
                "region": "PA",
                "country": "us",
                "remote": True,
            }
        }
    ) == "Remote - United States"


def test_normalization_uses_public_apply_url_and_full_description() -> None:
    source = _source("BoschGroup")
    raw = {
        "id": "abc",
        "name": "Electrical Engineer I",
        "releasedDate": "2026-07-20T00:00:00Z",
        "location": {
            "city": "Philadelphia",
            "region": "PA",
            "country": "us",
            "remote": False,
        },
    }
    details = {
        **raw,
        "applyUrl": "https://jobs.smartrecruiters.com/BoschGroup/abc/apply",
        "company": {"name": "Bosch Group"},
        "jobAd": {
            "jobDescription": "<p>Design electrical systems.</p>",
            "qualifications": "<p>One year of experience preferred.</p>",
        },
        "experienceLevel": {"label": "Entry Level"},
    }
    job = _normalize_posting(job_search, source, raw, details)
    assert job is not None
    assert job.source == "smartrecruiters"
    assert job.title == "Electrical Engineer I"
    assert job.location == "Philadelphia, PA, United States"
    assert job.apply_url.startswith("https://jobs.smartrecruiters.com/")
    assert "Design electrical systems" in job.description
    assert "Entry Level" in job.description


def test_live_shape_search_rejects_wrong_role_and_remote_fallback(monkeypatch) -> None:
    source = _source("BoschGroup")
    monkeypatch.setattr(
        "app.job_search_source_expansion.select_smartrecruiters_sources",
        lambda *_args, **_kwargs: (source,),
    )

    list_payload = {
        "content": [
            {
                "id": "exact",
                "name": "Electrical Engineer I",
                "location": {
                    "city": "Philadelphia",
                    "region": "PA",
                    "country": "us",
                    "remote": False,
                },
                "experienceLevel": {"label": "Entry Level"},
            },
            {
                "id": "wrong-role",
                "name": "Analytics Engineer",
                "location": {
                    "city": "Philadelphia",
                    "region": "PA",
                    "country": "us",
                    "remote": False,
                },
                "experienceLevel": {"label": "Entry Level"},
            },
            {
                "id": "remote",
                "name": "Electrical Engineer I",
                "location": {
                    "city": "Philadelphia",
                    "region": "PA",
                    "country": "us",
                    "remote": True,
                },
                "experienceLevel": {"label": "Entry Level"},
            },
        ]
    }
    detail_payload = {
        "id": "exact",
        "name": "Electrical Engineer I",
        "applyUrl": "https://jobs.smartrecruiters.com/BoschGroup/exact/apply",
        "company": {"name": "Bosch Group"},
        "location": {
            "city": "Philadelphia",
            "region": "PA",
            "country": "us",
            "remote": False,
        },
        "jobAd": {
            "jobDescription": "Design electrical systems.",
            "qualifications": "One year of experience preferred.",
        },
        "experienceLevel": {"label": "Entry Level"},
    }

    detail_requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/postings"):
            return httpx.Response(200, json=list_payload)
        if request.url.path.endswith("/postings/exact"):
            detail_requests.append(request.url.path)
            return httpx.Response(200, json=detail_payload)
        raise AssertionError(str(request.url))

    monkeypatch.setattr(
        job_search,
        "_build_provider_client",
        lambda: httpx.Client(transport=httpx.MockTransport(handler)),
    )

    outcome, selected = _search_smartrecruiters(
        job_search,
        "Electrical Engineer",
        "Philadelphia",
        "entry",
    )
    assert selected == (source,)
    assert outcome is not None
    assert [job.title for _, job in outcome.scored_jobs] == ["Electrical Engineer I"]
    assert outcome.fetched_count == 3
    assert "Bosch Group" in outcome.notes[0]
    assert len(detail_requests) == 1
    assert len(outcome.scored_jobs) <= MAX_DETAIL_REQUESTS


def test_untrusted_posting_id_cannot_change_the_detail_endpoint(monkeypatch) -> None:
    source = _source("BoschGroup")
    monkeypatch.setattr(
        "app.job_search_source_expansion.select_smartrecruiters_sources",
        lambda *_args, **_kwargs: (source,),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/postings"):
            return httpx.Response(
                200,
                json={
                    "content": [
                        {
                            "id": "../../other-company/postings/secret",
                            "name": "Electrical Engineer I",
                            "location": {
                                "city": "Philadelphia",
                                "region": "PA",
                                "country": "us",
                                "remote": False,
                            },
                        }
                    ]
                },
            )
        raise AssertionError("Invalid posting id should never trigger a detail request")

    monkeypatch.setattr(
        job_search,
        "_build_provider_client",
        lambda: httpx.Client(transport=httpx.MockTransport(handler)),
    )
    outcome, _ = _search_smartrecruiters(
        job_search,
        "Electrical Engineer",
        "Philadelphia",
        "entry",
    )
    assert outcome is not None
    assert outcome.fetched_count == 0
    assert outcome.scored_jobs == []


def _empty_provider_outcome(provider: str, label: str) -> job_search._ProviderOutcome:
    return job_search._ProviderOutcome(provider, label, 0, [], notes=[])


def _disable_legacy_remote_feeds(monkeypatch) -> None:
    monkeypatch.setattr(job_search, "_remoteok_enabled", lambda: False)
    monkeypatch.setattr(job_search, "_remotive_enabled", lambda: False)


def _stub_empty_ats_providers(monkeypatch) -> None:
    monkeypatch.setattr(
        job_search,
        "_search_greenhouse_boards",
        lambda *args, **kwargs: _empty_provider_outcome(
            "greenhouse",
            "Greenhouse company boards",
        ),
    )
    monkeypatch.setattr(
        job_search,
        "_search_lever_sites",
        lambda *args, **kwargs: _empty_provider_outcome(
            "lever",
            "Lever company boards",
        ),
    )


def test_disabled_source_expansion_preserves_existing_search_without_network(monkeypatch) -> None:
    monkeypatch.setenv("JOB_SEARCH_SMARTRECRUITERS_ENABLED", "false")
    _disable_legacy_remote_feeds(monkeypatch)
    _stub_empty_ats_providers(monkeypatch)

    def unexpected_client() -> None:
        raise AssertionError("Disabled SmartRecruiters must not create a provider client")

    # Base search still creates its established provider client, so supply a
    # harmless context manager and assert SmartRecruiters is absent from reporting.
    from contextlib import nullcontext

    monkeypatch.setattr(job_search, "_build_provider_client", lambda: nullcontext(object()))
    result = job_search.search_external_jobs(
        query="Electrical Engineer",
        location="Philadelphia",
        level="entry",
        limit=5,
    )
    assert result.results == []
    assert not any(
        provider.startswith("smartrecruiters:")
        for provider in result.providers_searched
    )
    assert not any(
        coverage.provider == "smartrecruiters"
        for coverage in result.source_coverage
    )


def test_source_expansion_failure_degrades_to_existing_results_and_reports_failure(monkeypatch) -> None:
    monkeypatch.setenv("JOB_SEARCH_SMARTRECRUITERS_ENABLED", "true")
    _disable_legacy_remote_feeds(monkeypatch)
    _stub_empty_ats_providers(monkeypatch)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"message": "temporary failure"})

    monkeypatch.setattr(
        job_search,
        "_build_provider_client",
        lambda: httpx.Client(transport=httpx.MockTransport(handler)),
    )
    result = job_search.search_external_jobs(
        query="Electrical Engineer",
        location="Philadelphia",
        level="entry",
        limit=5,
    )
    assert result.results == []
    smartrecruiters_coverage = next(
        coverage
        for coverage in result.source_coverage
        if coverage.provider == "smartrecruiters"
    )
    assert smartrecruiters_coverage.status == "failed"
    assert smartrecruiters_coverage.matched_count == 0
    assert any(
        provider.startswith("smartrecruiters:")
        for provider in result.providers_searched
    )


def test_source_expansion_merges_ranks_and_semantically_deduplicates(monkeypatch) -> None:
    monkeypatch.setenv("JOB_SEARCH_SMARTRECRUITERS_ENABLED", "true")
    _disable_legacy_remote_feeds(monkeypatch)

    base_duplicate = job_search.ExternalJobResult(
        id="greenhouse:regional:1",
        source="greenhouse",
        company="Regional Engineering",
        title="Electrical Engineer I",
        location="Philadelphia, PA",
        description="Entry-level electrical design role requiring 1 year of experience.",
        apply_url="https://example.com/base",
    )
    base_near_match = job_search.ExternalJobResult(
        id="greenhouse:regional:2",
        source="greenhouse",
        company="Regional Engineering",
        title="Electrical Design Engineer",
        location="King of Prussia, PA",
        description="Electrical systems design role requiring 1 year of experience.",
        apply_url="https://example.com/design",
    )
    monkeypatch.setattr(
        job_search,
        "_search_greenhouse_boards",
        lambda *args, **kwargs: job_search._ProviderOutcome(
            "greenhouse",
            "Greenhouse company boards",
            2,
            [
                (job_search._score_job(base_duplicate.title, base_duplicate.description, "Electrical Engineer", "entry"), base_duplicate),
                (job_search._score_job(base_near_match.title, base_near_match.description, "Electrical Engineer", "entry"), base_near_match),
            ],
            notes=[],
        ),
    )
    monkeypatch.setattr(
        job_search,
        "_search_lever_sites",
        lambda *args, **kwargs: _empty_provider_outcome(
            "lever",
            "Lever company boards",
        ),
    )

    source = _source("AECOM2")
    smart_duplicate = job_search.ExternalJobResult(
        id="smartrecruiters:AECOM2:duplicate",
        source="smartrecruiters",
        company="Regional Engineering",
        title="Electrical Engineer I",
        location="Philadelphia, PA",
        description="Entry-level electrical design role requiring 1 year of experience.",
        apply_url="https://example.com/smart",
    )
    smart_exact = job_search.ExternalJobResult(
        id="smartrecruiters:AECOM2:exact",
        source="smartrecruiters",
        company="AECOM",
        title="Electrical Engineer I",
        location="Philadelphia, PA",
        description="Entry-level electrical design role requiring 1 year of experience.",
        apply_url="https://example.com/exact",
    )
    monkeypatch.setattr(
        "app.job_search_source_expansion._search_smartrecruiters",
        lambda *args, **kwargs: (
            job_search._ProviderOutcome(
                "smartrecruiters",
                "SmartRecruiters cross-sector company boards",
                2,
                [(80, smart_duplicate), (90, smart_exact)],
                notes=["Intent-selected public company boards: AECOM."],
            ),
            (source,),
        ),
    )
    from contextlib import nullcontext

    monkeypatch.setattr(job_search, "_build_provider_client", lambda: nullcontext(object()))
    result = job_search.search_external_jobs(
        query="Electrical Engineer",
        location="Philadelphia",
        level="entry",
        limit=5,
    )

    assert result.results[0].id == smart_exact.id
    duplicate_keys = [
        (job.company.lower(), job.title.lower(), (job.location or "").lower())
        for job in result.results
    ]
    assert len(duplicate_keys) == len(set(duplicate_keys))
    assert len(result.results) == 3
    assert result.source_coverage[-1].provider == "smartrecruiters"
