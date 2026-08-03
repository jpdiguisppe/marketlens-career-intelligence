"""Final precision hardening for the cached universal occupation runtime.

The runtime deliberately supports descriptive occupations that are not yet in the
curated catalog. These guards preserve the user's complete phrase when a known
catalog title appears only as a subset, and they normalize harmless conjunctions
when an accepted catalog title is an otherwise exact match.
"""

from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
from typing import Any, Callable

from .occupation_catalog import (
    OCCUPATIONS,
    SOC_MAJOR_GROUPS,
    OccupationConcept,
    OccupationInterpretation,
    normalize_occupation_text,
)

_QUERY_NOISE = frozenset(
    {
        "a",
        "an",
        "and",
        "career",
        "careers",
        "entry",
        "entry-level",
        "for",
        "grad",
        "graduate",
        "intern",
        "internship",
        "internships",
        "job",
        "jobs",
        "junior",
        "level",
        "mid",
        "new",
        "opening",
        "openings",
        "position",
        "positions",
        "role",
        "roles",
        "senior",
        "sr",
        "staff",
    }
)
_SAFE_CONTEXTUAL_SINGLE_WORD_CONCEPTS = frozenset(
    {"architect", "coach", "education_administrator", "server"}
)
_COMPLETE_PHRASE_REASON = (
    "Preserved the complete occupation phrase instead of dropping a meaningful qualifier."
)


def _semantic_tokens(value: str) -> tuple[str, ...]:
    return tuple(
        token
        for token in normalize_occupation_text(value).split()
        if token not in _QUERY_NOISE
    )


def _accepted_titles(concept: OccupationConcept) -> tuple[str, ...]:
    return tuple(
        sorted(
            {normalize_occupation_text(value) for value in {*concept.aliases, concept.canonical_title}},
            key=lambda value: (-len(value.split()), -len(value), value),
        )
    )


_SEMANTIC_ALIASES_MUTABLE: dict[tuple[str, ...], list[tuple[str, OccupationConcept]]] = defaultdict(list)
for _concept in OCCUPATIONS:
    for _alias in {*_concept.aliases, _concept.canonical_title}:
        _key = _semantic_tokens(_alias)
        if _key:
            _SEMANTIC_ALIASES_MUTABLE[_key].append((normalize_occupation_text(_alias), _concept))

_SEMANTIC_ALIASES = {
    key: tuple(values)
    for key, values in _SEMANTIC_ALIASES_MUTABLE.items()
}


def _exact_semantic_concept(query: str) -> tuple[str, OccupationConcept] | None:
    candidates = _SEMANTIC_ALIASES.get(_semantic_tokens(query), ())
    concepts = {concept.key: concept for _, concept in candidates}
    if len(concepts) != 1:
        return None
    concept = next(iter(concepts.values()))
    matching_aliases = sorted(
        alias for alias, candidate in candidates if candidate.key == concept.key
    )
    return matching_aliases[0], concept


def _recognized_concept(
    query: str,
    concept: OccupationConcept,
) -> OccupationInterpretation:
    return OccupationInterpretation(
        status="recognized",
        original_query=query.strip(),
        canonical_query=normalize_occupation_text(query),
        occupation_phrase=concept.canonical_title,
        concept_key=concept.key,
        soc_major_group=concept.soc_major_group,
        major_group_name=SOC_MAJOR_GROUPS[concept.soc_major_group],
        search_family=concept.search_family,
        accepted_titles=_accepted_titles(concept),
        reason="Matched a complete accepted occupation title after normalizing query filler.",
    )


def _complete_generic(
    query: str,
    interpretation: OccupationInterpretation,
) -> OccupationInterpretation:
    phrase = " ".join(_semantic_tokens(query))
    return OccupationInterpretation(
        status="recognized",
        original_query=query.strip(),
        canonical_query=normalize_occupation_text(query),
        occupation_phrase=phrase,
        search_family=interpretation.search_family,
        accepted_titles=(phrase,),
        reason=_COMPLETE_PHRASE_REASON,
    )


def apply_occupation_runtime_hardening(
    runtime_module: Any,
    universal_module: Any,
    compatibility_module: Any,
) -> None:
    if getattr(runtime_module, "_OCCUPATION_RUNTIME_HARDENING_APPLIED", False):
        return

    original_interpret: Callable[[str], OccupationInterpretation] = (
        runtime_module.interpret_occupation_query
    )
    original_title_match: Callable[[str, OccupationInterpretation], bool] = (
        runtime_module.title_matches_occupation
    )

    @lru_cache(maxsize=2_048)
    def interpret(query: str) -> OccupationInterpretation:
        semantic_exact = _exact_semantic_concept(query)
        if semantic_exact is not None:
            _, concept = semantic_exact
            return _recognized_concept(query, concept)

        interpretation = original_interpret(query)
        if not interpretation.recognized or interpretation.concept_key is None:
            return interpretation
        if interpretation.concept_key in _SAFE_CONTEXTUAL_SINGLE_WORD_CONCEPTS:
            return interpretation

        query_tokens = _semantic_tokens(query)
        accepted_token_sets = {
            _semantic_tokens(title) for title in interpretation.accepted_titles
        }
        if query_tokens in accepted_token_sets:
            return interpretation

        # A catalog alias was only a subset of the user's request. Retain every
        # meaningful token so a query such as "police software engineer" cannot
        # silently become the broader "software engineer" occupation.
        return _complete_generic(query, interpretation)

    def title_match(
        title: str,
        interpretation: OccupationInterpretation,
    ) -> bool:
        if interpretation.reason == _COMPLETE_PHRASE_REASON:
            requested = set(_semantic_tokens(interpretation.occupation_phrase or ""))
            candidate = set(_semantic_tokens(title))
            return bool(requested) and requested.issubset(candidate)
        return original_title_match(title, interpretation)

    runtime_module.interpret_occupation_query = interpret
    runtime_module.title_matches_occupation = title_match
    universal_module.interpret_occupation_query = interpret
    universal_module.normalize_occupation_text = runtime_module.normalize_occupation_text
    universal_module.title_matches_occupation = title_match
    compatibility_module.interpret_occupation_query = interpret
    compatibility_module.normalize_occupation_text = runtime_module.normalize_occupation_text
    runtime_module._OCCUPATION_RUNTIME_HARDENING_APPLIED = True


__all__ = ["apply_occupation_runtime_hardening"]
