"""Add intent-selected SmartRecruiters company boards to job search."""

from __future__ import annotations

import difflib
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import httpx

from app.external_urls import sanitize_external_https_url
from . import job_search_intent_patch as intent_patch
from .smartrecruiters_sources import SMARTRECRUITERS_SOURCES, SmartRecruitersSource

SMARTRECRUITERS_BASE_URL = "https://api.smartrecruiters.com/v1/companies"
MAX_SOURCES_PER_SEARCH = 4
MAX_LIST_RESULTS = 100
MAX_DETAIL_REQUESTS = 8
MAX_SEARCH_PASSES_PER_SOURCE = 2
POSTING_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,120}$")
GENERIC_SOURCE_QUERY_TERMS = {
    "assistant",
    "designer",
    "engineer",
    "engineering",
    "manager",
    "operations",
    "quality",
    "research",
    "scientist",
    "specialist",
    "technician",
}


def _smartrecruiters_enabled() -> bool:
    return os.getenv("JOB_SEARCH_SMARTRECRUITERS_ENABLED", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }

_LIST_CACHE: dict[str, dict[str, Any]] = {}
_DETAIL_CACHE: dict[str, dict[str, Any]] = {}


def _cache_get(cache: dict[str, dict[str, Any]], key: str) -> Any | None:
    entry = cache.get(key)
    if not entry or time.monotonic() >= float(entry.get("expires_at", 0.0)):
        return None
    return entry.get("value")


def _cache_put(cache: dict[str, dict[str, Any]], key: str, value: Any, seconds: int) -> None:
    cache[key] = {"expires_at": time.monotonic() + seconds, "value": value}


def _source_matches_explicit_location(source: SmartRecruitersSource, location: str | None) -> bool:
    if not source.location_terms or not location:
        return True
    normalized = location.lower().strip()
    if normalized == "remote":
        return False
    return any(intent_patch._contains_phrase(normalized, term) for term in source.location_terms)


def _source_score(
    source: SmartRecruitersSource,
    *,
    query: str,
    job_function: str | None,
    industry: str | None,
    location: str | None,
) -> int:
    if not _source_matches_explicit_location(source, location):
        return -10_000
    normalized = query.lower().strip()
    expanded_terms = set(intent_patch._expanded_occupation_terms(query))
    matched_terms = {
        term
        for term in source.query_terms
        if intent_patch._contains_phrase(normalized, term) or term in expanded_terms
    }
    specific_matches = sum(
        len(term.split()) > 1 or term not in GENERIC_SOURCE_QUERY_TERMS
        for term in matched_terms
    )
    generic_matches = len(matched_terms) - specific_matches
    family_match = bool(job_function and job_function in source.role_families)

    # Industry adjacency alone is not enough for a concrete occupation. For
    # example, an education publisher should not be queried for an elementary
    # teacher search merely because both relate to education.
    if (
        intent_patch._should_apply_specific_occupation_guard(query)
        and not specific_matches
        and not family_match
    ):
        return 0

    score = min(specific_matches, 3) * 12 + min(generic_matches, 2) * 3
    if family_match:
        score += 9
    if industry and industry in source.industries:
        score += 12
    return score


def select_smartrecruiters_sources(
    job_search: Any,
    query: str,
    location: str | None,
    level: str,
) -> tuple[SmartRecruitersSource, ...]:
    intent = job_search.parse_job_search_intent(query=query, location=location, level=level)
    scores = {
        source.identifier: _source_score(
            source,
            query=query,
            job_function=intent.job_function,
            industry=intent.industry,
            location=location,
        )
        for source in SMARTRECRUITERS_SOURCES
    }
    ranked = sorted(
        SMARTRECRUITERS_SOURCES,
        key=lambda source: (
            -scores[source.identifier],
            -source.fallback_priority,
            source.organization,
        ),
    )
    positive = [source for source in ranked if scores[source.identifier] > 0]
    return tuple(positive[:MAX_SOURCES_PER_SEARCH])


def _search_terms(query: str) -> tuple[str, ...]:
    signature = intent_patch._occupation_signature(query)
    normalized_query = re.sub(r"\s+", " ", query.lower()).strip()
    occupation_query = " ".join(signature.meaningful_tokens).strip() or normalized_query

    aliases = sorted(
        (
            alias.strip().lower()
            for alias in signature.aliases
            if alias.strip()
            and alias.strip().lower() != occupation_query
            and len(alias.strip()) >= 4
        ),
        key=lambda alias: (
            -difflib.SequenceMatcher(None, occupation_query, alias).ratio(),
            len(alias),
            alias,
        ),
    )

    seen: set[str] = set()
    terms: list[str] = []
    for candidate in (occupation_query, *aliases):
        cleaned = candidate.strip().lower()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        terms.append(cleaned)
        if len(terms) >= MAX_SEARCH_PASSES_PER_SOURCE:
            break
    return tuple(terms or [normalized_query])


def _list_postings(
    client: httpx.Client,
    source: SmartRecruitersSource,
    search_term: str,
    cache_seconds: int,
) -> list[dict[str, Any]]:
    cache_key = f"{source.identifier}:{search_term}"
    cached = _cache_get(_LIST_CACHE, cache_key)
    if isinstance(cached, list):
        return cached
    response = client.get(
        f"{SMARTRECRUITERS_BASE_URL}/{source.identifier}/postings",
        params={
            "q": search_term,
            "limit": str(MAX_LIST_RESULTS),
            "offset": "0",
            "country": "us",
            "destination": "PUBLIC",
        },
        headers={
            "Accept": "application/json",
            "User-Agent": "MarketLens Career Intelligence",
        },
    )
    response.raise_for_status()
    payload = response.json()
    raw_content = payload.get("content", []) if isinstance(payload, dict) else []
    postings = [item for item in raw_content if isinstance(item, dict)]
    _cache_put(_LIST_CACHE, cache_key, postings, cache_seconds)
    return postings


def _posting_details(
    client: httpx.Client,
    source: SmartRecruitersSource,
    posting_id: str,
    cache_seconds: int,
) -> dict[str, Any]:
    cache_key = f"{source.identifier}:{posting_id}"
    cached = _cache_get(_DETAIL_CACHE, cache_key)
    if isinstance(cached, dict):
        return cached
    response = client.get(
        f"{SMARTRECRUITERS_BASE_URL}/{source.identifier}/postings/{posting_id}",
        headers={
            "Accept": "application/json",
            "User-Agent": "MarketLens Career Intelligence",
        },
    )
    response.raise_for_status()
    payload = response.json()
    details = payload if isinstance(payload, dict) else {}
    _cache_put(_DETAIL_CACHE, cache_key, details, cache_seconds)
    return details


def _metadata_label(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    return str(value.get("label") or "").strip() if isinstance(value, dict) else ""


def _posting_location(raw: dict[str, Any]) -> str | None:
    location = raw.get("location")
    if not isinstance(location, dict):
        return None
    country = str(location.get("country") or "").strip()
    city = str(location.get("city") or "").strip()
    region = str(location.get("region") or "").strip()
    if bool(location.get("remote")):
        if country.lower() in {"us", "usa", "united states", "united states of america"}:
            return "Remote - United States"
        return f"Remote - {country}" if country else "Remote"
    parts = [part for part in (city, region) if part]
    if country:
        parts.append(
            "United States"
            if country.lower() in {"us", "usa", "united states", "united states of america"}
            else country
        )
    return ", ".join(parts) or None


def _preliminary_description(raw: dict[str, Any], title: str) -> str:
    parts = [title]
    for key in ("industry", "department", "function", "experienceLevel", "typeOfEmployment"):
        label = _metadata_label(raw, key)
        if label:
            parts.append(label)
    return " ".join(parts)


def _detail_description(job_search: Any, details: dict[str, Any], title: str) -> str:
    parts: list[str] = []
    job_ad = details.get("jobAd")
    if isinstance(job_ad, dict):
        for key in ("companyDescription", "jobDescription", "qualifications", "additionalInformation"):
            value = job_ad.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(value)
    for key in ("industry", "department", "function", "experienceLevel", "typeOfEmployment"):
        label = _metadata_label(details, key)
        if label:
            parts.append(label)
    return job_search.clean_job_description(" ".join(parts)) or title


def _normalize_posting(
    job_search: Any,
    source: SmartRecruitersSource,
    raw: dict[str, Any],
    details: dict[str, Any],
) -> Any | None:
    posting_id = str(raw.get("id") or raw.get("uuid") or "").strip()
    title = str(details.get("name") or raw.get("name") or "").strip()
    if not posting_id or not title:
        return None
    apply_url = sanitize_external_https_url(
        str(details.get("applyUrl") or details.get("postingUrl") or "")
    )
    if apply_url is None:
        return None
    company = source.organization
    company_payload = details.get("company")
    if isinstance(company_payload, dict):
        company = str(company_payload.get("name") or company).strip() or company
    return job_search.ExternalJobResult(
        id=f"smartrecruiters:{source.identifier}:{posting_id}",
        source="smartrecruiters",
        company=company,
        title=title,
        location=_posting_location(details) or _posting_location(raw),
        description=_detail_description(job_search, details, title)[:50_000],
        apply_url=apply_url,
        updated_at=str(details.get("releasedDate") or raw.get("releasedDate") or "").strip() or None,
    )


def _search_smartrecruiters(
    job_search: Any,
    query: str,
    location: str | None,
    level: str,
    selected_sources: tuple[SmartRecruitersSource, ...] | None = None,
) -> tuple[Any | None, tuple[SmartRecruitersSource, ...]]:
    sources = selected_sources or select_smartrecruiters_sources(
        job_search,
        query,
        location,
        level,
    )
    if not sources:
        return None, sources

    preliminary: dict[
        tuple[str, str],
        tuple[int, SmartRecruitersSource, dict[str, Any]],
    ] = {}
    fetched_count = list_errors = detail_errors = 0
    scored_jobs: list[tuple[int, Any]] = []
    cache_seconds = job_search._provider_cache_seconds()

    try:
        with job_search._build_provider_client() as client:
            postings_by_source: dict[str, dict[str, dict[str, Any]]] = {
                source.identifier: {} for source in sources
            }
            list_tasks = [
                (source, search_term)
                for source in sources
                for search_term in _search_terms(query)
            ]
            if list_tasks:
                with ThreadPoolExecutor(
                    max_workers=min(8, len(list_tasks)),
                    thread_name_prefix="marketlens-smartrecruiters-list",
                ) as executor:
                    futures = {
                        executor.submit(
                            _list_postings,
                            client,
                            source,
                            search_term,
                            cache_seconds,
                        ): source
                        for source, search_term in list_tasks
                    }
                    for future in as_completed(futures):
                        source = futures[future]
                        try:
                            postings = future.result()
                        except (httpx.HTTPError, ValueError):
                            list_errors += 1
                            continue
                        for raw in postings:
                            posting_id = str(
                                raw.get("id") or raw.get("uuid") or ""
                            ).strip()
                            if POSTING_ID_PATTERN.fullmatch(posting_id):
                                postings_by_source[source.identifier][posting_id] = raw

            for source in sources:
                source_postings = postings_by_source[source.identifier]
                fetched_count += len(source_postings)
                for posting_id, raw in source_postings.items():
                    title = str(raw.get("name") or "").strip()
                    location_text = _posting_location(raw)
                    if (
                        not title
                        or not job_search._matches_location(location_text, location)
                    ):
                        continue
                    role_score = job_search._score_job(
                        title,
                        _preliminary_description(raw, title),
                        query,
                        "any",
                        company=source.organization,
                    )
                    if role_score > 0:
                        preliminary[(source.identifier, posting_id)] = (
                            role_score
                            + job_search._location_score_bonus(
                                location_text,
                                location,
                            ),
                            source,
                            raw,
                        )

            ranked = sorted(
                preliminary.values(),
                key=lambda item: (
                    -item[0],
                    item[1].organization,
                    str(item[2].get("name") or ""),
                ),
            )[:MAX_DETAIL_REQUESTS]
            if ranked:
                with ThreadPoolExecutor(
                    max_workers=min(8, len(ranked)),
                    thread_name_prefix="marketlens-smartrecruiters-detail",
                ) as executor:
                    futures = {}
                    for _, source, raw in ranked:
                        posting_id = str(
                            raw.get("id") or raw.get("uuid") or ""
                        ).strip()
                        if not POSTING_ID_PATTERN.fullmatch(posting_id):
                            continue
                        future = executor.submit(
                            _posting_details,
                            client,
                            source,
                            posting_id,
                            cache_seconds,
                        )
                        futures[future] = (source, raw)

                    for future in as_completed(futures):
                        source, raw = futures[future]
                        try:
                            details = future.result()
                        except (httpx.HTTPError, ValueError):
                            detail_errors += 1
                            continue
                        job = _normalize_posting(
                            job_search,
                            source,
                            raw,
                            details,
                        )
                        if (
                            job is None
                            or not job_search._matches_location(
                                job.location,
                                location,
                            )
                        ):
                            continue
                        score = job_search._score_job(
                            job.title,
                            job.description,
                            query,
                            level,
                            company=job.company,
                        )
                        if score > 0:
                            scored_jobs.append(
                                (
                                    score
                                    + job_search._location_score_bonus(
                                        job.location,
                                        location,
                                    ),
                                    job,
                                )
                            )
    except (httpx.HTTPError, ValueError):
        list_errors += 1

    notes = [
        "Intent-selected public company boards: "
        + ", ".join(source.organization for source in sources)
        + "."
    ]
    if list_errors:
        notes.append(
            f"{list_errors} SmartRecruiters listing request"
            f"{'s' if list_errors != 1 else ''} failed or returned invalid data."
        )
    if detail_errors:
        notes.append(
            f"{detail_errors} SmartRecruiters detail request"
            f"{'s' if detail_errors != 1 else ''} failed or returned invalid data."
        )
    notes.append(
        "Only public postings from the named employers were queried; SmartRecruiters "
        "was not treated as a universal job-board search."
    )
    status = "failed" if fetched_count == 0 and list_errors else "searched"
    return (
        job_search._ProviderOutcome(
            "smartrecruiters",
            "SmartRecruiters cross-sector company boards",
            fetched_count,
            scored_jobs,
            status=status,
            notes=notes,
        ),
        sources,
    )

def _dedupe_key(job: Any) -> tuple[str, str, str]:
    return (
        job.company.strip().lower(),
        job.title.strip().lower(),
        (job.location or "").strip().lower(),
    )


def apply_job_search_source_expansion(job_search: Any) -> None:
    if getattr(job_search, "_SOURCE_EXPANSION_APPLIED", False):
        return
    original_search = job_search.search_external_jobs

    def search_external_jobs(
        query: str,
        location: str | None = None,
        limit: int = 15,
        level: str | None = None,
    ) -> Any:
        if not _smartrecruiters_enabled():
            return original_search(
                query=query,
                location=location,
                limit=limit,
                level=level,
            )

        intent = job_search.parse_job_search_intent(
            query=query,
            location=location,
            level=level,
        )
        sources = select_smartrecruiters_sources(
            job_search,
            intent.query,
            intent.location,
            intent.level,
        )
        if not sources:
            return original_search(
                query=query,
                location=location,
                limit=limit,
                level=level,
            )

        # The established providers and the cross-sector company boards are
        # independent. Run them concurrently so additional coverage does not
        # simply add another full provider round-trip to user-facing latency.
        with ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="marketlens-provider-group",
        ) as executor:
            base_future = executor.submit(
                original_search,
                query=query,
                location=location,
                limit=limit,
                level=level,
            )
            smartrecruiters_future = executor.submit(
                _search_smartrecruiters,
                job_search,
                intent.query,
                intent.location,
                intent.level,
                sources,
            )
            base = base_future.result()
            outcome, selected_sources = smartrecruiters_future.result()

        if outcome is None:
            return base

        scored: list[tuple[int, Any]] = list(outcome.scored_jobs)
        for job in base.results:
            score = job_search._score_job(
                job.title,
                job.description,
                base.query,
                base.level,
                company=job.company,
            )
            if score > 0:
                scored.append(
                    (
                        score
                        + job_search._location_score_bonus(
                            job.location,
                            base.location,
                        ),
                        job,
                    )
                )

        results: list[Any] = []
        seen_ids: set[str] = set()
        seen_jobs: set[tuple[str, str, str]] = set()
        for _, job in sorted(
            scored,
            key=lambda item: (
                -item[0],
                item[1].company,
                item[1].title,
            ),
        ):
            semantic_key = _dedupe_key(job)
            if job.id in seen_ids or semantic_key in seen_jobs:
                continue
            seen_ids.add(job.id)
            seen_jobs.add(semantic_key)
            results.append(job)
            if len(results) >= limit:
                break

        warnings = list(base.warnings)
        if results and not base.results:
            warnings = [
                warning
                for warning in warnings
                if "failed to respond" in warning.lower()
            ]

        return job_search.JobSearchResults(
            query=base.query,
            location=base.location,
            level=base.level,
            providers_searched=[
                *base.providers_searched,
                *(
                    f"smartrecruiters:{source.identifier}"
                    for source in selected_sources
                ),
            ],
            results=results,
            warnings=warnings,
            role_family=base.role_family,
            industry=base.industry,
            source_coverage=[
                *base.source_coverage,
                job_search._coverage_from_outcome(outcome),
            ],
            search_suggestions=base.search_suggestions,
            external_search_links=base.external_search_links,
        )

    job_search.search_external_jobs = search_external_jobs
    job_search._SOURCE_EXPANSION_APPLIED = True
