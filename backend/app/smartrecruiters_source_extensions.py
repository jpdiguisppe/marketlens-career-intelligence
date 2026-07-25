"""Additional verified public SmartRecruiters boards for sector coverage."""

from __future__ import annotations

from typing import Any

from .smartrecruiters_sources import SmartRecruitersSource, _source


ADDITIONAL_SMARTRECRUITERS_SOURCES: tuple[SmartRecruitersSource, ...] = (
    _source(
        "SyngentaGroup",
        "Syngenta Group",
        {
            "agriculture",
            "agricultural",
            "agricultural technician",
            "agronomist",
            "agronomy",
            "crop science",
            "plant science",
            "plant scientist",
            "seed production",
            "field production",
            "farm manager",
            "biology",
            "chemistry",
            "scientist",
            "research",
            "laboratory",
            "supply chain",
            "manufacturing",
            "operations",
            "data analyst",
        },
        role_families={"operations", "data", "finance", "marketing", "healthcare"},
        industries={
            "agriculture",
            "life_sciences",
            "manufacturing",
            "environmental_services",
        },
        fallback_priority=9,
    ),
    _source(
        "Dominos",
        "Domino's",
        {
            "delivery driver",
            "driver",
            "restaurant",
            "food service",
            "food preparation",
            "customer service",
            "cashier",
            "cook",
            "team member",
            "shift manager",
            "general manager",
            "warehouse",
            "maintenance",
        },
        role_families={"operations", "marketing"},
        industries={"hospitality", "retail", "transportation", "logistics"},
        fallback_priority=8,
    ),
)


def apply_smartrecruiters_source_extensions(
    source_registry: Any,
    source_expansion: Any,
) -> None:
    """Expose one deduplicated source tuple to the registry and search adapter."""

    existing = tuple(source_registry.SMARTRECRUITERS_SOURCES)
    existing_ids = {source.identifier for source in existing}
    additions = tuple(
        source
        for source in ADDITIONAL_SMARTRECRUITERS_SOURCES
        if source.identifier not in existing_ids
    )
    combined = (*existing, *additions)
    source_registry.SMARTRECRUITERS_SOURCES = combined
    source_expansion.SMARTRECRUITERS_SOURCES = combined
