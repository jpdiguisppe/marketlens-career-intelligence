from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.job_source_registry import JobSourceRegistryEntry, Provider, find_source

JobLevel = Literal["any", "intern", "entry", "mid", "senior"]

MAX_INDUSTRY_ROUTED_SOURCES = 16
MIN_PROVIDER_FALLBACK_SOURCES = 2

INDUSTRY_ADJACENCIES: dict[str, frozenset[str]] = {
    "sports": frozenset({"entertainment", "media", "gaming"}),
    "entertainment": frozenset({"media", "gaming", "sports"}),
    "healthcare": frozenset({"life_sciences", "technology"}),
    "financial_services": frozenset({"fintech", "technology"}),
    "education": frozenset({"technology"}),
    "nonprofit": frozenset({"education", "healthcare", "media"}),
    "media": frozenset({"entertainment", "gaming", "technology"}),
}


@dataclass(frozen=True)
class SourceRoutingPlan:
    greenhouse_identifiers: tuple[str, ...]
    lever_identifiers: tuple[str, ...]
    greenhouse_note: str
    lever_note: str
    routed: bool
    direct_industry_matches: int


def _registered_entries(
    provider: Provider,
    identifiers: list[str] | tuple[str, ...],
) -> list[JobSourceRegistryEntry]:
    entries: list[JobSourceRegistryEntry] = []
    for identifier in identifiers:
        entry = find_source(identifier, provider)
        if entry is not None and entry.enabled:
            entries.append(entry)
    return entries


def _source_score(
    entry: JobSourceRegistryEntry,
    *,
    industry: str,
    job_function: str | None,
    level: JobLevel,
    location: str | None,
) -> int:
    score = 0
    adjacent_industries = INDUSTRY_ADJACENCIES.get(industry, frozenset())

    if industry in entry.industries:
        score += 100
    elif adjacent_industries.intersection(entry.industries):
        score += 55

    if job_function:
        if job_function in entry.role_families:
            score += 24
        elif job_function == "technology" and {
            "software",
            "data",
            "cybersecurity",
            "product",
        }.intersection(entry.role_families):
            score += 18
        else:
            score -= 12

    if level in {"intern", "entry"}:
        early_career_bonus = {
            "strong": 18,
            "general": 4,
            "unknown": 0,
            "limited": -10,
        }
        score += early_career_bonus[entry.early_career_relevance]

    normalized_location = (location or "").strip().lower()
    if normalized_location:
        if normalized_location == "remote" and "remote" in entry.geographic_focus:
            score += 8
        elif normalized_location != "remote" and "united_states" in entry.geographic_focus:
            score += 6
        elif "varies_by_posting" in entry.geographic_focus:
            score += 1

    return score


def _ensure_provider_fallbacks(
    selected: list[JobSourceRegistryEntry],
    ranked_entries: list[JobSourceRegistryEntry],
    provider: Provider,
) -> None:
    provider_count = sum(entry.provider == provider for entry in selected)
    for entry in ranked_entries:
        if provider_count >= MIN_PROVIDER_FALLBACK_SOURCES:
            return
        if entry.provider != provider or entry in selected:
            continue
        if len(selected) >= MAX_INDUSTRY_ROUTED_SOURCES:
            selected.pop()
        selected.append(entry)
        provider_count += 1


def _provider_note(
    provider_label: str,
    *,
    selected_count: int,
    configured_count: int,
    industry: str | None,
    job_function: str | None,
    level: JobLevel,
    location: str | None,
    direct_match_count: int,
    routed: bool,
) -> str:
    if not routed:
        return (
            f"Source routing kept all {configured_count} configured {provider_label} boards because no "
            "industry was detected. Job function, experience level, and location still filter and rank postings."
        )

    dimensions = [f"industry={industry}"]
    if job_function:
        dimensions.append(f"function={job_function}")
    if level != "any":
        dimensions.append(f"level={level}")
    if location:
        dimensions.append(f"location={location}")

    match_note = (
        f"{direct_match_count} exact-industry registry match{'es' if direct_match_count != 1 else ''} were available."
        if direct_match_count
        else "No exact-industry registry match was available, so adjacent and general fallback sources were used."
    )
    return (
        f"Intent-aware routing selected {selected_count} of {configured_count} configured {provider_label} boards "
        f"for {', '.join(dimensions)}. {match_note}"
    )


def build_source_routing_plan(
    *,
    greenhouse_identifiers: list[str] | tuple[str, ...],
    lever_identifiers: list[str] | tuple[str, ...],
    industry: str | None,
    job_function: str | None,
    level: JobLevel,
    location: str | None,
) -> SourceRoutingPlan:
    greenhouse_entries = _registered_entries("greenhouse", greenhouse_identifiers)
    lever_entries = _registered_entries("lever", lever_identifiers)
    all_entries = greenhouse_entries + lever_entries

    if industry is None:
        greenhouse_selected = tuple(entry.identifier for entry in greenhouse_entries)
        lever_selected = tuple(entry.identifier for entry in lever_entries)
        return SourceRoutingPlan(
            greenhouse_identifiers=greenhouse_selected,
            lever_identifiers=lever_selected,
            greenhouse_note=_provider_note(
                "Greenhouse",
                selected_count=len(greenhouse_selected),
                configured_count=len(greenhouse_entries),
                industry=None,
                job_function=job_function,
                level=level,
                location=location,
                direct_match_count=0,
                routed=False,
            ),
            lever_note=_provider_note(
                "Lever",
                selected_count=len(lever_selected),
                configured_count=len(lever_entries),
                industry=None,
                job_function=job_function,
                level=level,
                location=location,
                direct_match_count=0,
                routed=False,
            ),
            routed=False,
            direct_industry_matches=0,
        )

    original_order = {
        (entry.provider, entry.identifier): index
        for index, entry in enumerate(all_entries)
    }
    ranked_entries = sorted(
        all_entries,
        key=lambda entry: (
            -_source_score(
                entry,
                industry=industry,
                job_function=job_function,
                level=level,
                location=location,
            ),
            original_order[(entry.provider, entry.identifier)],
        ),
    )

    direct_entries = [entry for entry in ranked_entries if industry in entry.industries]
    adjacent_industries = INDUSTRY_ADJACENCIES.get(industry, frozenset())
    adjacent_entries = [
        entry
        for entry in ranked_entries
        if entry not in direct_entries and adjacent_industries.intersection(entry.industries)
    ]
    fallback_entries = [
        entry
        for entry in ranked_entries
        if entry not in direct_entries and entry not in adjacent_entries
    ]

    selected = (direct_entries + adjacent_entries + fallback_entries)[:MAX_INDUSTRY_ROUTED_SOURCES]
    _ensure_provider_fallbacks(selected, ranked_entries, "greenhouse")
    _ensure_provider_fallbacks(selected, ranked_entries, "lever")
    selected.sort(key=lambda entry: ranked_entries.index(entry))

    greenhouse_selected = tuple(
        entry.identifier for entry in selected if entry.provider == "greenhouse"
    )
    lever_selected = tuple(
        entry.identifier for entry in selected if entry.provider == "lever"
    )
    greenhouse_direct_matches = sum(
        entry.provider == "greenhouse" and industry in entry.industries
        for entry in all_entries
    )
    lever_direct_matches = sum(
        entry.provider == "lever" and industry in entry.industries
        for entry in all_entries
    )

    return SourceRoutingPlan(
        greenhouse_identifiers=greenhouse_selected,
        lever_identifiers=lever_selected,
        greenhouse_note=_provider_note(
            "Greenhouse",
            selected_count=len(greenhouse_selected),
            configured_count=len(greenhouse_entries),
            industry=industry,
            job_function=job_function,
            level=level,
            location=location,
            direct_match_count=greenhouse_direct_matches,
            routed=True,
        ),
        lever_note=_provider_note(
            "Lever",
            selected_count=len(lever_selected),
            configured_count=len(lever_entries),
            industry=industry,
            job_function=job_function,
            level=level,
            location=location,
            direct_match_count=lever_direct_matches,
            routed=True,
        ),
        routed=True,
        direct_industry_matches=len(direct_entries),
    )
