from __future__ import annotations

import httpx
import pytest

from app import job_search, occupation_catalog_runtime
from app.production_occupation_audit import ProductionOccupationAudit


def test_live_audit_uses_final_search_matcher_as_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        occupation_catalog_runtime,
        "title_matches_occupation",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(
        job_search,
        "_matches_requested_role",
        lambda *_args, **_kwargs: True,
    )

    assert ProductionOccupationAudit._title_is_relevant(
        case={"query": "Financial Analyst", "level": "any"},
        interpretation=object(),
        title="Senior Analyst, Strategic Finance",
        description="Own forecasting, financial planning, and business analysis.",
    )


def test_production_audit_rejects_accountant_partner_program_title() -> None:
    audit_manifest = {
        "version": 1,
        "minimum_cases": 1,
        "minimum_career_spheres": 1,
        "max_results_per_case": 3,
        "cases": [
            {
                "id": "accountant-partner-program",
                "kind": "recognized",
                "career_sphere": "accounting",
                "query": "Accountant",
                "expected_status": "recognized",
                "expected_concept_key": "accountant",
                "expected_soc_major_group": "13",
            }
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            request=request,
            json={
                "query": "Accountant",
                "location": None,
                "level": "any",
                "role_family": "finance",
                "industry": None,
                "providers_searched": ["greenhouse:gusto"],
                "result_count": 1,
                "results": [
                    {
                        "title": "Head of Accountant Partner Program",
                        "description": "Lead the partner program serving accounting firms.",
                    }
                ],
                "warnings": [],
                "source_coverage": [
                    {
                        "provider": "greenhouse:gusto",
                        "status": "available",
                    }
                ],
                "search_suggestions": [],
                "external_search_links": [],
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    audit = ProductionOccupationAudit(
        backend_url="https://example.test",
        audit=audit_manifest,
        client=client,
        inter_request_seconds=0,
    )
    try:
        audit.run()
        report = audit.report()
    finally:
        client.close()

    assert not report["passed"]
    assert report["counts"]["failed_cases"] == 1
    assert report["cases"][0]["error_code"] == "irrelevant_result_title"
