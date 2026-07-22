from __future__ import annotations

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
