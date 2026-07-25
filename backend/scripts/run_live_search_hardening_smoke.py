from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import job_search  # noqa: E402
from app.job_search_source_expansion import (  # noqa: E402
    select_smartrecruiters_sources,
)


SCENARIOS = (
    {
        "sector": "engineering-built-environment",
        "query": "electrical engineer",
        "level": "entry",
        "location": "Philadelphia",
        "expected_source": "AECOM2",
    },
    {
        "sector": "education-liberal-arts",
        "query": "elementary school teacher",
        "level": "entry",
        "location": "Philadelphia",
        "expected_source": "KIPP",
    },
    {
        "sector": "science-research",
        "query": "chemistry",
        "level": "entry",
        "location": "Philadelphia",
        "expected_source": "Eurofins",
    },
    {
        "sector": "business-finance-operations",
        "query": "human resources specialist",
        "level": "entry",
        "location": "Philadelphia",
        "expected_source": "Experian",
    },
    {
        "sector": "healthcare",
        "query": "physical therapy",
        "level": "entry",
        "location": "Philadelphia",
        "expected_source": "USPhysicalTherapy2",
    },
    {
        "sector": "legal-public-service",
        "query": "policy analyst",
        "level": "entry",
        "location": "Philadelphia",
        "expected_source": "CityofPhiladelphia",
    },
    {
        "sector": "trades-construction-logistics",
        "query": "hvac technician",
        "level": "entry",
        "location": "Philadelphia",
        "expected_source": "Bosch-HomeComfort",
    },
    {
        "sector": "creative-communications",
        "query": "journalism",
        "level": "entry",
        "location": "Philadelphia",
        "expected_source": "NBCUniversal3",
    },
    {
        "sector": "service-hospitality-transport-agriculture",
        "query": "agronomist",
        "level": "entry",
        "location": "Philadelphia",
        "expected_source": "SyngentaGroup",
    },
    {
        "sector": "service-hospitality-transport-agriculture",
        "query": "delivery driver",
        "level": "entry",
        "location": "Philadelphia",
        "expected_source": "Dominos",
    },
)

CLOSED_PROVIDER_PREFIXES = (
    "indeed",
    "linkedin",
    "handshake",
    "workday",
)


def _job_score(job: Any, query: str, level: str, location: str | None) -> int:
    return job_search._score_job(
        job.title,
        job.description,
        query,
        level,
        company=job.company,
    ) + job_search._location_score_bonus(job.location, location)


def _run_scenario(scenario: dict[str, str]) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    selected_sources = select_smartrecruiters_sources(
        job_search,
        scenario["query"],
        scenario["location"],
        scenario["level"],
    )
    selected_ids = {source.identifier for source in selected_sources}
    if scenario["expected_source"] not in selected_ids:
        failures.append(
            f"expected source {scenario['expected_source']} was not selected; got {sorted(selected_ids)}"
        )

    result = job_search.search_external_jobs(
        query=scenario["query"],
        location=scenario["location"],
        level=scenario["level"],
        limit=8,
    )

    expected_provider_ids = {
        f"smartrecruiters:{source.identifier}" for source in selected_sources
    }
    missing_provider_ids = expected_provider_ids - set(result.providers_searched)
    if missing_provider_ids:
        failures.append(
            f"selected public sources missing from providers_searched: {sorted(missing_provider_ids)}"
        )

    if any(
        provider.lower().startswith(CLOSED_PROVIDER_PREFIXES)
        for provider in result.providers_searched
    ):
        failures.append("closed job boards were incorrectly reported as searched providers")

    smartrecruiters_coverage = [
        coverage
        for coverage in result.source_coverage
        if coverage.provider == "smartrecruiters"
    ]
    if not smartrecruiters_coverage:
        failures.append("SmartRecruiters source coverage was not reported")

    seen_ids: set[str] = set()
    seen_semantic: set[tuple[str, str, str]] = set()
    scores: list[int] = []
    result_rows: list[dict[str, Any]] = []
    for job in result.results:
        semantic_key = (
            job.company.strip().lower(),
            job.title.strip().lower(),
            (job.location or "").strip().lower(),
        )
        if job.id in seen_ids:
            failures.append(f"duplicate job id returned: {job.id}")
        if semantic_key in seen_semantic:
            failures.append(f"semantic duplicate returned: {semantic_key}")
        seen_ids.add(job.id)
        seen_semantic.add(semantic_key)

        role_score = job_search._score_job(
            job.title,
            job.description,
            result.query,
            result.level,
            company=job.company,
        )
        location_match = job_search._matches_location(job.location, result.location)
        total_score = _job_score(job, result.query, result.level, result.location)
        scores.append(total_score)

        if role_score <= 0:
            failures.append(
                f"irrelevant result passed role/level filtering: {job.company} | {job.title}"
            )
        if not location_match:
            failures.append(
                f"result violated strict location: {job.company} | {job.title} | {job.location}"
            )
        if not job.apply_url.startswith("https://"):
            failures.append(f"non-HTTPS apply URL returned for {job.id}")

        result_rows.append(
            {
                "company": job.company,
                "title": job.title,
                "location": job.location,
                "source": job.source,
                "score": total_score,
                "apply_url": job.apply_url,
            }
        )

    if scores != sorted(scores, reverse=True):
        failures.append(f"results were not sorted by descending search score: {scores}")

    if not result.results and not result.warnings:
        failures.append("zero-result search did not explain the current source limitation")
    if not result.external_search_links:
        failures.append("responsible external continuation links were missing")
    if any(not link.url.startswith("https://") for link in result.external_search_links):
        failures.append("non-HTTPS external continuation link returned")

    coverage_rows = [
        {
            "provider": coverage.provider,
            "label": coverage.label,
            "status": coverage.status,
            "fetched_count": coverage.fetched_count,
            "matched_count": coverage.matched_count,
            "notes": coverage.notes,
        }
        for coverage in result.source_coverage
    ]
    return (
        {
            **scenario,
            "selected_smartrecruiters_sources": sorted(selected_ids),
            "providers_searched": result.providers_searched,
            "coverage": coverage_rows,
            "results": result_rows,
            "warnings": result.warnings,
            "suggestions": result.search_suggestions,
        },
        failures,
    )


def main() -> int:
    reports: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for scenario in SCENARIOS:
        report, scenario_failures = _run_scenario(scenario)
        reports.append(report)
        if scenario_failures:
            failures.append(
                {
                    "sector": scenario["sector"],
                    "query": scenario["query"],
                    "failures": scenario_failures,
                }
            )

    total_fetched = sum(
        int(coverage["fetched_count"])
        for report in reports
        for coverage in report["coverage"]
    )
    searched_scenarios = sum(
        any(coverage["status"] == "searched" for coverage in report["coverage"])
        for report in reports
    )
    if total_fetched <= 0:
        failures.append(
            {
                "sector": "all",
                "query": "all",
                "failures": ["live public providers returned no fetched postings at all"],
            }
        )
    if searched_scenarios < len(SCENARIOS) - 2:
        failures.append(
            {
                "sector": "all",
                "query": "all",
                "failures": [
                    f"only {searched_scenarios}/{len(SCENARIOS)} scenarios had a successfully searched provider"
                ],
            }
        )

    output = {
        "passed": not failures,
        "scenario_count": len(SCENARIOS),
        "total_fetched": total_fetched,
        "scenarios_with_searched_provider": searched_scenarios,
        "failures": failures,
        "reports": reports,
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if output["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
