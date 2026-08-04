from __future__ import annotations

import httpx

from app import occupation_catalog_runtime as occupation_runtime
from app.production_occupation_audit import (
    ProductionOccupationAudit,
    load_production_occupation_audit,
)


def test_production_occupation_audit_manifest_is_bounded_and_valid() -> None:
    audit = load_production_occupation_audit()
    cases = audit["cases"]

    assert len(cases) == 40
    assert audit["max_results_per_case"] == 3
    assert len({case["id"] for case in cases}) == 40
    assert len(
        {
            case["career_sphere"]
            for case in cases
            if case["kind"] == "recognized"
        }
    ) >= 12
    assert sum(case["kind"] == "recognized" for case in cases) == 32
    assert sum(case["kind"] == "ambiguous" for case in cases) == 4
    assert sum(case["kind"] == "unknown" for case in cases) == 4

    for case in cases:
        interpretation = occupation_runtime.interpret_occupation_query(case["query"])
        assert interpretation.status == case["expected_status"], case
        if case["kind"] == "recognized":
            assert interpretation.concept_key == case["expected_concept_key"], case
            assert interpretation.soc_major_group == case["expected_soc_major_group"], case


def test_production_occupation_audit_validates_safe_live_shapes() -> None:
    audit_manifest = {
        "version": 1,
        "minimum_cases": 3,
        "minimum_career_spheres": 1,
        "max_results_per_case": 3,
        "cases": [
            {
                "id": "recognized-accountant",
                "kind": "recognized",
                "career_sphere": "accounting",
                "query": "Accountant",
                "expected_status": "recognized",
                "expected_concept_key": "accountant",
                "expected_soc_major_group": "13",
            },
            {
                "id": "ambiguous-sae",
                "kind": "ambiguous",
                "career_sphere": "cross-sector ambiguity",
                "query": "SAE",
                "expected_status": "ambiguous",
            },
            {
                "id": "unknown-xyz",
                "kind": "unknown",
                "career_sphere": "unknown",
                "query": "XYZ jobs",
                "expected_status": "unrecognized",
            },
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        query = request.url.params["query"]
        common = {
            "query": query,
            "location": None,
            "level": "any",
            "industry": None,
            "role_family": None,
        }
        if query == "Accountant":
            return httpx.Response(
                200,
                request=request,
                json={
                    **common,
                    "providers_searched": ["mock:accounting"],
                    "result_count": 1,
                    "results": [
                        {
                            "title": "Senior Staff Accountant",
                            "description": "Own accounting close and financial reporting.",
                        }
                    ],
                    "warnings": [],
                    "source_coverage": [
                        {
                            "provider": "mock",
                            "status": "available",
                        }
                    ],
                    "search_suggestions": [],
                    "external_search_links": [],
                },
            )
        if query == "SAE":
            return httpx.Response(
                200,
                request=request,
                json={
                    **common,
                    "providers_searched": [],
                    "result_count": 0,
                    "results": [],
                    "warnings": ["Choose an occupation meaning before searching."],
                    "source_coverage": [],
                    "search_suggestions": ["Sales Engineer", "Systems Application Engineer"],
                    "external_search_links": [],
                },
            )
        return httpx.Response(
            200,
            request=request,
            json={
                **common,
                "providers_searched": [],
                "result_count": 0,
                "results": [],
                "warnings": ["MarketLens could not safely identify this occupation."],
                "source_coverage": [],
                "search_suggestions": ["Spell out the occupation title."],
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

    assert report["passed"], report
    assert report["counts"]["passed_cases"] == 3
    assert report["counts"]["returned_titles"] == 1
    assert report["metrics"]["returned_title_precision"] == 1.0
