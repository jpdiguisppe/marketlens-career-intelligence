"""Precision hardening for the cached universal occupation runtime."""

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
        "a", "an", "and", "career", "careers", "entry", "entry-level",
        "for", "grad", "graduate", "intern", "internship", "internships",
        "job", "jobs", "junior", "level", "mid", "new", "opening",
        "openings", "position", "positions", "role", "roles", "senior",
        "sr", "staff",
    }
)
_CONTEXT_SENSITIVE_CONCEPTS = frozenset(
    {"architect", "coach", "education_administrator", "server"}
)
_COMPLETE_PHRASE_REASON = (
    "Preserved the complete occupation phrase instead of dropping a meaningful qualifier."
)
_FUZZY_MATCH_REASON = "Matched a high-confidence spelling variant."


def _semantic_tokens(value: str) -> tuple[str, ...]:
    return tuple(
        token
        for token in normalize_occupation_text(value).split()
        if token not in _QUERY_NOISE
    )


def _accepted_titles(concept: OccupationConcept) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                normalize_occupation_text(value)
                for value in {*concept.aliases, concept.canonical_title}
            },
            key=lambda value: (-len(value.split()), -len(value), value),
        )
    )


_SEMANTIC_ALIASES_MUTABLE: dict[
    tuple[str, ...], list[tuple[str, OccupationConcept]]
] = defaultdict(list)
for _concept in OCCUPATIONS:
    for _alias in {*_concept.aliases, _concept.canonical_title}:
        _key = _semantic_tokens(_alias)
        if _key:
            _SEMANTIC_ALIASES_MUTABLE[_key].append(
                (normalize_occupation_text(_alias), _concept)
            )

_SEMANTIC_ALIASES = {
    key: tuple(values) for key, values in _SEMANTIC_ALIASES_MUTABLE.items()
}


def _exact_semantic_concept(query: str) -> tuple[str, OccupationConcept] | None:
    candidates = _SEMANTIC_ALIASES.get(_semantic_tokens(query), ())
    concepts = {concept.key: concept for _, concept in candidates}
    if len(concepts) != 1:
        return None
    concept = next(iter(concepts.values()))
    aliases = sorted(
        alias for alias, candidate in candidates if candidate.key == concept.key
    )
    return aliases[0], concept


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
        if interpretation.concept_key in _CONTEXT_SENSITIVE_CONCEPTS:
            return interpretation
        if interpretation.reason == _FUZZY_MATCH_REASON:
            return interpretation

        query_tokens = _semantic_tokens(query)
        accepted_token_sets = {
            _semantic_tokens(title) for title in interpretation.accepted_titles
        }
        if query_tokens in accepted_token_sets:
            return interpretation
        return _complete_generic(query, interpretation)

    def title_match(
        title: str,
        interpretation: OccupationInterpretation,
    ) -> bool:
        if interpretation.reason == _COMPLETE_PHRASE_REASON:
            requested = set(
                _semantic_tokens(interpretion_phrase)
                if (interpretion_phrase := interpretation.occupation_phrase)
                else ()
            )
            candidate = set(_semantic_tokens(title))
            return bool(requested) and requested.issubset(candidate)

        if original_title_match(title, interpretation):
            return True
        if (
            interpretation.concept_key is None
            or interpretation.concept_key in _CONTEXT_SENSITIVE_CONCEPTS
        ):
            return False

        candidate_tokens = set(_semantic_tokens(title))
        for accepted_title in interpretation.accepted_titles:
            accepted_tokens = set(_semantic_tokens(accepted_title))
            if len(accepted_tokens) >= 2 and accepted_tokens.issubset(
                candidate_tokens
            ):
                return True
        return False

    runtime_module.interpret_occupation_query = interpret
    runtime_module.title_matches_occupation = title_match
    universal_module.interpret_occupation_query = interpret
    universal_module.normalize_occupation_text = runtime_module.normalize_occupation_text
    universal_module.title_matches_occupation = title_match
    compatibility_module.interpret_occupation_query = interpret
    compatibility_module.normalize_occupation_text = runtime_module.normalize_occupation_text
    runtime_module._OCCUPATION_RUNTIME_HARDENING_APPLIED = True


__all__ = ["apply_occupation_runtime_hardening"]
