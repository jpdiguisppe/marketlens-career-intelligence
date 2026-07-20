"""Apply the MarketLens job-intent engine to the provider search layer.

The fetch/normalization code still lives in app.job_search. This adapter keeps
that provider code stable while centralizing product matching rules in
app.job_intent_engine.

The adapter also provides a general occupation fallback. Known role families
receive carefully tuned matching, while careers outside the taxonomy still
match through normalized occupation phrases, aliases, and conservative title
matching instead of silently producing zero-score results.
"""

from __future__ import annotations

import re
from typing import Any

from . import job_intent_engine as intent_engine


NURSING_TERMS = {
    "nurse",
    "nursing",
    "registered nurse",
    "registered nursing",
    "rn",
    "licensed practical nurse",
    "licensed vocational nurse",
    "lpn",
    "lvn",
    "certified nursing assistant",
    "nursing assistant",
    "nurse assistant",
    "cna",
    "nurse practitioner",
    "advanced practice registered nurse",
    "aprn",
    "clinical nurse",
    "staff nurse",
    "travel nurse",
    "school nurse",
    "home health nurse",
    "public health nurse",
    "nurse educator",
    "nurse manager",
}

GENERIC_QUERY_STOP_TERMS = {
    "a",
    "an",
    "and",
    "any",
    "career",
    "careers",
    "employment",
    "for",
    "fulltime",
    "full-time",
    "hiring",
    "in",
    "job",
    "jobs",
    "market",
    "near",
    "of",
    "opening",
    "openings",
    "opportunities",
    "opportunity",
    "position",
    "positions",
    "role",
    "roles",
    "the",
    "work",
}

# These aliases cover common cases where a field of study, occupation name,
# credential, and actual job title use different words. The generic morphology
# fallback below handles careers not explicitly listed here.
OCCUPATION_ALIASES: dict[str, set[str]] = {
    "nursing": NURSING_TERMS,
    "nurse": NURSING_TERMS,
    "rn": NURSING_TERMS,
    "lpn": NURSING_TERMS,
    "cna": NURSING_TERMS,
    "teaching": {"teacher", "teaching", "educator", "education"},
    "education": {"teacher", "teaching", "educator", "education"},
    "law": {"law", "lawyer", "attorney", "legal", "paralegal"},
    "legal": {"law", "lawyer", "attorney", "legal", "paralegal"},
    "psychology": {"psychology", "psychologist", "behavioral health"},
    "biology": {"biology", "biologist", "biological"},
    "chemistry": {"chemistry", "chemist", "chemical"},
    "physics": {"physics", "physicist"},
    "architecture": {"architecture", "architect", "architectural"},
    "journalism": {"journalism", "journalist", "reporter", "editorial"},
    "social work": {"social work", "social worker", "case worker", "caseworker"},
    "engineering": {"engineering", "engineer"},
    "mechanical engineering": {"mechanical engineering", "mechanical engineer"},
    "electrical engineering": {"electrical engineering", "electrical engineer"},
    "civil engineering": {"civil engineering", "civil engineer"},
    "chemical engineering": {"chemical engineering", "chemical engineer"},
    "biomedical engineering": {"biomedical engineering", "biomedical engineer"},
    "environmental science": {"environmental science", "environmental scientist"},
    "political science": {"political science", "policy analyst", "government affairs"},
    "criminal justice": {"criminal justice", "probation officer", "corrections officer"},
    "electrician": {"electrician", "electrical technician"},
    "plumbing": {"plumbing", "plumber"},
    "welding": {"welding", "welder"},
    "carpentry": {"carpentry", "carpenter"},
    "hvac": {"hvac", "heating technician", "air conditioning technician"},
    "automotive": {"automotive", "auto mechanic", "automotive technician", "mechanic"},
    "culinary": {"culinary", "chef", "cook"},
    "hospitality": {"hospitality", "hotel", "guest services"},
    "real estate": {"real estate", "realtor", "property manager"},
}

TOKEN_PATTERN = re.compile(r"[a-z0-9+#.&-]+", re.IGNORECASE)


def _contains_phrase(value: str, phrase: str) -> bool:
    cleaned_phrase = phrase.strip().lower()
    if not cleaned_phrase:
        return False
    escaped_words = [
        re.escape(part)
        for part in re.split(r"[\s,./()\-]+", cleaned_phrase)
        if part
    ]
    if not escaped_words:
        return False
    separator = r"[\s,./()\-]+"
    pattern = r"(?<![a-z0-9])" + separator.join(escaped_words) + r"(?![a-z0-9])"
    return bool(re.search(pattern, value.lower()))


def _token_variants(token: str) -> set[str]:
    """Return conservative occupation-word variants without external NLP deps."""

    normalized = token.lower().strip(" .,&-")
    if not normalized or normalized in GENERIC_QUERY_STOP_TERMS:
        return set()

    variants = {normalized}

    if normalized.endswith("ies") and len(normalized) > 4:
        variants.add(f"{normalized[:-3]}y")
    elif normalized.endswith("es") and len(normalized) > 4:
        variants.add(normalized[:-2])
    elif normalized.endswith("s") and len(normalized) > 3:
        variants.add(normalized[:-1])

    if normalized.endswith("ing") and len(normalized) > 5:
        base = normalized[:-3]
        variants.add(base)
        variants.add(f"{base}e")
        variants.add(f"{base}er")
        if len(base) > 2 and base[-1] == base[-2]:
            variants.add(base[:-1])

    if normalized.endswith("tion") and len(normalized) > 6:
        variants.add(normalized[:-3])
    if normalized.endswith("ist") and len(normalized) > 5:
        variants.add(normalized[:-3])
    if normalized.endswith("er") and len(normalized) > 4:
        variants.add(normalized[:-2])

    return {variant for variant in variants if len(variant) >= 2}


def _expanded_occupation_terms(query: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", query.lower()).strip()
    terms: set[str] = set()

    for phrase, aliases in OCCUPATION_ALIASES.items():
        if _contains_phrase(normalized, phrase):
            terms.update(aliases)

    meaningful_tokens = [
        token
        for token in TOKEN_PATTERN.findall(normalized)
        if token not in GENERIC_QUERY_STOP_TERMS
    ]
    for token in meaningful_tokens:
        terms.update(_token_variants(token))

    compact_phrase = " ".join(meaningful_tokens).strip()
    if compact_phrase:
        terms.add(compact_phrase)

    return sorted(
        (term for term in terms if term and term not in GENERIC_QUERY_STOP_TERMS),
        key=lambda term: (-len(term.split()), -len(term), term),
    )


def _generic_title_matches_query(
    title: str,
    description: str,
    query: str,
    level: str | None,
) -> bool:
    """Match careers outside the curated taxonomy without accepting everything."""

    terms = _expanded_occupation_terms(query)
    if not terms:
        return True

    title_lower = title.lower()
    if any(_contains_phrase(title_lower, term) for term in terms):
        return True

    # Only use descriptions as a fallback for explicitly early-career generic
    # postings. This avoids admitting unrelated jobs merely because a broad
    # occupation word appears somewhere in the description.
    searchable = f"{title} {description}".lower()
    is_early_career = level in {"intern", "entry"} or any(
        _contains_phrase(searchable, term)
        for term in intent_engine.INTERN_TITLE_TERMS | intent_engine.ENTRY_TEXT_TERMS
    )
    return bool(
        is_early_career
        and any(_contains_phrase(description.lower(), term) for term in terms)
    )


def _extend_known_taxonomies(job_search: Any) -> None:
    """Add high-value synonyms to both the legacy and centralized taxonomies."""

    job_search.HEALTHCARE_TITLE_TERMS.update(NURSING_TERMS)
    job_search.ROLE_FAMILY_TITLE_TERMS["healthcare"].update(NURSING_TERMS)
    job_search.ROLE_FAMILY_QUERY_TERMS["healthcare"].update(NURSING_TERMS)

    intent_engine.HEALTHCARE_TITLE_TERMS.update(NURSING_TERMS)
    intent_engine.ROLE_TITLE_TERMS["healthcare"].update(NURSING_TERMS)
    intent_engine.ROLE_QUERY_TERMS["healthcare"].update(NURSING_TERMS)
    intent_engine.ENGINE_HANDLED_FAMILIES = frozenset(
        set(intent_engine.ENGINE_HANDLED_FAMILIES) | {"healthcare"}
    )


def apply_job_search_intent_patch(job_search: Any) -> None:
    """Patch app.job_search helpers with centralized, occupation-wide behavior."""

    if getattr(job_search, "_INTENT_PATCH_APPLIED", False):
        return

    _extend_known_taxonomies(job_search)

    original_query_role_family = job_search._query_role_family
    original_title_matches_role_family = job_search._title_matches_role_family
    original_matches_requested_role = job_search._matches_requested_role
    original_query_terms = job_search._query_terms

    job_search.NON_US_LOCATION_TERMS.update(intent_engine.EXTRA_NON_US_LOCATION_TERMS)
    job_search.INTERN_TERMS.update(intent_engine.INTERN_TITLE_TERMS)

    def _query_role_family(query: str) -> str | None:
        intent = intent_engine.classify_search_intent(query)
        if intent.role_family in job_search.ROLE_FAMILY_TITLE_TERMS:
            return intent.role_family
        return original_query_role_family(query)

    def _title_matches_role_family(title: str, family: str) -> bool:
        if family in intent_engine.ENGINE_HANDLED_FAMILIES:
            return intent_engine.title_matches_search_family(title, family)
        return original_title_matches_role_family(title, family)

    def _matches_requested_role(
        title: str,
        description: str,
        query: str,
        level: str | None = None,
    ) -> bool:
        resolved_level = level or job_search.resolve_job_level(query)
        intent = intent_engine.classify_search_intent(query, resolved_level)

        if intent.role_family in intent_engine.ENGINE_HANDLED_FAMILIES:
            return intent_engine.job_matches_search_intent(title, description, intent)

        if intent.role_family is None:
            return _generic_title_matches_query(
                title,
                description,
                query,
                resolved_level,
            )

        return original_matches_requested_role(title, description, query, level)

    def _query_terms(query: str) -> list[str]:
        return sorted(
            set(original_query_terms(query)) | set(_expanded_occupation_terms(query))
        )

    def _remotive_search_terms(query: str, level: str) -> list[str | None]:
        terms = intent_engine.remotive_search_terms(query, level)
        terms.extend(_expanded_occupation_terms(query))
        seen: set[str | None] = set()
        unique_terms: list[str | None] = []
        for term in terms:
            normalized = term.strip().lower() if isinstance(term, str) else None
            if normalized in seen:
                continue
            seen.add(normalized)
            unique_terms.append(normalized)
            if len(unique_terms) >= 12:
                break
        return unique_terms

    def _warnings_for_no_results(
        query: str,
        location: str | None,
        level: str,
        role_family: str | None,
    ) -> list[str]:
        return [
            intent_engine.no_results_warning(
                query,
                location,
                level,
                role_family,
            )
        ]

    job_search._query_role_family = _query_role_family
    job_search._title_matches_role_family = _title_matches_role_family
    job_search._matches_requested_role = _matches_requested_role
    job_search._query_terms = _query_terms
    job_search._remotive_search_terms = _remotive_search_terms
    job_search._warnings_for_no_results = _warnings_for_no_results
    job_search._INTENT_PATCH_APPLIED = True
