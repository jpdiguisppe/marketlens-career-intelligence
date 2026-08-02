"""Precision guards for cross-domain occupation-title collisions.

A universal title index improves recall, but single-word titles such as server,
principal, architect, coach, and pilot can appear inside unrelated occupations.
This patch keeps the catalog data simple while enforcing context-sensitive
interpretation and result matching at runtime.
"""

from __future__ import annotations

import re
from typing import Any, Callable

from . import occupation_catalog as catalog


OCCUPATIONAL_HEAD_WORDS = frozenset(
    {
        "accountant",
        "administrator",
        "advisor",
        "aide",
        "analyst",
        "architect",
        "assistant",
        "attendant",
        "attorney",
        "auditor",
        "coach",
        "consultant",
        "counselor",
        "designer",
        "developer",
        "director",
        "dispatcher",
        "doctor",
        "driver",
        "economist",
        "editor",
        "engineer",
        "instructor",
        "investigator",
        "lawyer",
        "manager",
        "mechanic",
        "nurse",
        "officer",
        "operator",
        "pilot",
        "planner",
        "producer",
        "professor",
        "recruiter",
        "representative",
        "researcher",
        "scientist",
        "server",
        "specialist",
        "supervisor",
        "teacher",
        "technician",
        "therapist",
        "trainer",
        "worker",
        "writer",
    }
)
TECHNOLOGY_CONTEXT = frozenset(
    {
        "application",
        "cloud",
        "computer",
        "cyber",
        "data",
        "database",
        "developer",
        "digital",
        "engineer",
        "engineering",
        "infrastructure",
        "network",
        "platform",
        "security",
        "software",
        "system",
        "systems",
        "technology",
        "web",
    }
)
FOOD_SERVICE_CONTEXT = frozenset(
    {
        "banquet",
        "bar",
        "catering",
        "dining",
        "food",
        "hospitality",
        "restaurant",
        "waiter",
        "waitress",
    }
)
EDUCATION_CONTEXT = frozenset(
    {
        "academy",
        "education",
        "educational",
        "elementary",
        "high",
        "principal",
        "school",
        "secondary",
        "student",
    }
)
BUILT_ENVIRONMENT_CONTEXT = frozenset(
    {
        "architect",
        "architectural",
        "architecture",
        "building",
        "construction",
        "landscape",
        "residential",
        "urban",
    }
)
SPORTS_CONTEXT = frozenset(
    {
        "athletic",
        "baseball",
        "basketball",
        "coach",
        "football",
        "soccer",
        "sport",
        "sports",
        "team",
    }
)


def _tokens(value: str) -> set[str]:
    return set(catalog.normalize_occupation_text(value).split())


def _has_multiword_accepted_title(
    value: str,
    interpretation: catalog.OccupationInterpretation,
) -> bool:
    normalized = catalog.normalize_occupation_text(value)
    return any(
        " " in accepted
        and re.search(
            r"(?<![a-z0-9])" + re.escape(accepted) + r"(?![a-z0-9])",
            normalized,
        )
        for accepted in interpretation.accepted_titles
    )


def _generic_technology_interpretation(
    query: str,
    *,
    reason: str,
) -> catalog.OccupationInterpretation:
    normalized = catalog.normalize_occupation_text(query)
    tokens = _tokens(query)
    family = "software" if tokens & {
        "application",
        "cloud",
        "developer",
        "infrastructure",
        "platform",
        "software",
        "web",
    } else "technology"
    return catalog.OccupationInterpretation(
        status="recognized",
        original_query=query.strip(),
        canonical_query=normalized,
        occupation_phrase=" ".join(
            token
            for token in normalized.split()
            if token not in catalog._QUERY_FILLER
        ),
        search_family=family,
        accepted_titles=(normalized,),
        reason=reason,
    )


def _guard_interpretation(
    original: Callable[[str], catalog.OccupationInterpretation],
    query: str,
) -> catalog.OccupationInterpretation:
    interpretation = original(query)
    if not interpretation.recognized or interpretation.concept_key is None:
        return interpretation

    query_tokens = _tokens(query)
    if _has_multiword_accepted_title(query, interpretation):
        return interpretation

    concept_key = interpretation.concept_key
    if concept_key == "server" and len(query_tokens) > 1:
        if query_tokens & TECHNOLOGY_CONTEXT:
            return _generic_technology_interpretation(
                query,
                reason="Interpreted server as a technology qualifier rather than a food-service occupation.",
            )
        if not query_tokens & FOOD_SERVICE_CONTEXT:
            return catalog.OccupationInterpretation(
                status="unrecognized",
                original_query=query.strip(),
                canonical_query=catalog.normalize_occupation_text(query),
                reason="Server requires food-service context when used inside a longer occupation title.",
            )

    if concept_key == "education_administrator":
        if query_tokens & TECHNOLOGY_CONTEXT and not query_tokens & EDUCATION_CONTEXT:
            return _generic_technology_interpretation(
                query,
                reason="Interpreted principal as a seniority modifier in a technology occupation.",
            )
        if "principal" in query_tokens and len(query_tokens) > 1 and not query_tokens & EDUCATION_CONTEXT:
            return catalog.OccupationInterpretation(
                status="unrecognized",
                original_query=query.strip(),
                canonical_query=catalog.normalize_occupation_text(query),
                reason="Principal requires school or education context when used as an occupation title.",
            )

    if concept_key == "architect" and query_tokens & TECHNOLOGY_CONTEXT:
        if not query_tokens & (BUILT_ENVIRONMENT_CONTEXT - {"architect"}):
            return _generic_technology_interpretation(
                query,
                reason="Interpreted architect as a technology occupation rather than a building architect.",
            )

    if concept_key == "coach" and len(query_tokens) > 1:
        if not query_tokens & SPORTS_CONTEXT:
            normalized = catalog.normalize_occupation_text(query)
            return catalog.OccupationInterpretation(
                status="recognized",
                original_query=query.strip(),
                canonical_query=normalized,
                occupation_phrase=normalized,
                search_family="operations",
                accepted_titles=(normalized,),
                reason="Interpreted coach using the supplied professional domain rather than assuming athletics.",
            )

    competing_heads = (query_tokens & OCCUPATIONAL_HEAD_WORDS) - _tokens(
        interpretation.canonical_query
    )
    if competing_heads and len(query_tokens) > 1 and concept_key in {
        "server",
        "education_administrator",
        "architect",
    }:
        if query_tokens & TECHNOLOGY_CONTEXT:
            return _generic_technology_interpretation(
                query,
                reason="Resolved a cross-domain single-word title collision using the complete occupation phrase.",
            )

    return interpretation


def _guard_title_match(
    original: Callable[[str, catalog.OccupationInterpretation], bool],
    title: str,
    interpretation: catalog.OccupationInterpretation,
) -> bool:
    if not original(title, interpretation):
        return False

    title_tokens = _tokens(title)
    concept_key = interpretation.concept_key
    if concept_key == "server":
        if title_tokens == {"server"}:
            return True
        return bool(title_tokens & FOOD_SERVICE_CONTEXT) and not bool(
            title_tokens & TECHNOLOGY_CONTEXT
        )

    if concept_key == "education_administrator" and "principal" in title_tokens:
        return bool(title_tokens & EDUCATION_CONTEXT) and not bool(
            title_tokens & TECHNOLOGY_CONTEXT
        )

    if concept_key == "architect" and title_tokens & TECHNOLOGY_CONTEXT:
        return bool(title_tokens & (BUILT_ENVIRONMENT_CONTEXT - {"architect"}))

    if concept_key == "coach" and len(title_tokens) > 1:
        return bool(title_tokens & SPORTS_CONTEXT)

    return True


def apply_occupation_precision_guards(universal_module: Any) -> None:
    if getattr(catalog, "_OCCUPATION_PRECISION_GUARDS_APPLIED", False):
        return

    original_interpret = catalog.interpret_occupation_query
    original_title_match = catalog.title_matches_occupation

    def interpret(query: str) -> catalog.OccupationInterpretation:
        return _guard_interpretation(original_interpret, query)

    def title_match(
        title: str,
        interpretation: catalog.OccupationInterpretation,
    ) -> bool:
        return _guard_title_match(original_title_match, title, interpretation)

    catalog.interpret_occupation_query = interpret
    catalog.title_matches_occupation = title_match
    # The universal adapter imports these callables directly, so update its
    # module globals as well as the catalog exports.
    universal_module.interpret_occupation_query = interpret
    universal_module.title_matches_occupation = title_match
    catalog._OCCUPATION_PRECISION_GUARDS_APPLIED = True
