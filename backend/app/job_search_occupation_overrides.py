"""Resolve occupation queries that need stricter matching than a broad family.

The general intent engine handles broad role families and unknown occupations.
Some queries need phrase-first behavior so the complete occupation remains more
important than a shared family keyword. For example, an RN search must return
nursing titles rather than every healthcare-adjacent job.
"""

from __future__ import annotations

import re
from typing import Any


REGISTERED_NURSE_TITLE_TERMS = {
    "registered nurse",
    "registered professional nurse",
    "clinical nurse",
    "staff nurse",
    "charge nurse",
    "travel nurse",
    "school nurse",
    "home health nurse",
    "public health nurse",
    "nurse educator",
    "nurse manager",
    "nurse resident",
    "graduate nurse",
    "nurse practitioner",
    "advanced practice registered nurse",
    "aprn",
    "rn",
}

PRACTICAL_NURSE_TITLE_TERMS = {
    "licensed practical nurse",
    "licensed vocational nurse",
    "practical nurse",
    "vocational nurse",
    "lpn",
    "lvn",
}

NURSING_ASSISTANT_TITLE_TERMS = {
    "certified nursing assistant",
    "nursing assistant",
    "nurse assistant",
    "nurse aide",
    "nursing aide",
    "cna",
}

NURSE_PRACTITIONER_TITLE_TERMS = {
    "nurse practitioner",
    "advanced practice registered nurse",
    "advanced practice nurse",
    "aprn",
}

NURSING_TITLE_TERMS = (
    REGISTERED_NURSE_TITLE_TERMS
    | PRACTICAL_NURSE_TITLE_TERMS
    | NURSING_ASSISTANT_TITLE_TERMS
    | NURSE_PRACTITIONER_TITLE_TERMS
    | {
        "nurse",
        "nursing",
    }
)

# Order matters: specific phrases are checked before broad words such as nurse.
OCCUPATION_TITLE_OVERRIDES: dict[str, set[str]] = {
    "nurse practitioner": NURSE_PRACTITIONER_TITLE_TERMS,
    "registered nurse": REGISTERED_NURSE_TITLE_TERMS,
    "licensed practical nurse": PRACTICAL_NURSE_TITLE_TERMS,
    "licensed vocational nurse": PRACTICAL_NURSE_TITLE_TERMS,
    "certified nursing assistant": NURSING_ASSISTANT_TITLE_TERMS,
    "nursing assistant": NURSING_ASSISTANT_TITLE_TERMS,
    "aprn": NURSE_PRACTITIONER_TITLE_TERMS,
    "lpn": PRACTICAL_NURSE_TITLE_TERMS,
    "lvn": PRACTICAL_NURSE_TITLE_TERMS,
    "cna": NURSING_ASSISTANT_TITLE_TERMS,
    "rn": REGISTERED_NURSE_TITLE_TERMS,
    "nursing": NURSING_TITLE_TERMS,
    "nurse": NURSING_TITLE_TERMS,
    "court reporting": {"court reporter", "court reporting"},
}

NURSING_OVERRIDE_PHRASES = frozenset(
    phrase for phrase in OCCUPATION_TITLE_OVERRIDES if phrase != "court reporting"
)

# Court reporting must bypass the data/reporting family. Nursing remains in the
# healthcare family for user-facing classification, but its title matching is
# still narrowed by OCCUPATION_TITLE_OVERRIDES.
FAMILY_BYPASS_PHRASES = frozenset({"court reporting"})


def _contains_phrase(value: str, phrase: str) -> bool:
    escaped_words = [
        re.escape(part)
        for part in re.split(r"[\s,./()\-]+", phrase.strip().lower())
        if part
    ]
    if not escaped_words:
        return False
    separator = r"[\s,./()\-]+"
    pattern = r"(?<![a-z0-9])" + separator.join(escaped_words) + r"(?![a-z0-9])"
    return bool(re.search(pattern, value.lower()))


def _occupation_override_phrase(query: str) -> str | None:
    normalized = query.lower().strip()
    for phrase in OCCUPATION_TITLE_OVERRIDES:
        if _contains_phrase(normalized, phrase):
            return phrase
    return None


def _occupation_override(query: str) -> set[str] | None:
    phrase = _occupation_override_phrase(query)
    if phrase is None:
        return None
    return OCCUPATION_TITLE_OVERRIDES[phrase]


def _is_nursing_query(query: str) -> bool:
    phrase = _occupation_override_phrase(query)
    return phrase in NURSING_OVERRIDE_PHRASES


def _is_remote_location(location: str | None) -> bool:
    if not location:
        return False
    normalized = location.lower()
    return "remote" in normalized or "worldwide" in normalized


def _filter_local_nursing_outcome(
    job_search: Any,
    outcome: Any,
    query: str,
    location: str | None,
) -> Any:
    """Remove remote fallback jobs from an explicitly local nursing search."""

    if not _is_nursing_query(query) or not location or location.lower().strip() == "remote":
        return outcome

    filtered_jobs = [
        (score, job)
        for score, job in outcome.scored_jobs
        if not _is_remote_location(job.location)
    ]
    removed_count = len(outcome.scored_jobs) - len(filtered_jobs)
    if removed_count == 0:
        return outcome

    notes = list(outcome.notes)
    notes.append(
        f"Excluded {removed_count} remote fallback nursing result"
        f"{'s' if removed_count != 1 else ''} from this local search."
    )
    return job_search._ProviderOutcome(
        provider=outcome.provider,
        label=outcome.label,
        fetched_count=outcome.fetched_count,
        scored_jobs=filtered_jobs,
        status=outcome.status,
        notes=notes,
    )


def apply_job_search_occupation_overrides(job_search: Any) -> None:
    """Apply narrow phrase-first overrides after the main intent patch."""

    if getattr(job_search, "_OCCUPATION_OVERRIDES_APPLIED", False):
        return

    original_query_role_family = job_search._query_role_family
    original_matches_requested_role = job_search._matches_requested_role
    original_search_greenhouse_boards = job_search._search_greenhouse_boards
    original_search_lever_sites = job_search._search_lever_sites
    original_search_remoteok = job_search._search_remoteok
    original_search_remotive = job_search._search_remotive

    def _query_role_family(query: str) -> str | None:
        phrase = _occupation_override_phrase(query)
        if phrase in FAMILY_BYPASS_PHRASES:
            return None
        return original_query_role_family(query)

    def _matches_requested_role(
        title: str,
        description: str,
        query: str,
        level: str | None = None,
    ) -> bool:
        title_terms = _occupation_override(query)
        if title_terms is not None:
            return any(_contains_phrase(title, term) for term in title_terms)
        return original_matches_requested_role(title, description, query, level)

    def _search_greenhouse_boards(
        client: Any,
        board_tokens: list[str],
        query: str,
        location: str | None,
        level: str,
    ) -> Any:
        outcome = original_search_greenhouse_boards(client, board_tokens, query, location, level)
        return _filter_local_nursing_outcome(job_search, outcome, query, location)

    def _search_lever_sites(
        client: Any,
        site_names: list[str],
        query: str,
        location: str | None,
        level: str,
    ) -> Any:
        outcome = original_search_lever_sites(client, site_names, query, location, level)
        return _filter_local_nursing_outcome(job_search, outcome, query, location)

    def _search_remoteok(
        client: Any,
        query: str,
        location: str | None,
        level: str,
    ) -> Any:
        outcome = original_search_remoteok(client, query, location, level)
        return _filter_local_nursing_outcome(job_search, outcome, query, location)

    def _search_remotive(
        client: Any,
        query: str,
        location: str | None,
        level: str,
    ) -> Any:
        outcome = original_search_remotive(client, query, location, level)
        return _filter_local_nursing_outcome(job_search, outcome, query, location)

    job_search._query_role_family = _query_role_family
    job_search._matches_requested_role = _matches_requested_role
    job_search._search_greenhouse_boards = _search_greenhouse_boards
    job_search._search_lever_sites = _search_lever_sites
    job_search._search_remoteok = _search_remoteok
    job_search._search_remotive = _search_remotive
    job_search._OCCUPATION_OVERRIDES_APPLIED = True
