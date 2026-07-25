"""Final cross-sector correctness guards for MarketLens job search.

This module applies after the legacy intent and occupation adapters. It keeps
explicit local searches strict, strengthens occupation-title matching for
unclassified careers, and resolves early-career level ambiguities that differ
across sectors (for example, apprentice trades and staff accountants).
"""

from __future__ import annotations

import re
from typing import Any

from . import job_intent_engine as intent_engine
from . import job_search_intent_patch as intent_patch


CONFLICTING_TITLE_TERMS = {
    "account executive",
    "business development",
    "customer success",
    "marketing",
    "recruiter",
    "sales",
    "sales representative",
    "solutions consultant",
    "support",
}

NON_SENIOR_STAFF_OCCUPATIONS = {
    "accountant",
    "auditor",
    "nurse",
    "pharmacist",
    "reporter",
    "scientist",
    "social worker",
    "writer",
}

ENTRY_TRAINING_TITLE_TERMS = {
    "apprentice",
    "apprenticeship",
    "recruit",
    "trainee",
}

EXPERIENCE_WORD_VALUES = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}
EXPERIENCE_WORD_PATTERN = re.compile(
    r"\b(" + "|".join(EXPERIENCE_WORD_VALUES) + r")\s*\+?\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)
GENERIC_ENTRY_NUMBERED_TITLE_PATTERN = re.compile(
    r"(?:^|[\s,()/-])(?:i|1)(?:$|[\s,()/-])",
    re.IGNORECASE,
)


def _strict_occupation_match_strength(title: str, query: str) -> int:
    """Return title-only occupation relevance; zero means reject."""

    signature = intent_patch._occupation_signature(query)
    if not signature.is_specific:
        return 1

    title_lower = title.lower()
    query_lower = query.lower()
    title_variants = intent_patch._title_token_variants(title)

    if any(
        intent_patch._contains_phrase(title_lower, term)
        and not intent_patch._contains_phrase(query_lower, term)
        for term in CONFLICTING_TITLE_TERMS
    ):
        return 0

    compact_query = " ".join(signature.meaningful_tokens)
    if compact_query and intent_patch._contains_phrase(title_lower, compact_query):
        return 50

    matched_aliases = [
        alias
        for alias in signature.aliases
        if intent_patch._contains_phrase(title_lower, alias)
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
            intent_patch._modifier_matches_title(modifier, title_variants)
            for modifier in signature.modifier_tokens
        )
        if matched_modifiers == 0:
            return 0
        coverage = matched_modifiers / len(signature.modifier_tokens)
        return 30 + round(15 * coverage)

    matched_tokens = sum(
        intent_patch._modifier_matches_title(token, title_variants)
        for token in signature.meaningful_tokens
    )
    if len(signature.meaningful_tokens) == 1:
        return 25 if matched_tokens == 1 else 0

    # Multi-word occupations without a recognized head noun must preserve every
    # term unless an explicit alias already matched. This prevents "social
    # worker" from matching "social media manager".
    required = len(signature.meaningful_tokens)
    return 20 + matched_tokens * 5 if matched_tokens >= required else 0


def _is_entry_training_title(job_search: Any, title: str) -> bool:
    title_lower = title.lower()
    return job_search._contains_any(title_lower, ENTRY_TRAINING_TITLE_TERMS)


def _is_non_senior_staff_title(job_search: Any, title: str, description: str) -> bool:
    title_lower = title.lower()
    if not job_search._contains_phrase(title_lower, "staff"):
        return False
    if not job_search._contains_any(title_lower, NON_SENIOR_STAFF_OCCUPATIONS):
        return False
    disqualifying = {"senior", "sr", "lead", "principal", "manager", "director"}
    if job_search._contains_any(title_lower, disqualifying):
        return False
    return job_search._max_required_years(description) <= 3


def apply_job_search_correctness_patch(job_search: Any) -> None:
    """Apply strict role, location, ranking, and level behavior."""

    if getattr(job_search, "_CORRECTNESS_PATCH_APPLIED", False):
        return

    # The intent adapter's closures resolve this helper from module globals at
    # call time, so replacing it strengthens both filtering and score ranking.
    intent_patch._occupation_match_strength = _strict_occupation_match_strength

    original_matches_requested_role = job_search._matches_requested_role
    original_matches_level = job_search._matches_level
    original_level_score_bonus = job_search._level_score_bonus
    original_max_required_years = job_search._max_required_years

    def _max_required_years(description: str) -> int:
        numeric_years = original_max_required_years(description)
        word_years = [
            EXPERIENCE_WORD_VALUES[match.group(1).lower()]
            for match in EXPERIENCE_WORD_PATTERN.finditer(description)
        ]
        return max([numeric_years, *word_years])

    def _matches_requested_role(
        title: str,
        description: str,
        query: str,
        level: str | None = None,
    ) -> bool:
        resolved_level = level or job_search.resolve_job_level(query)
        canonical_family = job_search._query_job_function(query)
        classified_family = intent_engine.classify_search_intent(
            query,
            resolved_level,
        ).role_family
        base_match = original_matches_requested_role(
            title,
            description,
            query,
            resolved_level,
        )
        strength = _strict_occupation_match_strength(title, query)

        # Known families keep their existing broad and early-career recall. An
        # exact alias can additionally rescue a title such as HR Specialist when
        # the legacy family list lacks that synonym.
        if canonical_family is not None or classified_family is not None:
            return base_match or strength >= 45

        if not base_match:
            return False
        if intent_patch._should_apply_specific_occupation_guard(query):
            return strength > 0
        return True

    def _matches_level(title: str, description: str, level: str) -> bool:
        if original_matches_level(title, description, level):
            return True
        if level != "entry":
            return False
        if _is_entry_training_title(job_search, title):
            return not (
                job_search._title_has_mid_signal(title)
                or job_search.SENIOR_NUMBERED_TITLE_PATTERN.search(title)
            )
        if _is_non_senior_staff_title(job_search, title, description):
            return True
        if GENERIC_ENTRY_NUMBERED_TITLE_PATTERN.search(title):
            return not (
                job_search._title_has_mid_signal(title)
                or job_search._title_has_senior_signal(title)
            )
        max_years = _max_required_years(description)
        return 0 < max_years <= 3 and not (
            job_search._title_has_mid_signal(title)
            or job_search._title_has_senior_signal(title)
        )

    def _level_score_bonus(title: str, description: str, level: str) -> int:
        if level == "entry" and _matches_level(title, description, level):
            if _is_entry_training_title(job_search, title):
                return 8
            if _is_non_senior_staff_title(job_search, title, description):
                return 6
        return original_level_score_bonus(title, description, level)

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
            )

        # City/state/region searches do not silently absorb remote jobs. Users
        # can explicitly search Remote or broaden the location field themselves.
        requested_terms = job_search._requested_location_terms(requested_location)
        return job_search._contains_any(location, requested_terms)

    def _location_score_bonus(
        job_location: str | None,
        requested_location: str | None,
    ) -> int:
        if not requested_location or not job_location:
            return 0
        if not _matches_location(job_location, requested_location):
            return 0
        return 10 if requested_location.lower().strip() == "remote" else 12

    job_search._max_required_years = _max_required_years
    job_search._matches_requested_role = _matches_requested_role
    job_search._matches_level = _matches_level
    job_search._level_score_bonus = _level_score_bonus
    job_search._matches_location = _matches_location
    job_search._location_score_bonus = _location_score_bonus
    job_search._CORRECTNESS_PATCH_APPLIED = True
