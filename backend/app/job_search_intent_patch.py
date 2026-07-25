"""Apply the MarketLens job-intent engine to the provider search layer.

The fetch/normalization code still lives in app.job_search. This adapter keeps
that provider code stable while centralizing product matching rules in
app.job_intent_engine.

The adapter also provides a general occupation fallback. Known role families
receive carefully tuned matching, while careers outside the taxonomy use a
phrase-first occupation signature instead of accepting every title that shares
one generic word such as "engineer", "analyst", or "assistant".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
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

LEVEL_QUERY_STOP_TERMS = {
    "apprentice",
    "apprenticeship",
    "associate",
    "campus",
    "co-op",
    "coop",
    "early",
    "entry",
    "fellow",
    "fellowship",
    "grad",
    "graduate",
    "intern",
    "internship",
    "junior",
    "level",
    "mid",
    "new",
    "principal",
    "recent",
    "senior",
    "staff",
    "student",
    "summer",
    "trainee",
    "university",
}

# These aliases cover common cases where a field of study, occupation name,
# credential, and actual job title use different words. Matching still requires
# title-level evidence; aliases never make a description-only result sufficient.
OCCUPATION_ALIASES: dict[str, set[str]] = {
    # Healthcare and allied health
    "nursing": NURSING_TERMS,
    "nurse": NURSING_TERMS,
    "rn": NURSING_TERMS,
    "lpn": NURSING_TERMS,
    "cna": NURSING_TERMS,
    "physical therapy": {"physical therapist", "physical therapy", "pt"},
    "occupational therapy": {"occupational therapist", "occupational therapy", "ot"},
    "respiratory therapy": {"respiratory therapist", "respiratory therapy"},
    "radiology": {"radiologic technologist", "radiology technologist", "radiographer"},
    "pharmacy": {"pharmacist", "pharmacy technician", "pharmacy"},
    "dental": {"dentist", "dental hygienist", "dental assistant", "dental"},
    "veterinary": {"veterinarian", "veterinary technician", "veterinary assistant"},
    "social work": {"social worker", "social work", "case worker", "caseworker"},
    "psychology": {"psychologist", "psychology", "behavioral health"},
    "counseling": {"counselor", "counselling", "counseling", "therapist"},
    # Education and liberal arts
    "teaching": {"teacher", "teaching", "educator", "instructor"},
    "education": {"teacher", "teaching", "educator", "instructor", "education"},
    "professor": {"professor", "faculty", "lecturer"},
    "library science": {"librarian", "library specialist", "library assistant"},
    "history": {"historian", "history teacher", "archivist", "museum educator"},
    "english": {"english teacher", "writer", "editor", "copywriter"},
    "journalism": {"journalist", "reporter", "editor", "editorial", "journalism"},
    "architecture": {"architect", "architecture", "architectural designer"},
    "communications": {"communications", "public relations", "pr specialist"},
    "public relations": {"public relations", "communications", "pr specialist"},
    # Science and research
    "biology": {"biologist", "biology", "biological scientist", "research biologist"},
    "chemistry": {"chemist", "chemistry", "chemical scientist"},
    "physics": {"physicist", "physics"},
    "environmental science": {
        "environmental scientist",
        "environmental specialist",
        "environmental science",
    },
    "geology": {"geologist", "geoscientist", "geology"},
    "laboratory": {"laboratory technician", "lab technician", "laboratory assistant"},
    "research": {"researcher", "research assistant", "research associate", "scientist"},
    # Engineering
    "engineering": {"engineer", "engineering"},
    "mechanical engineering": {
        "mechanical engineer",
        "mechanical design engineer",
        "mechanical engineering",
    },
    "electrical engineering": {
        "electrical engineer",
        "electrical design engineer",
        "electronics engineer",
        "power systems engineer",
        "controls engineer",
        "electrical engineering",
    },
    "civil engineering": {
        "civil engineer",
        "structural engineer",
        "transportation engineer",
        "civil engineering",
    },
    "chemical engineering": {"chemical engineer", "process engineer", "chemical engineering"},
    "biomedical engineering": {"biomedical engineer", "medical device engineer"},
    "industrial engineering": {"industrial engineer", "manufacturing engineer"},
    "aerospace engineering": {"aerospace engineer", "aeronautical engineer"},
    # Business and public service
    "accounting": {"accountant", "accounting", "auditor"},
    "human resources": {"human resources", "hr specialist", "recruiter"},
    "real estate": {"real estate", "realtor", "property manager"},
    "law": {"lawyer", "attorney", "legal", "paralegal", "counsel", "law clerk"},
    "legal": {"lawyer", "attorney", "legal", "paralegal", "counsel", "law clerk"},
    "political science": {"policy analyst", "government affairs", "legislative assistant"},
    "criminal justice": {
        "probation officer",
        "corrections officer",
        "criminal investigator",
        "police officer",
    },
    # Skilled trades and service work
    "electrician": {"electrician", "electrical technician"},
    "plumbing": {"plumber", "plumbing technician"},
    "welding": {"welder", "welding technician"},
    "carpentry": {"carpenter", "finish carpenter"},
    "hvac": {"hvac technician", "heating technician", "air conditioning technician"},
    "automotive": {"auto mechanic", "automotive technician", "mechanic"},
    "machining": {"machinist", "cnc machinist", "machine operator"},
    "construction": {"construction worker", "construction manager", "site superintendent"},
    "culinary": {"chef", "cook", "culinary"},
    "hospitality": {"hotel", "guest services", "hospitality"},
}

OCCUPATION_HEAD_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"engineer", "engineering"}),
    frozenset({"analyst", "analysis"}),
    frozenset({"scientist", "science"}),
    frozenset({"teacher", "teaching", "educator", "instructor"}),
    frozenset({"nurse", "nursing"}),
    frozenset({"therapist", "therapy"}),
    frozenset({"counselor", "counseling", "counselling"}),
    frozenset({"manager", "management"}),
    frozenset({"technician", "technologist"}),
    frozenset({"assistant"}),
    frozenset({"coordinator"}),
    frozenset({"specialist"}),
    frozenset({"researcher", "research"}),
    frozenset({"accountant", "accounting", "auditor", "audit"}),
    frozenset({"attorney", "lawyer", "counsel", "paralegal"}),
    frozenset({"designer", "design"}),
    frozenset({"writer", "editor", "journalist", "reporter"}),
    frozenset({"librarian", "archivist"}),
    frozenset({"electrician"}),
    frozenset({"plumber", "plumbing"}),
    frozenset({"welder", "welding"}),
    frozenset({"carpenter", "carpentry"}),
    frozenset({"mechanic", "automotive"}),
    frozenset({"machinist", "machining"}),
    frozenset({"chef", "cook", "culinary"}),
    frozenset({"driver"}),
    frozenset({"operator"}),
    frozenset({"inspector"}),
    frozenset({"installer"}),
    frozenset({"pharmacist", "pharmacy"}),
    frozenset({"dentist", "dental"}),
    frozenset({"veterinarian", "veterinary"}),
    frozenset({"physician", "doctor"}),
    frozenset({"social", "worker"}),
)

TOKEN_PATTERN = re.compile(r"[a-z0-9+#.&-]+", re.IGNORECASE)


@dataclass(frozen=True)
class OccupationSignature:
    meaningful_tokens: tuple[str, ...]
    head_groups: tuple[frozenset[str], ...]
    modifier_tokens: tuple[str, ...]
    aliases: tuple[str, ...]

    @property
    def is_specific(self) -> bool:
        return bool(self.aliases or self.head_groups or self.meaningful_tokens)


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
    if (
        not normalized
        or normalized in GENERIC_QUERY_STOP_TERMS
        or normalized in LEVEL_QUERY_STOP_TERMS
    ):
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


def _meaningful_query_tokens(query: str) -> list[str]:
    return [
        token.lower()
        for token in TOKEN_PATTERN.findall(query.lower())
        if token.lower() not in GENERIC_QUERY_STOP_TERMS
        and token.lower() not in LEVEL_QUERY_STOP_TERMS
    ]


def _head_group_for_token(token: str) -> frozenset[str] | None:
    variants = _token_variants(token)
    for group in OCCUPATION_HEAD_GROUPS:
        if variants & group:
            return group
    return None


def _occupation_signature(query: str) -> OccupationSignature:
    normalized = re.sub(r"\s+", " ", query.lower()).strip()
    meaningful_tokens = _meaningful_query_tokens(normalized)

    alias_terms: set[str] = set()
    for phrase, aliases in OCCUPATION_ALIASES.items():
        if _contains_phrase(normalized, phrase):
            alias_terms.update(aliases)

    head_groups: list[frozenset[str]] = []
    modifier_tokens: list[str] = []
    for token in meaningful_tokens:
        group = _head_group_for_token(token)
        if group is not None:
            if group not in head_groups:
                head_groups.append(group)
        else:
            modifier_tokens.append(token)

    return OccupationSignature(
        meaningful_tokens=tuple(meaningful_tokens),
        head_groups=tuple(head_groups),
        modifier_tokens=tuple(modifier_tokens),
        aliases=tuple(
            sorted(alias_terms, key=lambda term: (-len(term.split()), -len(term), term))
        ),
    )


def _title_token_variants(title: str) -> set[str]:
    variants: set[str] = set()
    for token in TOKEN_PATTERN.findall(title.lower()):
        variants.update(_token_variants(token))
    return variants


def _modifier_matches_title(modifier: str, title_variants: set[str]) -> bool:
    return bool(_token_variants(modifier) & title_variants)


def _occupation_match_strength(title: str, query: str) -> int:
    """Return title-only occupation relevance; zero means reject."""

    signature = _occupation_signature(query)
    if not signature.is_specific:
        return 1

    title_lower = title.lower()
    title_variants = _title_token_variants(title)

    compact_query = " ".join(signature.meaningful_tokens)
    if compact_query and _contains_phrase(title_lower, compact_query):
        return 50

    if signature.aliases:
        matched_aliases = [
            alias for alias in signature.aliases if _contains_phrase(title_lower, alias)
        ]
        if matched_aliases:
            return 45 + min(5, max(len(alias.split()) for alias in matched_aliases))

    for head_group in signature.head_groups:
        if not (title_variants & head_group):
            return 0

    if signature.head_groups:
        if not signature.modifier_tokens:
            return 25
        matched_modifiers = sum(
            _modifier_matches_title(modifier, title_variants)
            for modifier in signature.modifier_tokens
        )
        if matched_modifiers == 0:
            return 0
        coverage = matched_modifiers / len(signature.modifier_tokens)
        return 30 + round(15 * coverage)

    # No recognized head noun: require an alias or meaningful token in the title.
    matched_tokens = sum(
        _modifier_matches_title(token, title_variants)
        for token in signature.meaningful_tokens
    )
    if len(signature.meaningful_tokens) == 1:
        return 25 if matched_tokens == 1 else 0
    required = max(1, (len(signature.meaningful_tokens) + 1) // 2)
    return 20 + matched_tokens * 5 if matched_tokens >= required else 0


def _should_apply_specific_occupation_guard(query: str) -> bool:
    signature = _occupation_signature(query)
    if signature.aliases or signature.head_groups:
        return True
    return len(signature.meaningful_tokens) >= 2


def _expanded_occupation_terms(query: str) -> list[str]:
    signature = _occupation_signature(query)
    terms: set[str] = set(signature.aliases)

    for token in signature.meaningful_tokens:
        terms.update(_token_variants(token))

    compact_phrase = " ".join(signature.meaningful_tokens).strip()
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

    strength = _occupation_match_strength(title, query)
    if strength > 0:
        return True

    signature = _occupation_signature(query)
    if not signature.is_specific:
        return True

    # Description-only evidence is allowed only for genuinely generic student or
    # trainee titles, and it must preserve the occupation phrase/modifiers.
    title_lower = title.lower()
    generic_early_career_title = any(
        _contains_phrase(title_lower, term)
        for term in {
            "apprentice",
            "fellow",
            "graduate program",
            "intern",
            "internship",
            "student trainee",
            "trainee",
        }
    )
    if not generic_early_career_title or level not in {"intern", "entry"}:
        return False

    description_lower = description.lower()
    if any(_contains_phrase(description_lower, alias) for alias in signature.aliases):
        return True

    description_variants = _title_token_variants(description)
    if signature.head_groups and not all(
        description_variants & head_group for head_group in signature.head_groups
    ):
        return False
    if signature.modifier_tokens and not any(
        _modifier_matches_title(modifier, description_variants)
        for modifier in signature.modifier_tokens
    ):
        return False
    return bool(signature.head_groups or signature.modifier_tokens)


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
    original_score_job = job_search._score_job

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
        canonical_family = job_search._query_job_function(query)
        classified_intent = intent_engine.classify_search_intent(
            query,
            resolved_level,
        )
        strict_families = getattr(
            job_search,
            "STRICT_DESCRIPTION_ONLY_ROLE_FAMILIES",
            set(),
        )

        if canonical_family in strict_families:
            return original_matches_requested_role(
                title,
                description,
                query,
                resolved_level,
            )

        if classified_intent.role_family in intent_engine.ENGINE_HANDLED_FAMILIES:
            return intent_engine.job_matches_search_intent(
                title,
                description,
                classified_intent,
            )

        if classified_intent.role_family is None and canonical_family is None:
            return _generic_title_matches_query(
                title,
                description,
                query,
                resolved_level,
            )

        # Known role families retain their tuned family/description behavior. The
        # strict occupation fallback exists for careers outside that taxonomy; it
        # must not turn broad searches such as sports marketing, computer science,
        # or law-student programs into literal all-token title searches.
        return original_matches_requested_role(
            title,
            description,
            query,
            resolved_level,
        )

    def _query_terms(query: str) -> list[str]:
        return sorted(
            set(original_query_terms(query)) | set(_expanded_occupation_terms(query))
        )

    def _matches_location(
        job_location: str | None,
        requested_location: str | None,
    ) -> bool:
        if not requested_location:
            return job_search._is_default_us_market_location(job_location)
        if not job_location:
            return False

        requested = requested_location.lower().strip()
        location = job_location.lower()

        if requested == "remote":
            return (
                ("remote" in location or "worldwide" in location)
                and not job_search._has_non_us_location(job_location)
                and job_search._is_default_us_market_location(job_location)
            )

        # Explicit local searches are strict. Remote-US is a different location
        # preference and must be requested deliberately rather than silently
        # admitted as a fallback for every U.S. city.
        requested_terms = job_search._requested_location_terms(requested_location)
        return job_search._contains_any(location, requested_terms)

    def _location_score_bonus(
        job_location: str | None,
        requested_location: str | None,
    ) -> int:
        if not requested_location or not job_location:
            return 0
        requested = requested_location.lower().strip()
        location = job_location.lower()
        if requested == "remote":
            return 10 if _matches_location(job_location, requested_location) else 0
        return (
            12
            if job_search._contains_any(
                location,
                job_search._requested_location_terms(requested_location),
            )
            else 0
        )

    def _score_job(
        title: str,
        description: str,
        query: str,
        level: str | None = None,
        company: str | None = None,
    ) -> int:
        base_score = original_score_job(
            title=title,
            description=description,
            query=query,
            level=level,
            company=company,
        )
        if base_score <= 0:
            return 0

        classified_intent = intent_engine.classify_search_intent(
            query,
            level or job_search.resolve_job_level(query),
        )
        if (
            classified_intent.role_family is not None
            or job_search._query_job_function(query) is not None
            or not _should_apply_specific_occupation_guard(query)
        ):
            return base_score

        strength = _occupation_match_strength(title, query)
        if strength <= 0:
            return 0
        return base_score + strength

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
        warnings = [
            intent_engine.no_results_warning(
                query,
                location,
                level,
                role_family,
            )
        ]
        if location and location.lower().strip() != "remote":
            warnings.append(
                "This local search excludes remote-only roles. Search for Remote "
                "or a broader state/region deliberately to expand location coverage."
            )
        return warnings

    job_search._query_role_family = _query_role_family
    job_search._title_matches_role_family = _title_matches_role_family
    job_search._matches_requested_role = _matches_requested_role
    job_search._query_terms = _query_terms
    job_search._matches_location = _matches_location
    job_search._location_score_bonus = _location_score_bonus
    job_search._score_job = _score_job
    job_search._remotive_search_terms = _remotive_search_terms
    job_search._warnings_for_no_results = _warnings_for_no_results
    job_search._INTENT_PATCH_APPLIED = True
