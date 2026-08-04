from __future__ import annotations

import pytest

from app import job_search, occupation_catalog_runtime
from app.job_search_title_precision import title_satisfies_occupation_precision
from app.production_occupation_audit import ProductionOccupationAudit


@pytest.mark.parametrize(
    ("title", "query", "description"),
    [
        (
            "Finance Fellow - Human Frontier Collective (US)",
            "Financial Analyst",
            "Build forecasts, analyze financial models, and support strategic finance.",
        ),
        (
            "Finance Fellow - Human Frontier Collective (US)",
            "senior financial analyst",
            "Lead forecasts and financial planning with more than five years of experience.",
        ),
        (
            "SY 26/27 School Nurse LPN",
            "Registered Nurse",
            "Provide school health services and nursing care.",
        ),
        (
            "Medical Fellow - Human Frontier Collective (US)",
            "Medical Assistant",
            "Support medical operations, patient coordination, and clinical workflows.",
        ),
        (
            "Brex Rotational Program",
            "entry level accountant jobs",
            "Rotate through accounting, audit, and finance teams with no experience required.",
        ),
        (
            "Internal Audit Analyst",
            "entry level accountant jobs",
            "Perform accounting controls, reconciliations, and audit testing.",
        ),
        (
            "Head of Accountant Partner Program",
            "Accountant",
            "Lead an accountant partner program and go-to-market strategy.",
        ),
    ],
)
def test_production_observed_title_false_positives_are_rejected(
    title: str,
    query: str,
    description: str,
) -> None:
    assert not title_satisfies_occupation_precision(
        title,
        query,
        occupation_catalog_runtime,
    )
    assert not job_search._matches_requested_role(
        title,
        description,
        query,
        None,
    )
    assert job_search._score_job(
        title,
        description,
        query,
    ) == 0

    interpretation = occupation_catalog_runtime.interpret_occupation_query(query)
    assert not ProductionOccupationAudit._title_is_relevant(
        case={"query": query},
        interpretation=interpretation,
        title=title,
        description=description,
    )


@pytest.mark.parametrize(
    ("title", "query"),
    [
        ("Senior Analyst, Strategic Finance", "Financial Analyst"),
        ("Senior Financial Analyst", "senior financial analyst"),
        ("School Nurse (RN) - Camden", "Registered Nurse"),
        ("Emergency Department RN", "RN jobs"),
        ("Registered Nurse - Emergency Department", "Registered Nurse"),
        ("Certified Medical Assistant", "Medical Assistant"),
        ("Clinical Medical Assistant", "Medical Assistant"),
        ("Staff Accountant", "entry level accountant jobs"),
        ("Senior Accountant, Capital Markets", "Accountant"),
    ],
)
def test_legitimate_title_variants_remain_precise(title: str, query: str) -> None:
    assert title_satisfies_occupation_precision(
        title,
        query,
        occupation_catalog_runtime,
    )


def test_registered_nurse_guard_rejects_distinct_advanced_practice_roles() -> None:
    for title in (
        "Nurse Practitioner",
        "Certified Registered Nurse Anesthetist",
        "Licensed Vocational Nurse",
    ):
        assert not title_satisfies_occupation_precision(
            title,
            "Registered Nurse",
            occupation_catalog_runtime,
        )
