"""Apply universal occupation interpretation to the existing job-search stack."""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Any
from urllib.parse import quote_plus

from .occupation_catalog import (
    OccupationInterpretation,
    interpret_occupation_query,
    normalize_occupation_text,
    title_matches_occupation,
)


SOURCE_TERM_ENRICHMENTS: dict[str, frozenset[str]] = {
    "CityofPhiladelphia": frozenset(
        {
            "police officer",
            "law enforcement officer",
            "detective",
            "correctional officer",
            "firefighter",
            "security officer",
            "public safety dispatcher",
            "registered nurse",
            "medical assistant",
            "recreation worker",
            "coach",
            "custodian",
            "janitor",
            "truck driver",
            "construction laborer",
            "building inspector",
            "economist",
            "financial analyst",
            "business analyst",
            "market research analyst",
        }
    ),
    "HealthFederationOfPhiladelphia": frozenset(
        {
            "registered nurse",
            "nurse practitioner",
            "medical assistant",
            "community health worker",
            "epidemiologist",
            "mental health counselor",
            "case manager",
            "social worker",
        }
    ),
    "KIPP": frozenset(
        {
            "elementary school teacher",
            "secondary school teacher",
            "high school teacher",
            "special education teacher",
            "preschool teacher",
            "teaching assistant",
            "teacher aide",
            "academic advisor",
            "school administrator",
        }
    ),
    "AECOM2": frozenset(
        {
            "systems application engineer",
            "system application engineer",
            "systems engineer",
            "structural engineer",
            "aerospace engineer",
            "industrial engineer",
            "engineering technician",
            "surveyor",
            "construction manager",
        }
    ),
    "CRB": frozenset(
        {
            "systems application engineer",
            "application systems engineer",
            "systems engineer",
            "industrial engineer",
            "engineering technician",
            "construction manager",
        }
    ),
    "BoschGroup": frozenset(
        {
            "systems application engineer",
            "application engineer",
            "systems engineer",
            "software engineer",
            "quality assurance engineer",
            "electrical engineer",
            "mechanical engineer",
            "industrial maintenance technician",
            "automotive technician",
        }
    ),
    "Bosch-HomeComfort": frozenset(
        {
            "hvac installer",
            "hvac technician",
            "plumber",
            "electrician",
            "field service technician",
            "systems application engineer",
        }
    ),
    "VeoliaEnvironnementSA": frozenset(
        {
            "environmental engineer",
            "environmental scientist",
            "industrial maintenance technician",
            "electrician",
            "plumber",
            "heavy equipment operator",
            "plant operator",
        }
    ),
    "Eurofins": frozenset(
        {
            "laboratory technician",
            "research scientist",
            "chemist",
            "biologist",
            "epidemiologist",
            "quality inspector",
        }
    ),
    "SGS": frozenset(
        {
            "laboratory technician",
            "engineering technician",
            "quality inspector",
            "environmental scientist",
            "industrial engineer",
        }
    ),
    "USPhysicalTherapy2": frozenset(
        {
            "physical therapist",
            "physical therapist assistant",
            "occupational therapist",
            "occupational therapy assistant",
            "athletic coach",
        }
    ),
    "InformaGroupPlc": frozenset(
        {
            "economist",
            "market research analyst",
            "journalist",
            "writer",
            "editor",
            "public relations specialist",
            "sports analyst",
        }
    ),
    "NBCUniversal3": frozenset(
        {
            "journalist",
            "reporter",
            "writer",
            "editor",
            "producer",
            "video editor",
            "sports analyst",
            "announcer",
            "graphic designer",
        }
    ),
    "Evolution": frozenset(
        {
            "accountant",
            "financial analyst",
            "bartender",
            "server",
            "customer service representative",
            "security officer",
        }
    ),
    "PublicStorage": frozenset(
        {
            "customer service representative",
            "property manager",
            "maintenance technician",
            "district manager",
            "sales representative",
        }
    ),
    "Experian": frozenset(
        {
            "accountant",
            "auditor",
            "financial analyst",
            "business analyst",
            "market research analyst",
            "economist",
            "data analyst",
            "information security analyst",
        }
    ),
}

TECHNOLOGY_SOURCE_IDENTIFIERS = frozenset(
    {
        "AECOM2",
        "CRB",
        "BoschGroup",
        "Bosch-HomeComfort",
        "VeoliaEnvironnementSA",
        "SGS",
    }
)

_SHORT_UNKNOWN_ACRONYM = re.compile(r"^[A-Za-z]{2,5}$")


def _enrich_smartrecruiters_sources(source_expansion: Any) -> None:
    enriched = []
    for source in source_expansion.SMARTRECRUITERS_SOURCES:
        extra_terms = SOURCE_TERM_ENRICHMENTS.get(source.identifier, frozenset())
        extra_families = (
            frozenset({"technology"})
            if source.identifier in TECHNOLOGY_SOURCE_IDENTIFIERS
            else frozenset()
        )
        if extra_terms or extra_families:
            source = replace(
                source,
                query_terms=source.query_terms | extra_terms,
                role_families=source.role_families | extra_families,
            )
        enriched.append(source)
    source_expansion.SMARTRECRUITERS_SOURCES = tuple(enriched)


def _interpretation_for_search(query: str) -> OccupationInterpretation:
    return interpret_occupation_query(query)


def _clarification_result(
    job_search: Any,
    query: str,
    location: str | None,
    level: str | None,
    interpretation: OccupationInterpretation,
) -> Any:
    resolved_level = job_search.resolve_job_level(query, level)
    suggestions = [
        f"Choose one meaning: {suggestion}."
        for suggestion in interpretation.suggestions
    ]
    suggestions.append("Spell out the occupation title before searching so MarketLens can keep results precise.")
    return job_search.JobSearchResults(
        query=query.strip(),
        location=location.strip() if location and location.strip() else None,
        level=resolved_level,
        providers_searched=[],
        results=[],
        warnings=[
            f"MarketLens did not search providers because '{query.strip()}' is ambiguous. "
            f"{interpretation.reason}"
        ],
        role_family=None,
        industry=None,
        source_coverage=[],
        search_suggestions=suggestions,
        external_search_links=[],
    )


def _unknown_acronym_result(
    job_search: Any,
    query: str,
    location: str | None,
    level: str | None,
) -> Any:
    resolved_level = job_search.resolve_job_level(query, level)
    return job_search.JobSearchResults(
        query=query.strip(),
        location=location.strip() if location and location.strip() else None,
        level=resolved_level,
        providers_searched=[],
        results=[],
        warnings=[
            f"MarketLens could not safely identify the occupation abbreviation '{query.strip()}'. "
            "No providers were searched because guessing could return unrelated jobs."
        ],
        role_family=None,
        industry=None,
        source_coverage=[],
        search_suggestions=[
            "Spell out the complete occupation title.",
            "Include a discipline or function, such as 'civil engineer', 'financial analyst', or 'registered nurse'.",
            "Manual Smart Fit comparison still works for any posting copied from another job board.",
        ],
        external_search_links=[],
    )


def _occupation_external_links(
    job_search: Any,
    interpretation: OccupationInterpretation,
    location: str | None,
    level: str,
) -> list[Any]:
    if not interpretation.recognized or not interpretation.occupation_phrase:
        return []
    occupation = interpretation.occupation_phrase
    external_query = occupation
    if level == "intern":
        external_query += " internship"
    elif level == "entry":
        external_query += " entry level"
    if location:
        external_query += f" {location.strip()}"

    quoted = quote_plus(external_query)
    group = interpretation.soc_major_group
    links: list[Any] = []

    if group in {
        "11", "13", "15", "17", "19", "21", "23", "25", "27",
        "29", "31", "33", "43", "55",
    }:
        links.append(
            job_search.ExternalSearchLink(
                label="USAJOBS occupation search",
                url=f"https://www.usajobs.gov/Search/Results?k={quote_plus(occupation)}&l={quote_plus(location or 'United States')}",
                note="Official federal employment search. MarketLens opens it separately and does not import or verify the results.",
            )
        )

    if group in {"11", "13", "17", "19", "21", "23", "25", "27", "29", "31", "33", "37", "43", "47", "49", "53"}:
        links.append(
            job_search.ExternalSearchLink(
                label="Government and public-sector search",
                url=f"https://www.google.com/search?q={quote_plus('site:governmentjobs.com/jobs ' + external_query)}",
                note="Indexed public-sector listings. MarketLens does not scrape the destination site.",
            )
        )

    if group in {"35", "37", "39", "45", "47", "49", "51", "53"}:
        links.append(
            job_search.ExternalSearchLink(
                label="Apprenticeship.gov Job Finder",
                url=f"https://www.apprenticeship.gov/finder/listings?search={quoted}",
                note="Official U.S. Department of Labor apprenticeship finder; search filters may need to be entered again on the destination page.",
            )
        )

    return links


def _dedupe_links(links: list[Any]) -> list[Any]:
    seen: set[str] = set()
    deduped: list[Any] = []
    for link in links:
        if link.url in seen:
            continue
        seen.add(link.url)
        deduped.append(link)
    return deduped


def apply_universal_occupation_search(job_search: Any, source_expansion: Any) -> None:
    if getattr(job_search, "_UNIVERSAL_OCCUPATION_SEARCH_APPLIED", False):
        return

    _enrich_smartrecruiters_sources(source_expansion)

    original_query_role_family = job_search._query_role_family
    original_query_job_function = job_search._query_job_function
    original_parse_intent = job_search.parse_job_search_intent
    original_query_terms = job_search._query_terms
    original_matches_requested_role = job_search._matches_requested_role
    original_score_job = job_search._score_job
    original_source_search_terms = source_expansion._search_terms
    original_search = job_search.search_external_jobs

    def query_role_family(query: str) -> Any:
        existing = original_query_role_family(query)
        if existing is not None:
            return existing
        interpretation = _interpretation_for_search(query)
        return interpretation.search_family if interpretation.recognized else None

    def query_job_function(query: str) -> Any:
        existing = original_query_job_function(query)
        if existing is not None:
            return existing
        interpretation = _interpretation_for_search(query)
        return interpretation.search_family if interpretation.recognized else None

    def parse_job_search_intent(
        query: str,
        location: str | None = None,
        level: str | None = None,
    ) -> Any:
        interpretation = _interpretation_for_search(query)
        routed_query = interpretation.canonical_query if interpretation.recognized else query
        parsed = original_parse_intent(routed_query, location, level)
        family = interpretation.search_family if interpretation.recognized else parsed.job_function
        return job_search.JobSearchIntent(
            query=routed_query.strip(),
            job_function=family,
            industry=parsed.industry,
            level=parsed.level,
            location=parsed.location,
        )

    def query_terms(query: str) -> list[str]:
        terms = set(original_query_terms(query))
        interpretation = _interpretation_for_search(query)
        if interpretation.recognized:
            for title in interpretation.accepted_titles[:6]:
                terms.update(
                    token
                    for token in normalize_occupation_text(title).split()
                    if len(token) > 2
                )
        return sorted(terms)

    def matches_requested_role(
        title: str,
        description: str,
        query: str,
        level: Any = None,
    ) -> bool:
        interpretation = _interpretation_for_search(query)
        if interpretation.status == "ambiguous":
            return False
        if interpretation.recognized:
            if not title_matches_occupation(title, interpretation):
                return False
            resolved_level = level or job_search.resolve_job_level(query, None)
            return job_search._matches_level(title, description, resolved_level)
        return original_matches_requested_role(title, description, query, level)

    def score_job(
        title: str,
        description: str,
        query: str,
        level: str | None = None,
        company: str | None = None,
    ) -> int:
        interpretation = _interpretation_for_search(query)
        if interpretation.status == "ambiguous":
            return 0
        if not interpretation.recognized:
            return original_score_job(
                title=title,
                description=description,
                query=query,
                level=level,
                company=company,
            )
        if not title_matches_occupation(title, interpretation):
            return 0
        resolved_level = job_search.resolve_job_level(query, level)
        if not job_search._matches_level(title, description, resolved_level):
            return 0
        if not job_search._matches_requested_industry(title, description, query, company=company):
            return 0

        original_score = original_score_job(
            title=title,
            description=description,
            query=query,
            level=level,
            company=company,
        )
        title_tokens = set(normalize_occupation_text(title).split())
        occupation_tokens = set(normalize_occupation_text(interpretation.occupation_phrase or "").split())
        deterministic_score = (
            36
            + 4 * len(title_tokens & occupation_tokens)
            + job_search._level_score_bonus(title, description, resolved_level)
        )
        return max(original_score, deterministic_score)

    def source_search_terms(query: str) -> tuple[str, ...]:
        interpretation = _interpretation_for_search(query)
        if not interpretation.recognized or not interpretation.occupation_phrase:
            return original_source_search_terms(query)
        candidates = [interpretation.occupation_phrase]
        candidates.extend(
            title
            for title in interpretation.accepted_titles
            if title != interpretation.occupation_phrase and len(title) >= 4
        )
        unique: list[str] = []
        for candidate in candidates:
            normalized = normalize_occupation_text(candidate)
            if normalized and normalized not in unique:
                unique.append(normalized)
            if len(unique) >= source_expansion.MAX_SEARCH_PASSES_PER_SOURCE:
                break
        return tuple(unique)

    def search_external_jobs(
        query: str,
        location: str | None = None,
        limit: int = 15,
        level: str | None = None,
    ) -> Any:
        interpretation = _interpretation_for_search(query)
        if interpretation.status == "ambiguous":
            return _clarification_result(job_search, query, location, level, interpretation)
        if interpretation.status == "unrecognized" and _SHORT_UNKNOWN_ACRONYM.fullmatch(query.strip()):
            return _unknown_acronym_result(job_search, query, location, level)

        routed_query = interpretation.canonical_query if interpretation.recognized else query
        resolved_level = job_search.resolve_job_level(query, level)
        result = original_search(
            query=routed_query,
            location=location,
            limit=limit,
            level=resolved_level,
        )

        if not interpretation.recognized:
            return result

        suggestions = list(result.search_suggestions)
        occupation_note = f"Interpreted '{query.strip()}' as '{interpretation.occupation_phrase}'"
        if interpretation.major_group_name:
            occupation_note += f" in {interpretation.major_group_name}"
        occupation_note += "."
        suggestions.insert(0, occupation_note)

        warnings = [warning for warning in result.warnings if not warning.startswith("No matching")]
        if not result.results:
            failed = [coverage for coverage in result.source_coverage if coverage.status == "failed"]
            if failed:
                warnings.insert(
                    0,
                    f"MarketLens understood the occupation '{interpretation.occupation_phrase}', "
                    "but at least one public provider failed and no matching posting was returned. "
                    "Use the external searches or try again later.",
                )
            else:
                warnings.insert(
                    0,
                    f"MarketLens understood the occupation '{interpretation.occupation_phrase}', "
                    "but its configured public sources did not contain a current matching posting "
                    "for these filters. This is a coverage or availability result, not an interpretation failure.",
                )

        external_links = _dedupe_links(
            [
                *result.external_search_links,
                *_occupation_external_links(job_search, interpretation, result.location, result.level),
            ]
        )

        return job_search.JobSearchResults(
            query=query.strip(),
            location=result.location,
            level=result.level,
            providers_searched=result.providers_searched,
            results=result.results,
            warnings=warnings,
            role_family=interpretation.search_family or result.role_family,
            industry=result.industry,
            source_coverage=result.source_coverage,
            search_suggestions=suggestions,
            external_search_links=external_links,
        )

    job_search._query_role_family = query_role_family
    job_search._query_job_function = query_job_function
    job_search.parse_job_search_intent = parse_job_search_intent
    job_search._query_terms = query_terms
    job_search._matches_requested_role = matches_requested_role
    job_search._score_job = score_job
    source_expansion._search_terms = source_search_terms
    job_search.search_external_jobs = search_external_jobs
    job_search._UNIVERSAL_OCCUPATION_SEARCH_APPLIED = True
