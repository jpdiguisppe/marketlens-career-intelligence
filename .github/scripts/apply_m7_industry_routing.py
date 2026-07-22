from __future__ import annotations

from pathlib import Path

JOB_SEARCH_PATH = Path("backend/app/job_search.py")
INTEGRATION_TEST_PATH = Path("backend/tests/test_job_search_routing_integration.py")

IMPORT_BEFORE = '''from app.job_source_registry import (
    configured_source_identifiers,
    default_source_identifiers,
    organization_name,
)
'''
IMPORT_AFTER = '''from app.job_source_registry import (
    configured_source_identifiers,
    default_source_identifiers,
    organization_name,
)
from app.job_source_routing import build_source_routing_plan
'''

CONFIG_BEFORE = '''    greenhouse_boards = _configured_greenhouse_boards()
    lever_sites = _configured_lever_sites()
    remoteok_enabled = _remoteok_enabled()
'''
CONFIG_AFTER = '''    configured_greenhouse_boards = _configured_greenhouse_boards()
    configured_lever_sites = _configured_lever_sites()
    routing_plan = build_source_routing_plan(
        greenhouse_identifiers=configured_greenhouse_boards,
        lever_identifiers=configured_lever_sites,
        industry=industry,
        job_function=role_family,
        level=resolved_level,
        location=cleaned_location,
    )
    greenhouse_boards = list(routing_plan.greenhouse_identifiers)
    lever_sites = list(routing_plan.lever_identifiers)
    remoteok_enabled = _remoteok_enabled()
'''

OUTCOMES_BEFORE = '''            outcomes.append(_search_greenhouse_boards(client, greenhouse_boards, cleaned_query, cleaned_location, resolved_level))
            outcomes.append(_search_lever_sites(client, lever_sites, cleaned_query, cleaned_location, resolved_level))
'''
OUTCOMES_AFTER = '''            greenhouse_outcome = _search_greenhouse_boards(
                client,
                greenhouse_boards,
                cleaned_query,
                cleaned_location,
                resolved_level,
            )
            greenhouse_outcome.notes.insert(0, routing_plan.greenhouse_note)
            outcomes.append(greenhouse_outcome)

            lever_outcome = _search_lever_sites(
                client,
                lever_sites,
                cleaned_query,
                cleaned_location,
                resolved_level,
            )
            lever_outcome.notes.insert(0, routing_plan.lever_note)
            outcomes.append(lever_outcome)
'''

INTEGRATION_TEST = '''from __future__ import annotations

from contextlib import nullcontext

from app import job_search


def test_search_external_jobs_routes_industry_specific_sources(monkeypatch) -> None:
    captured: dict[str, list[str]] = {}

    monkeypatch.setattr(job_search, "_build_provider_client", lambda: nullcontext(object()))
    monkeypatch.setattr(job_search, "_remoteok_enabled", lambda: False)
    monkeypatch.setattr(job_search, "_remotive_enabled", lambda: False)

    def fake_greenhouse(client, board_tokens, query, location, level):
        captured["greenhouse"] = list(board_tokens)
        return job_search._ProviderOutcome(
            "greenhouse",
            "Greenhouse company boards",
            0,
            [],
            notes=[],
        )

    def fake_lever(client, site_names, query, location, level):
        captured["lever"] = list(site_names)
        return job_search._ProviderOutcome(
            "lever",
            "Lever company boards",
            0,
            [],
            notes=[],
        )

    monkeypatch.setattr(job_search, "_search_greenhouse_boards", fake_greenhouse)
    monkeypatch.setattr(job_search, "_search_lever_sites", fake_lever)

    result = job_search.search_external_jobs(
        query="education software internship",
        location="Philadelphia",
        level="intern",
    )

    assert "duolingo" in captured["greenhouse"]
    assert "coursera" in captured["lever"]
    assert len(captured["greenhouse"]) < len(job_search.DEFAULT_GREENHOUSE_BOARDS)
    assert len(captured["lever"]) < len(job_search.DEFAULT_LEVER_SITES)
    assert result.providers_searched == [
        *(f"greenhouse:{identifier}" for identifier in captured["greenhouse"]),
        *(f"lever:{identifier}" for identifier in captured["lever"]),
    ]
    assert "Intent-aware routing selected" in result.source_coverage[0].notes[0]
    assert "industry=education" in result.source_coverage[0].notes[0]


def test_search_external_jobs_keeps_broad_search_sources(monkeypatch) -> None:
    captured: dict[str, list[str]] = {}

    monkeypatch.setattr(job_search, "_build_provider_client", lambda: nullcontext(object()))
    monkeypatch.setattr(job_search, "_remoteok_enabled", lambda: False)
    monkeypatch.setattr(job_search, "_remotive_enabled", lambda: False)

    def fake_greenhouse(client, board_tokens, query, location, level):
        captured["greenhouse"] = list(board_tokens)
        return job_search._ProviderOutcome("greenhouse", "Greenhouse", 0, [], notes=[])

    def fake_lever(client, site_names, query, location, level):
        captured["lever"] = list(site_names)
        return job_search._ProviderOutcome("lever", "Lever", 0, [], notes=[])

    monkeypatch.setattr(job_search, "_search_greenhouse_boards", fake_greenhouse)
    monkeypatch.setattr(job_search, "_search_lever_sites", fake_lever)

    result = job_search.search_external_jobs(query="software engineer")

    assert captured["greenhouse"] == list(job_search.DEFAULT_GREENHOUSE_BOARDS)
    assert captured["lever"] == list(job_search.DEFAULT_LEVER_SITES)
    assert "kept all" in result.source_coverage[0].notes[0]
'''


def replace_once(text: str, before: str, after: str, label: str) -> str:
    if after in text:
        return text
    count = text.count(before)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} target, found {count}.")
    return text.replace(before, after, 1)


def main() -> None:
    text = JOB_SEARCH_PATH.read_text(encoding="utf-8")
    text = replace_once(text, IMPORT_BEFORE, IMPORT_AFTER, "routing import")
    text = replace_once(text, CONFIG_BEFORE, CONFIG_AFTER, "routing configuration")
    text = replace_once(text, OUTCOMES_BEFORE, OUTCOMES_AFTER, "provider outcomes")
    JOB_SEARCH_PATH.write_text(text, encoding="utf-8")
    INTEGRATION_TEST_PATH.write_text(INTEGRATION_TEST, encoding="utf-8")


if __name__ == "__main__":
    main()
