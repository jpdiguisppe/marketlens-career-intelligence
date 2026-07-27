"""Conservative occupation-query interpretation for public job search.

This layer centralizes exact abbreviations and high-confidence spelling repair
without weakening MarketLens title, level, location, or negative-match guards.
It changes how a query is interpreted; it never admits a job on its own.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Any, Callable


# Exact, bounded mappings only. Ambiguous abbreviations such as PM, SE, and BA
# deliberately remain literal unless the user supplies clarifying words.
EXACT_OCCUPATION_ABBREVIATIONS: dict[str, str] = {
    "soc analyst": "security operations center analyst",
    "fp&a": "financial planning and analysis",
    "fpa": "financial planning and analysis",
    "swe": "software engineer",
    "sde": "software development engineer",
    "sre": "site reliability engineer",
    "mle": "machine learning engineer",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "ds": "data scientist",
    "bi": "business intelligence",
    "ux": "user experience",
    "ui": "user interface",
    "rn": "registered nurse",
    "lpn": "licensed practical nurse",
    "lvn": "licensed vocational nurse",
    "cna": "certified nursing assistant",
    "aprn": "advanced practice registered nurse",
    "qa": "quality assurance",
    "cs": "computer science",
}

AMBIGUOUS_ABBREVIATIONS = frozenset({"ba", "pm", "se"})

# Curated occupation vocabulary only. This is intentionally not every English
# word or every technology name, which keeps fuzzy correction narrow.
TYPO_VOCABULARY = frozenset(
    {
        "accountant",
        "analyst",
        "architect",
        "backend",
        "business",
        "cybersecurity",
        "data",
        "developer",
        "engineer",
        "engineering",
        "frontend",
        "intelligence",
        "machine",
        "marketing",
        "nurse",
        "operations",
        "pharmacist",
        "reliability",
        "research",
        "scientist",
        "security",
        "software",
        "systems",
        "teacher",
        "therapist",
    }
)

_WORD_PATTERN = re.compile(r"[a-z][a-z-]*", re.IGNORECASE)


@dataclass(frozen=True)
class JobQueryInterpretation:
    original_query: str
    canonical_query: str
    abbreviation_expansions: tuple[str, ...]
    spelling_corrections: tuple[str, ...]

    @property
    def changed(self) -> bool:
        return self.original_query.strip().lower() != self.canonical_query


def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    parts = [re.escape(part) for part in re.split(r"\s+", phrase.strip()) if part]
    separator = r"\s+"
    return re.compile(
        r"(?<![a-z0-9])" + separator.join(parts) + r"(?![a-z0-9])",
        re.IGNORECASE,
    )


def _expand_abbreviations(value: str) -> tuple[str, tuple[str, ...]]:
    expanded = value
    applied: list[str] = []
    for abbreviation, canonical in sorted(
        EXACT_OCCUPATION_ABBREVIATIONS.items(),
        key=lambda item: (-len(item[0].split()), -len(item[0]), item[0]),
    ):
        pattern = _phrase_pattern(abbreviation)
        if not pattern.search(expanded):
            continue
        expanded = pattern.sub(canonical, expanded)
        applied.append(f"{abbreviation} -> {canonical}")
    return expanded, tuple(applied)


def _best_typo_correction(token: str) -> str | None:
    normalized = token.lower()
    if (
        len(normalized) < 5
        or normalized in TYPO_VOCABULARY
        or normalized in AMBIGUOUS_ABBREVIATIONS
        or not normalized.isalpha()
    ):
        return None

    scored = sorted(
        (
            (difflib.SequenceMatcher(None, normalized, candidate).ratio(), candidate)
            for candidate in TYPO_VOCABULARY
            if candidate[0] == normalized[0] and abs(len(candidate) - len(normalized)) <= 2
        ),
        reverse=True,
    )
    if not scored:
        return None

    best_score, best_candidate = scored[0]
    runner_up_score = scored[1][0] if len(scored) > 1 else 0.0
    if best_score < 0.88 or best_score - runner_up_score < 0.06:
        return None
    return best_candidate


def _correct_spelling(value: str) -> tuple[str, tuple[str, ...]]:
    corrections: list[str] = []

    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        corrected = _best_typo_correction(token)
        if corrected is None:
            return token
        corrections.append(f"{token.lower()} -> {corrected}")
        return corrected

    return _WORD_PATTERN.sub(replace, value), tuple(corrections)


def interpret_job_query(query: str) -> JobQueryInterpretation:
    original = query.strip()
    normalized = re.sub(r"\s+", " ", original.lower()).strip()
    expanded, abbreviation_expansions = _expand_abbreviations(normalized)
    corrected, spelling_corrections = _correct_spelling(expanded)
    canonical = re.sub(r"\s+", " ", corrected).strip()
    return JobQueryInterpretation(
        original_query=original,
        canonical_query=canonical,
        abbreviation_expansions=abbreviation_expansions,
        spelling_corrections=spelling_corrections,
    )


def canonicalize_job_query(query: str) -> str:
    return interpret_job_query(query).canonical_query


def _wrap_query_first(function: Callable[..., Any]) -> Callable[..., Any]:
    def wrapped(query: str, *args: Any, **kwargs: Any) -> Any:
        return function(canonicalize_job_query(query), *args, **kwargs)

    return wrapped


def apply_job_search_query_interpretation(job_search: Any, intent_patch: Any) -> None:
    """Apply centralized interpretation without replacing existing search rules."""

    if getattr(job_search, "_QUERY_INTERPRETATION_APPLIED", False):
        return

    original_parse_intent = job_search.parse_job_search_intent
    original_resolve_level = job_search.resolve_job_level
    original_query_terms = job_search._query_terms
    original_query_role_family = job_search._query_role_family
    original_query_job_function = job_search._query_job_function
    original_query_industry = job_search._query_industry
    original_matches_requested_role = job_search._matches_requested_role
    original_score_job = job_search._score_job
    original_occupation_signature = intent_patch._occupation_signature

    def parse_job_search_intent(
        query: str,
        location: str | None = None,
        level: str | None = None,
    ) -> Any:
        canonical = canonicalize_job_query(query)
        parsed = original_parse_intent(canonical, location, level)
        return job_search.JobSearchIntent(
            query=query.strip(),
            job_function=parsed.job_function,
            industry=parsed.industry,
            level=parsed.level,
            location=parsed.location,
        )

    def resolve_job_level(query: str, level: str | None = None) -> Any:
        return original_resolve_level(canonicalize_job_query(query), level)

    def matches_requested_role(
        title: str,
        description: str,
        query: str,
        level: Any = None,
    ) -> bool:
        return original_matches_requested_role(
            title,
            description,
            canonicalize_job_query(query),
            level,
        )

    def score_job(
        title: str,
        description: str,
        query: str,
        level: str | None = None,
        company: str | None = None,
    ) -> int:
        return original_score_job(
            title=title,
            description=description,
            query=canonicalize_job_query(query),
            level=level,
            company=company,
        )

    def occupation_signature(query: str) -> Any:
        return original_occupation_signature(canonicalize_job_query(query))

    job_search.parse_job_search_intent = parse_job_search_intent
    job_search.resolve_job_level = resolve_job_level
    job_search._query_terms = _wrap_query_first(original_query_terms)
    job_search._query_role_family = _wrap_query_first(original_query_role_family)
    job_search._query_job_function = _wrap_query_first(original_query_job_function)
    job_search._query_industry = _wrap_query_first(original_query_industry)
    job_search._matches_requested_role = matches_requested_role
    job_search._score_job = score_job
    intent_patch._occupation_signature = occupation_signature
    job_search._QUERY_INTERPRETATION_APPLIED = True
