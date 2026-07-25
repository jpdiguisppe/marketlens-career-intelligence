from __future__ import annotations

import json
from typing import Any

from run_live_search_hardening_smoke import _run_scenario


NATIONAL_SCENARIOS: tuple[dict[str, Any], ...] = (
    {
        "sector": "engineering-built-environment",
        "query": "electrical engineer",
        "level": "any",
        "location": None,
        "expected_source": "AECOM2",
    },
    {
        "sector": "education-liberal-arts",
        "query": "elementary school teacher",
        "level": "any",
        "location": None,
        "expected_source": "KIPP",
    },
    {
        "sector": "science-research",
        "query": "chemistry",
        "level": "any",
        "location": None,
        "expected_source": "Eurofins",
    },
    {
        "sector": "business-finance-operations",
        "query": "human resources specialist",
        "level": "any",
        "location": None,
        "expected_source": "Experian",
    },
    {
        "sector": "healthcare",
        "query": "physical therapy",
        "level": "any",
        "location": None,
        "expected_source": "USPhysicalTherapy2",
    },
    {
        "sector": "legal-public-service",
        "query": "policy analyst",
        "level": "any",
        "location": None,
        "expected_source": "CityofPhiladelphia",
    },
    {
        "sector": "trades-construction-logistics",
        "query": "hvac technician",
        "level": "any",
        "location": None,
        "expected_source": "Bosch-HomeComfort",
    },
    {
        "sector": "creative-communications",
        "query": "journalism",
        "level": "any",
        "location": None,
        "expected_source": "NBCUniversal3",
    },
    {
        "sector": "service-hospitality-transport-agriculture",
        "query": "agronomist",
        "level": "any",
        "location": None,
        "expected_source": "SyngentaGroup",
    },
    {
        "sector": "service-hospitality-transport-agriculture",
        "query": "delivery driver",
        "level": "any",
        "location": None,
        "expected_source": "Dominos",
    },
)


def main() -> int:
    reports: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for scenario in NATIONAL_SCENARIOS:
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

    scenarios_with_results = sum(bool(report["results"]) for report in reports)
    scenarios_with_multiple_results = sum(
        len(report["results"]) >= 2 for report in reports
    )
    total_results = sum(len(report["results"]) for report in reports)
    represented_sectors = {
        report["sector"] for report in reports if report["results"]
    }

    if scenarios_with_results < 5:
        failures.append(
            {
                "sector": "all",
                "query": "national breadth",
                "failures": [
                    f"only {scenarios_with_results}/{len(NATIONAL_SCENARIOS)} broadened searches returned a valid live result"
                ],
            }
        )
    if len(represented_sectors) < 5:
        failures.append(
            {
                "sector": "all",
                "query": "national breadth",
                "failures": [
                    f"live results represented only {len(represented_sectors)} sector groups: {sorted(represented_sectors)}"
                ],
            }
        )
    if scenarios_with_multiple_results < 2:
        failures.append(
            {
                "sector": "all",
                "query": "national breadth",
                "failures": [
                    "fewer than two broadened searches returned multiple live candidates for ordering validation"
                ],
            }
        )

    output = {
        "passed": not failures,
        "scenario_count": len(NATIONAL_SCENARIOS),
        "scenarios_with_results": scenarios_with_results,
        "scenarios_with_multiple_results": scenarios_with_multiple_results,
        "total_results": total_results,
        "represented_sectors": sorted(represented_sectors),
        "failures": failures,
        "reports": reports,
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if output["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
