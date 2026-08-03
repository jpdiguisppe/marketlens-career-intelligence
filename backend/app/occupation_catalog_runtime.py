"""Fast deterministic runtime for the cross-sector occupation catalog.

The raw catalog is intentionally data-oriented. This module owns production
interpretation, spelling repair, ambiguity handling, and strict title matching.
It is cached because the same query is evaluated repeatedly while providers are
ranked and candidate postings are scored.
"""

from __future__ import annotations

import difflib
import re
from collections import defaultdict
from functools import lru_cache

from .occupation_catalog import (
    AMBIGUOUS_ACRONYMS,
    OCCUPATIONS,
    SOC_MAJOR_GROUPS,
    OccupationConcept,
    OccupationInterpretation,
    normalize_occupation_text,
    registry_summary,
)

_QUERY_MODIFIERS = frozenset(
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

_OCCUPATIONAL_HEAD_WORDS = frozenset(
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
        "barber",
        "bartender",
        "broker",
        "carpenter",
        "chemist",
        "clerk",
        "coach",
        "consultant",
        "cook",
        "coordinator",
        "counselor",
        "designer",
        "detective",
        "developer",
        "director",
        "dispatcher",
        "doctor",
        "driver",
        "economist",
        "editor",
        "electrician",
        "engineer",
        "farmer",
        "firefighter",
        "guard",
        "instructor",
        "investigator",
        "journalist",
        "lawyer",
        "librarian",
        "machinist",
        "manager",
        "mechanic",
        "nurse",
        "officer",
        "operator",
        "paralegal",
        "pharmacist",
        "photographer",
        "physician",
        "pilot",
        "planner",
        "plumber",
        "producer",
        "professor",
        "recruiter",
        "reporter",
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

_TECHNOLOGY_CONTEXT = frozenset(
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
_FOOD_SERVICE_CONTEXT = frozenset(
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
_EDUCATION_CONTEXT = frozenset(
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
_BUILT_ENVIRONMENT_CONTEXT = frozenset(
    {
        "architectural",
        "architecture",
        "building",
        "construction",
        "landscape",
        "residential",
        "urban",
    }
)
_SPORTS_CONTEXT = frozenset(
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

_FAMILY_KEYWORDS: tuple[tuple[str, frozenset[str]], ...] = (
    ("legal", frozenset({"attorney", "lawyer", "legal", "paralegal", "court", "contract"})),
    ("healthcare", frozenset({"health", "medical", "nurse", "physician", "therapy", "therapist", "pharmacy", "dental"})),
    ("cybersecurity", frozenset({"cyber", "security", "infosec", "soc"})),
    ("software", frozenset({"software", "developer", "application", "web", "programmer", "test"})),
    ("data", frozenset({"data", "analytics", "scientist", "economist", "statistician", "research"})),
    ("marketing", frozenset({"marketing", "sales", "communications", "public", "relations", "writer", "editor", "media"})),
    ("design", frozenset({"design", "designer", "photographer"})),
    ("technology", frozenset({"engineer", "engineering", "network", "systems", "system", "architect"})),
)


def _normalize_alias(value: str) -> str:
    return normalize_occupation_text(value)


_ALIAS_CONCEPTS_MUTABLE: dict[str, list[OccupationConcept]] = defaultdict(list)
for _concept in OCCUPATIONS:
    for _alias in {*_concept.aliases, _concept.canonical_title}:
        _normalized_alias = _normalize_alias(_alias)
        if _concept not in _ALIAS_CONCEPTS_MUTABLE[_normalized_alias]:
            _ALIAS_CONCEPTS_MUTABLE[_normalized_alias].append(_concept)

_ALIAS_CONCEPTS: dict[str, tuple[OccupationConcept, ...]] = {
    alias: tuple(sorted(concepts, key=lambda concept: concept.key))
    for alias, concepts in _ALIAS_CONCEPTS_MUTABLE.items()
}
_SORTED_ALIASES = tuple(
    sorted(
        _ALIAS_CONCEPTS,
        key=lambda alias: (-len(alias.split()), -len(alias), alias),
    )
)
_ALIASES_BY_WORD_COUNT: dict[int, tuple[str, ...]] = {
    count: tuple(alias for alias in _SORTED_ALIASES if len(alias.split()) == count)
    for count in {len(alias.split()) for alias in _SORTED_ALIASES}
}


def _core_tokens(query: str) -> tuple[str, ...]:
    return tuple(
        token
        for token in normalize_occupation_text(query).split()
        if token not in _QUERY_MODIFIERS
    )


def _core_query(query: str) -> str:
    return " ".join(_core_tokens(query))


def _pure_ambiguous_acronym(query: str) -> str | None:
    tokens = _core_tokens(query)
    if len(tokens) != 1:
        return None
    token = tokens[0]
    return token if token in AMBIGUOUS_ACRONYMS else None


def is_ambiguous_occupation_query(query: str) -> bool:
    return _pure_ambiguous_acronym(query) is not None


def _accepted_titles(concept: OccupationConcept) -> tuple[str, ...]:
    return tuple(
        sorted(
            {_normalize_alias(value) for value in {*concept.aliases, concept.canonical_title}},
            key=lambda value: (-len(value.split()), -len(value), value),
        )
    )


def _replace_core_phrase(query: str, matched_alias: str, canonical: str) -> str:
    normalized = normalize_occupation_text(query)
    pattern = re.compile(
        r"(?<![a-z0-9])" + re.escape(matched_alias) + r"(?![a-z0-9])"
    )
    replaced = pattern.sub(canonical, normalized, count=1)
    return re.sub(r"\s+", " ", replaced).strip()


def _recognized(
    query: str,
    concept: OccupationConcept,
    matched_alias: str,
    reason: str,
) -> OccupationInterpretation:
    return OccupationInterpretation(
        status="recognized",
        original_query=query.strip(),
        canonical_query=_replace_core_phrase(query, matched_alias, concept.canonical_title),
        occupation_phrase=concept.canonical_title,
        concept_key=concept.key,
        soc_major_group=concept.soc_major_group,
        major_group_name=SOC_MAJOR_GROUPS[concept.soc_major_group],
        search_family=concept.search_family,
        accepted_titles=_accepted_titles(concept),
        reason=reason,
    )


def _generic_family(tokens: set[str]) -> str:
    for family, keywords in _FAMILY_KEYWORDS:
        if tokens & keywords:
            return family
    return "operations"


def _generic_recognized(query: str, reason: str) -> OccupationInterpretation:
    core = _core_query(query)
    tokens = set(core.split())
    return OccupationInterpretation(
        status="recognized",
        original_query=query.strip(),
        canonical_query=normalize_occupation_text(query),
        occupation_phrase=core,
        search_family=_generic_family(tokens),
        accepted_titles=(core,),
        reason=reason,
    )


def _single_word_alias_is_safe(
    alias: str,
    concept: OccupationConcept,
    core_tokens: tuple[str, ...],
) -> bool:
    if len(core_tokens) == 1:
        return True
    tokens = set(core_tokens)
    competing_heads = (tokens & _OCCUPATIONAL_HEAD_WORDS) - {alias}

    if concept.key == "server":
        return bool(tokens & _FOOD_SERVICE_CONTEXT) and not bool(tokens & _TECHNOLOGY_CONTEXT)
    if concept.key == "education_administrator" and alias == "principal":
        return bool(tokens & (_EDUCATION_CONTEXT - {"principal"})) and not bool(tokens & _TECHNOLOGY_CONTEXT)
    if concept.key == "architect":
        return bool(tokens & _BUILT_ENVIRONMENT_CONTEXT) and not bool(tokens & _TECHNOLOGY_CONTEXT)
    if concept.key == "coach":
        return bool(tokens & _SPORTS_CONTEXT)
    return not competing_heads


def _choose_exact_concept(
    alias: str,
    core_tokens: tuple[str, ...],
) -> OccupationConcept | None:
    concepts = _ALIAS_CONCEPTS.get(alias, ())
    if len(concepts) != 1:
        return None
    concept = concepts[0]
    if len(alias.split()) == 1 and not _single_word_alias_is_safe(alias, concept, core_tokens):
        return None
    return concept


def _exact_or_reordered_match(query: str) -> tuple[str, OccupationConcept] | None:
    core = _core_query(query)
    core_tokens = tuple(core.split())
    if not core_tokens:
        return None

    concept = _choose_exact_concept(core, core_tokens)
    if concept is not None:
        return core, concept

    # Reordered multiword titles are accepted only when the token sets match
    # exactly, avoiding partial-title drift.
    if len(core_tokens) > 1:
        core_set = set(core_tokens)
        reordered = [
            alias
            for alias in _ALIASES_BY_WORD_COUNT.get(len(core_tokens), ())
            if set(alias.split()) == core_set
        ]
        if len(reordered) == 1:
            alias = reordered[0]
            concept = _choose_exact_concept(alias, core_tokens)
            if concept is not None:
                return alias, concept

    # Longest phrase wins inside a query that carries a meaningful qualifier,
    # such as "senior staff accountant" after level words are removed.
    for alias in _SORTED_ALIASES:
        if alias == core:
            continue
        if not re.search(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])", core):
            continue
        concept = _choose_exact_concept(alias, core_tokens)
        if concept is not None:
            return alias, concept
    return None


def _fuzzy_match(query: str) -> tuple[str, OccupationConcept] | None:
    core = _core_query(query)
    tokens = core.split()
    if len(core) < 5 or not tokens:
        return None

    candidates = _ALIASES_BY_WORD_COUNT.get(len(tokens), ())
    scored: list[tuple[float, str, OccupationConcept]] = []
    for alias in candidates:
        if abs(len(alias) - len(core)) > max(3, len(core) // 5):
            continue
        concepts = _ALIAS_CONCEPTS[alias]
        if len(concepts) != 1:
            continue
        score = difflib.SequenceMatcher(None, core, alias).ratio()
        if score >= 0.86:
            scored.append((score, alias, concepts[0]))
    if not scored:
        return None
    scored.sort(key=lambda item: (-item[0], item[1], item[2].key))
    best = scored[0]
    runner_up = scored[1][0] if len(scored) > 1 else 0.0
    if best[0] < 0.88 or best[0] - runner_up < 0.025:
        return None
    return best[1], best[2]


def _collision_generic(query: str) -> OccupationInterpretation | None:
    tokens = set(_core_tokens(query))
    if not tokens:
        return None
    if tokens & _TECHNOLOGY_CONTEXT and tokens & _OCCUPATIONAL_HEAD_WORDS:
        return _generic_recognized(
            query,
            "Resolved a cross-domain occupation phrase using its complete technology context.",
        )
    return None


@lru_cache(maxsize=2_048)
def interpret_occupation_query(query: str) -> OccupationInterpretation:
    original = query.strip()
    acronym = _pure_ambiguous_acronym(original)
    if acronym is not None:
        return OccupationInterpretation(
            status="ambiguous",
            original_query=original,
            canonical_query=normalize_occupation_text(original),
            suggestions=AMBIGUOUS_ACRONYMS[acronym],
            reason=f"{acronym.upper()} has multiple common occupational meanings.",
        )

    exact = _exact_or_reordered_match(original)
    if exact is not None:
        alias, concept = exact
        return _recognized(
            original,
            concept,
            alias,
            "Matched a canonical, alternate, or safely reordered occupation title.",
        )

    fuzzy = _fuzzy_match(original)
    if fuzzy is not None:
        alias, concept = fuzzy
        return _recognized(
            original,
            concept,
            alias,
            "Matched a high-confidence spelling variant.",
        )

    collision = _collision_generic(original)
    if collision is not None:
        return collision

    core = _core_query(original)
    tokens = set(core.split())
    if tokens & _OCCUPATIONAL_HEAD_WORDS:
        return _generic_recognized(
            original,
            "Recognized a descriptive occupation title by its occupational head word.",
        )

    return OccupationInterpretation(
        status="unrecognized",
        original_query=original,
        canonical_query=normalize_occupation_text(original),
        reason="No deterministic occupation title or safe occupational pattern matched.",
    )


def _contains_title_phrase(title: str, phrase: str) -> bool:
    return bool(
        re.search(
            r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])",
            normalize_occupation_text(title),
        )
    )


def _specific_collision_allows(
    title: str,
    interpretation: OccupationInterpretation,
) -> bool:
    tokens = set(normalize_occupation_text(title).split())
    if interpretation.concept_key == "server":
        if tokens == {"server"}:
            return True
        return bool(tokens & _FOOD_SERVICE_CONTEXT) and not bool(tokens & _TECHNOLOGY_CONTEXT)
    if interpretation.concept_key == "education_administrator" and "principal" in tokens:
        return bool(tokens & (_EDUCATION_CONTEXT - {"principal"})) and not bool(tokens & _TECHNOLOGY_CONTEXT)
    if interpretation.concept_key == "architect":
        if tokens & _TECHNOLOGY_CONTEXT:
            return bool(tokens & _BUILT_ENVIRONMENT_CONTEXT)
    if interpretation.concept_key == "coach" and len(tokens) > 1:
        return bool(tokens & _SPORTS_CONTEXT)
    return True


def title_matches_occupation(
    title: str,
    interpretation: OccupationInterpretation,
) -> bool:
    if not interpretation.recognized or not interpretation.occupation_phrase:
        return False

    if interpretation.concept_key is not None:
        if not any(
            _contains_title_phrase(title, alias)
            for alias in interpretation.accepted_titles
        ):
            return False
        return _specific_collision_allows(title, interpretation)

    requested_tokens = {
        token
        for token in normalize_occupation_text(interpretation.occupation_phrase).split()
        if token not in _QUERY_MODIFIERS
    }
    title_tokens = set(normalize_occupation_text(title).split())
    head_tokens = requested_tokens & _OCCUPATIONAL_HEAD_WORDS
    if not head_tokens or not head_tokens.issubset(title_tokens):
        return False
    qualifier_tokens = requested_tokens - head_tokens
    if not qualifier_tokens:
        return True
    required = max(1, len(qualifier_tokens) - 1)
    return len(qualifier_tokens & title_tokens) >= required


__all__ = [
    "interpret_occupation_query",
    "is_ambiguous_occupation_query",
    "normalize_occupation_text",
    "registry_summary",
    "title_matches_occupation",
]
