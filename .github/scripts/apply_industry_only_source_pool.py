from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(relative_path: str, old: str, new: str) -> None:
    path = ROOT / relative_path
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one match in {relative_path}, found {count}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1))


# Registry: introduce explicit primary and industry-only pools.
replace_once(
    "backend/app/job_source_registry.py",
    'Provider = Literal["greenhouse", "lever"]\nEarlyCareerRelevance = Literal["general", "strong", "limited", "unknown"]',
    'Provider = Literal["greenhouse", "lever"]\nSourcePool = Literal["primary", "industry_only"]\nEarlyCareerRelevance = Literal["general", "strong", "limited", "unknown"]',
)
replace_once(
    "backend/app/job_source_registry.py",
    '    geographic_focus: tuple[str, ...]\n    enabled: bool = True',
    '    geographic_focus: tuple[str, ...]\n    source_pool: SourcePool = "primary"\n    enabled: bool = True',
)
replace_once(
    "backend/app/job_source_registry.py",
    '    geographic_focus: tuple[str, ...] = ("varies_by_posting",),\n    coverage_note: str | None = None,',
    '    geographic_focus: tuple[str, ...] = ("varies_by_posting",),\n    source_pool: SourcePool = "primary",\n    coverage_note: str | None = None,',
)
replace_once(
    "backend/app/job_source_registry.py",
    '        geographic_focus=geographic_focus,\n        coverage_note=coverage_note or DEFAULT_COVERAGE_NOTE,',
    '        geographic_focus=geographic_focus,\n        source_pool=source_pool,\n        coverage_note=coverage_note or DEFAULT_COVERAGE_NOTE,',
)
for identifier in ("theathletic", "feldinc", "standtogether"):
    marker = f'        "{identifier}",'
    path = ROOT / "backend/app/job_source_registry.py"
    text = path.read_text()
    start = text.index(marker)
    end = text.index("    ),", start)
    block = text[start:end]
    if 'source_pool="industry_only"' not in block:
        block = block + '\n        source_pool="industry_only",'
        path.write_text(text[:start] + block + text[end:])

replace_once(
    "backend/app/job_source_registry.py",
    'def source_registry_entries(\n    provider: Provider | None = None,\n    *,\n    enabled_only: bool = True,\n) -> tuple[JobSourceRegistryEntry, ...]:',
    'def source_registry_entries(\n    provider: Provider | None = None,\n    *,\n    enabled_only: bool = True,\n    source_pool: SourcePool | None = None,\n) -> tuple[JobSourceRegistryEntry, ...]:',
)
replace_once(
    "backend/app/job_source_registry.py",
    '        if (provider is None or entry.provider == provider)\n        and (entry.enabled or not enabled_only)',
    '        if (provider is None or entry.provider == provider)\n        and (entry.enabled or not enabled_only)\n        and (source_pool is None or entry.source_pool == source_pool)',
)
replace_once(
    "backend/app/job_source_registry.py",
    'def default_source_identifiers(provider: Provider) -> tuple[str, ...]:\n    return tuple(entry.identifier for entry in source_registry_entries(provider))',
    'def default_source_identifiers(provider: Provider) -> tuple[str, ...]:\n    """Return primary sources used by broad searches."""\n    return tuple(\n        entry.identifier\n        for entry in source_registry_entries(provider, source_pool="primary")\n    )\n\n\ndef industry_source_identifiers(provider: Provider) -> tuple[str, ...]:\n    """Return secondary sources that activate only for matching industries."""\n    return tuple(\n        entry.identifier\n        for entry in source_registry_entries(provider, source_pool="industry_only")\n    )',
)
replace_once(
    "backend/app/job_source_registry.py",
    'def configured_source_identifiers(\n    provider: Provider,\n    raw_identifiers: str | None,\n) -> tuple[str, ...]:',
    'def configured_source_identifiers(\n    provider: Provider,\n    raw_identifiers: str | None,\n    *,\n    source_pool: SourcePool = "primary",\n) -> tuple[str, ...]:',
)
replace_once(
    "backend/app/job_source_registry.py",
    '    defaults = default_source_identifiers(provider)',
    '    defaults = tuple(\n        entry.identifier\n        for entry in source_registry_entries(provider, source_pool=source_pool)\n    )',
)
replace_once(
    "backend/app/job_source_registry.py",
    '        if entry is not None and entry.enabled:\n            selected.append(normalized)',
    '        if (\n            entry is not None\n            and entry.enabled\n            and entry.source_pool == source_pool\n        ):\n            selected.append(normalized)',
)

# Routing: broad searches use primary sources only; exact-industry secondary sources join routed searches.
replace_once(
    "backend/app/job_source_routing.py",
    'from app.job_source_registry import JobSourceRegistryEntry, Provider, find_source',
    'from app.job_source_registry import (\n    JobSourceRegistryEntry,\n    Provider,\n    SourcePool,\n    find_source,\n)',
)
replace_once(
    "backend/app/job_source_routing.py",
    '    routed: bool\n    direct_industry_matches: int',
    '    routed: bool\n    direct_industry_matches: int\n    industry_only_sources_activated: int',
)
replace_once(
    "backend/app/job_source_routing.py",
    'def _registered_entries(\n    provider: Provider,\n    identifiers: list[str] | tuple[str, ...],\n) -> list[JobSourceRegistryEntry]:',
    'def _registered_entries(\n    provider: Provider,\n    identifiers: list[str] | tuple[str, ...],\n    *,\n    source_pool: SourcePool,\n) -> list[JobSourceRegistryEntry]:',
)
replace_once(
    "backend/app/job_source_routing.py",
    '        if entry is not None and entry.enabled:\n            entries.append(entry)',
    '        if (\n            entry is not None\n            and entry.enabled\n            and entry.source_pool == source_pool\n        ):\n            entries.append(entry)',
)
replace_once(
    "backend/app/job_source_routing.py",
    '    direct_match_count: int,\n    routed: bool,',
    '    direct_match_count: int,\n    industry_only_count: int,\n    routed: bool,',
)
replace_once(
    "backend/app/job_source_routing.py",
    '            "industry was detected. Job function, experience level, and location still filter and rank postings."',
    '            "industry was detected. Industry-only boards remained inactive; job function, experience level, "\n            "and location still filter and rank postings."',
)
replace_once(
    "backend/app/job_source_routing.py",
    '    return (\n        f"Intent-aware routing selected {selected_count} of {configured_count} configured {provider_label} boards "\n        f"for {\', \'.join(dimensions)}. {match_note}"\n    )',
    '    industry_pool_note = (\n        f" Activated {industry_only_count} matching industry-only "\n        f"{provider_label} board{\'s\' if industry_only_count != 1 else \'\'}."\n        if industry_only_count\n        else f" No matching industry-only {provider_label} boards were activated."\n    )\n    return (\n        f"Intent-aware routing selected {selected_count} of {configured_count} eligible {provider_label} boards "\n        f"for {\', \'.join(dimensions)}. {match_note}{industry_pool_note}"\n    )',
)
replace_once(
    "backend/app/job_source_routing.py",
    '    location: str | None,\n) -> SourceRoutingPlan:\n    greenhouse_entries = _registered_entries("greenhouse", greenhouse_identifiers)\n    lever_entries = _registered_entries("lever", lever_identifiers)\n    all_entries = greenhouse_entries + lever_entries',
    '    location: str | None,\n    greenhouse_industry_identifiers: list[str] | tuple[str, ...] = (),\n    lever_industry_identifiers: list[str] | tuple[str, ...] = (),\n) -> SourceRoutingPlan:\n    greenhouse_entries = _registered_entries(\n        "greenhouse", greenhouse_identifiers, source_pool="primary"\n    )\n    lever_entries = _registered_entries(\n        "lever", lever_identifiers, source_pool="primary"\n    )\n\n    greenhouse_industry_entries = (\n        [\n            entry\n            for entry in _registered_entries(\n                "greenhouse",\n                greenhouse_industry_identifiers,\n                source_pool="industry_only",\n            )\n            if industry is not None and industry in entry.industries\n        ]\n        if industry is not None\n        else []\n    )\n    lever_industry_entries = (\n        [\n            entry\n            for entry in _registered_entries(\n                "lever",\n                lever_industry_identifiers,\n                source_pool="industry_only",\n            )\n            if industry is not None and industry in entry.industries\n        ]\n        if industry is not None\n        else []\n    )\n    all_entries = (\n        greenhouse_entries\n        + lever_entries\n        + greenhouse_industry_entries\n        + lever_industry_entries\n    )',
)
# Add new constructor arguments in both broad provider notes and routed provider notes.
text_path = ROOT / "backend/app/job_source_routing.py"
text = text_path.read_text()
text = text.replace('                direct_match_count=0,\n                routed=False,', '                direct_match_count=0,\n                industry_only_count=0,\n                routed=False,')
text = text.replace('            direct_industry_matches=0,\n        )', '            direct_industry_matches=0,\n            industry_only_sources_activated=0,\n        )', 1)
text = text.replace(
    '            direct_match_count=greenhouse_direct_matches,\n            routed=True,',
    '            direct_match_count=greenhouse_direct_matches,\n            industry_only_count=len(greenhouse_industry_entries),\n            routed=True,',
)
text = text.replace(
    '            direct_match_count=lever_direct_matches,\n            routed=True,',
    '            direct_match_count=lever_direct_matches,\n            industry_only_count=len(lever_industry_entries),\n            routed=True,',
)
text = text.replace(
    '        direct_industry_matches=len(direct_entries),\n    )',
    '        direct_industry_matches=len(direct_entries),\n        industry_only_sources_activated=(\n            len(greenhouse_industry_entries) + len(lever_industry_entries)\n        ),\n    )',
)
text_path.write_text(text)

# Search integration: configure the two pools independently and pass both into routing.
replace_once(
    "backend/app/job_search.py",
    '    default_source_identifiers,\n    organization_name,',
    '    default_source_identifiers,\n    industry_source_identifiers,\n    organization_name,',
)
replace_once(
    "backend/app/job_search.py",
    'DEFAULT_GREENHOUSE_BOARDS = default_source_identifiers("greenhouse")\nDEFAULT_LEVER_SITES = default_source_identifiers("lever")',
    'DEFAULT_GREENHOUSE_BOARDS = default_source_identifiers("greenhouse")\nDEFAULT_LEVER_SITES = default_source_identifiers("lever")\nDEFAULT_GREENHOUSE_INDUSTRY_BOARDS = industry_source_identifiers("greenhouse")\nDEFAULT_LEVER_INDUSTRY_SITES = industry_source_identifiers("lever")',
)
replace_once(
    "backend/app/job_search.py",
    'def _remoteok_enabled() -> bool:',
    'def _configured_greenhouse_industry_boards() -> list[str]:\n    return list(\n        configured_source_identifiers(\n            "greenhouse",\n            os.getenv("JOB_SEARCH_GREENHOUSE_INDUSTRY_BOARDS"),\n            source_pool="industry_only",\n        )\n    )\n\n\ndef _configured_lever_industry_sites() -> list[str]:\n    return list(\n        configured_source_identifiers(\n            "lever",\n            os.getenv("JOB_SEARCH_LEVER_INDUSTRY_SITES"),\n            source_pool="industry_only",\n        )\n    )\n\n\ndef _remoteok_enabled() -> bool:',
)
replace_once(
    "backend/app/job_search.py",
    '    configured_greenhouse_boards = _configured_greenhouse_boards()\n    configured_lever_sites = _configured_lever_sites()\n    routing_plan = build_source_routing_plan(',
    '    configured_greenhouse_boards = _configured_greenhouse_boards()\n    configured_lever_sites = _configured_lever_sites()\n    configured_greenhouse_industry_boards = _configured_greenhouse_industry_boards()\n    configured_lever_industry_sites = _configured_lever_industry_sites()\n    routing_plan = build_source_routing_plan(',
)
replace_once(
    "backend/app/job_search.py",
    '        location=cleaned_location,\n    )',
    '        location=cleaned_location,\n        greenhouse_industry_identifiers=configured_greenhouse_industry_boards,\n        lever_industry_identifiers=configured_lever_industry_sites,\n    )',
)

# Focused tests for the source-pool boundary.
(ROOT / "backend/tests/test_job_source_registry.py").write_text('''from app.job_search import (\n    DEFAULT_GREENHOUSE_BOARDS,\n    DEFAULT_GREENHOUSE_INDUSTRY_BOARDS,\n    DEFAULT_LEVER_INDUSTRY_SITES,\n    DEFAULT_LEVER_SITES,\n    DEFAULT_MAX_PROVIDER_REQUESTS_PER_SEARCH,\n    _provider_company_name,\n)\nfrom app.job_source_registry import (\n    SOURCE_REGISTRY,\n    configured_source_identifiers,\n    default_source_identifiers,\n    find_source,\n    industry_source_identifiers,\n    normalize_source_identifier,\n    organization_name,\n    source_registry_entries,\n)\n\n\nEXPECTED_GREENHOUSE_BOARDS = (\n    "datadog", "airbnb", "figma", "duolingo", "roblox", "scaleai",\n    "hubspot", "cloudflare", "verkada", "doordash", "okta", "mongodb",\n    "asana", "plaid", "brex", "coinbase", "ramp", "gusto", "rippling", "affirm",\n)\nEXPECTED_LEVER_SITES = (\n    "github", "postman", "benchling", "box", "coursera", "lyft",\n    "pinterest", "reddit", "snap", "twitch", "zapier", "affirm",\n    "robinhood", "rippling", "webflow", "notion", "loom", "intercom",\n    "mixpanel", "fivetran", "algolia", "addepar",\n)\nEXPECTED_GREENHOUSE_INDUSTRY_BOARDS: tuple[str, ...] = ()\nEXPECTED_LEVER_INDUSTRY_SITES = ("theathletic", "feldinc", "standtogether")\n\n\ndef test_registry_keys_are_unique_and_metadata_is_complete() -> None:\n    keys = [(entry.provider, entry.identifier) for entry in SOURCE_REGISTRY]\n    assert len(keys) == len(set(keys))\n    assert all(entry.organization for entry in SOURCE_REGISTRY)\n    assert all(entry.industries for entry in SOURCE_REGISTRY)\n    assert all(entry.role_families for entry in SOURCE_REGISTRY)\n    assert all(entry.geographic_focus for entry in SOURCE_REGISTRY)\n    assert all(entry.coverage_note for entry in SOURCE_REGISTRY)\n    assert all(entry.source_pool in {"primary", "industry_only"} for entry in SOURCE_REGISTRY)\n\n\ndef test_registry_separates_primary_and_industry_only_defaults() -> None:\n    assert default_source_identifiers("greenhouse") == EXPECTED_GREENHOUSE_BOARDS\n    assert default_source_identifiers("lever") == EXPECTED_LEVER_SITES\n    assert industry_source_identifiers("greenhouse") == EXPECTED_GREENHOUSE_INDUSTRY_BOARDS\n    assert industry_source_identifiers("lever") == EXPECTED_LEVER_INDUSTRY_SITES\n    assert DEFAULT_GREENHOUSE_BOARDS == EXPECTED_GREENHOUSE_BOARDS\n    assert DEFAULT_LEVER_SITES == EXPECTED_LEVER_SITES\n    assert DEFAULT_GREENHOUSE_INDUSTRY_BOARDS == EXPECTED_GREENHOUSE_INDUSTRY_BOARDS\n    assert DEFAULT_LEVER_INDUSTRY_SITES == EXPECTED_LEVER_INDUSTRY_SITES\n\n\ndef test_registry_exposes_industry_metadata_and_source_pool() -> None:\n    duolingo = find_source("duolingo", "greenhouse")\n    the_athletic = find_source("theathletic", "lever")\n    feld = find_source("feldinc", "lever")\n    stand_together = find_source("standtogether", "lever")\n    assert duolingo is not None and duolingo.source_pool == "primary"\n    assert the_athletic is not None\n    assert {"sports", "media"}.issubset(the_athletic.industries)\n    assert the_athletic.source_pool == "industry_only"\n    assert feld is not None and feld.source_pool == "industry_only"\n    assert stand_together is not None\n    assert stand_together.source_pool == "industry_only"\n    assert stand_together.early_career_relevance == "strong"\n\n\ndef test_registry_lookup_and_company_name_fallbacks_are_stable() -> None:\n    assert organization_name("github", "lever") == "GitHub"\n    assert organization_name("theathletic", "lever") == "The Athletic"\n    assert _provider_company_name("doordash") == "DoorDash"\n    assert organization_name("example-company") == "Example Company"\n    assert find_source("missing-source", "greenhouse") is None\n\n\ndef test_registry_can_filter_by_provider_and_pool() -> None:\n    primary_lever = source_registry_entries("lever", source_pool="primary")\n    industry_lever = source_registry_entries("lever", source_pool="industry_only")\n    assert len(primary_lever) == len(EXPECTED_LEVER_SITES)\n    assert len(industry_lever) == len(EXPECTED_LEVER_INDUSTRY_SITES)\n    assert all(entry.provider == "lever" for entry in primary_lever + industry_lever)\n\n\ndef test_uncached_broad_search_gains_request_headroom() -> None:\n    ats_source_count = len(EXPECTED_GREENHOUSE_BOARDS) + len(EXPECTED_LEVER_SITES)\n    assert ats_source_count <= DEFAULT_MAX_PROVIDER_REQUESTS_PER_SEARCH - 6\n\n\ndef test_registry_rejects_malformed_and_unregistered_identifiers() -> None:\n    assert normalize_source_identifier("github") == "github"\n    assert normalize_source_identifier("../internal") is None\n    assert normalize_source_identifier("https://evil.example") is None\n    assert normalize_source_identifier("name with spaces") is None\n    assert find_source("../internal", "lever") is None\n\n\ndef test_environment_configuration_cannot_move_sources_between_pools() -> None:\n    assert configured_source_identifiers(\n        "lever", " github,../internal,unknown-company,theathletic "\n    ) == ("github",)\n    assert configured_source_identifiers(\n        "lever", " github,theathletic,feldinc ", source_pool="industry_only"\n    ) == ("theathletic", "feldinc")\n    assert configured_source_identifiers(\n        "greenhouse", "https://evil.example,unknown-company"\n    ) == EXPECTED_GREENHOUSE_BOARDS\n''')

(ROOT / "backend/tests/test_job_source_routing.py").write_text('''from app.job_source_registry import default_source_identifiers, industry_source_identifiers\nfrom app.job_source_routing import MAX_INDUSTRY_ROUTED_SOURCES, build_source_routing_plan\n\n\ndef _plan(*, industry: str | None, job_function: str | None = None, level: str = "any", location: str | None = None):\n    return build_source_routing_plan(\n        greenhouse_identifiers=default_source_identifiers("greenhouse"),\n        lever_identifiers=default_source_identifiers("lever"),\n        industry=industry,\n        job_function=job_function,\n        level=level,  # type: ignore[arg-type]\n        location=location,\n        greenhouse_industry_identifiers=industry_source_identifiers("greenhouse"),\n        lever_industry_identifiers=industry_source_identifiers("lever"),\n    )\n\n\ndef test_broad_search_uses_only_primary_sources() -> None:\n    plan = _plan(industry=None, job_function="software", level="entry")\n    assert plan.routed is False\n    assert plan.greenhouse_identifiers == default_source_identifiers("greenhouse")\n    assert plan.lever_identifiers == default_source_identifiers("lever")\n    assert {"theathletic", "feldinc", "standtogether"}.isdisjoint(plan.lever_identifiers)\n    assert plan.industry_only_sources_activated == 0\n    assert "Industry-only boards remained inactive" in plan.lever_note\n\n\ndef test_financial_services_search_does_not_activate_unrelated_niche_sources() -> None:\n    plan = _plan(industry="financial_services", job_function="finance", level="intern", location="Philadelphia")\n    selected = set(plan.greenhouse_identifiers) | set(plan.lever_identifiers)\n    assert plan.routed is True\n    assert plan.direct_industry_matches >= 8\n    assert {"plaid", "brex", "ramp", "robinhood", "addepar"}.issubset(selected)\n    assert {"theathletic", "feldinc", "standtogether"}.isdisjoint(selected)\n    assert plan.industry_only_sources_activated == 0\n    assert len(selected) <= MAX_INDUSTRY_ROUTED_SOURCES\n\n\ndef test_education_search_activates_matching_mission_source() -> None:\n    plan = _plan(industry="education", job_function="software", level="entry")\n    assert "duolingo" in plan.greenhouse_identifiers\n    assert "coursera" in plan.lever_identifiers\n    assert "standtogether" in plan.lever_identifiers\n    assert plan.industry_only_sources_activated == 1\n    assert "Activated 1 matching industry-only Lever board" in plan.lever_note\n\n\ndef test_sports_search_activates_exact_industry_only_sources() -> None:\n    plan = _plan(industry="sports", job_function="marketing", level="intern")\n    selected = set(plan.greenhouse_identifiers) | set(plan.lever_identifiers)\n    assert plan.direct_industry_matches == 2\n    assert {"theathletic", "feldinc"}.issubset(selected)\n    assert "standtogether" not in selected\n    assert plan.industry_only_sources_activated == 2\n    assert "Activated 2 matching industry-only Lever boards" in plan.lever_note\n\n\ndef test_nonprofit_search_activates_only_stand_together() -> None:\n    plan = _plan(industry="nonprofit", job_function="marketing", level="intern")\n    assert plan.direct_industry_matches == 1\n    assert "standtogether" in plan.lever_identifiers\n    assert "theathletic" not in plan.lever_identifiers\n    assert "feldinc" not in plan.lever_identifiers\n    assert plan.industry_only_sources_activated == 1\n\n\ndef test_unregistered_and_wrong_pool_identifiers_are_never_routed() -> None:\n    plan = build_source_routing_plan(\n        greenhouse_identifiers=("duolingo", "../internal", "unknown-board"),\n        lever_identifiers=("coursera", "theathletic", "https://evil.example"),\n        industry="education",\n        job_function="software",\n        level="any",\n        location=None,\n        lever_industry_identifiers=("standtogether", "github", "unknown-board"),\n    )\n    assert plan.greenhouse_identifiers == ("duolingo",)\n    assert plan.lever_identifiers == ("coursera", "standtogether")\n''')

# Extend integration coverage without changing the existing test structure.
path = ROOT / "backend/tests/test_job_search_routing_integration.py"
text = path.read_text()
text = text.replace(
    '    assert "coursera" in captured["lever"]\n',
    '    assert "coursera" in captured["lever"]\n    assert "standtogether" in captured["lever"]\n',
    1,
)
text = text.replace(
    '    assert "industry=education" in result.source_coverage[0].notes[0]\n',
    '    assert "industry=education" in result.source_coverage[0].notes[0]\n    assert "industry-only" in result.source_coverage[1].notes[0]\n',
    1,
)
text = text.replace(
    '    assert captured["lever"] == list(job_search.DEFAULT_LEVER_SITES)\n',
    '    assert captured["lever"] == list(job_search.DEFAULT_LEVER_SITES)\n    assert {"theathletic", "feldinc", "standtogether"}.isdisjoint(captured["lever"])\n',
    1,
)
path.write_text(text)

(ROOT / "docs/milestone-7-industry-only-source-pool.md").write_text('''# Milestone 7 — Secondary Industry-Only Source Pool\n\n## Objective\n\nAllow MarketLens to keep adding niche public ATS boards without forcing every broad search to request every specialized source.\n\n## Source pools\n\n- **Primary** sources participate in broad searches and remain available to industry-aware routing.\n- **Industry-only** sources stay inactive for broad searches and activate only when the detected industry exactly matches their registry metadata.\n\nThe Athletic, Feld Entertainment, and Stand Together now live in the industry-only pool. This preserves their value for sports, nonprofit, and education searches while removing three requests from uncached broad searches.\n\n## Configuration and safety\n\nPrimary and industry-only identifiers are configured independently. Registry allowlisting also enforces the pool boundary, so an environment variable cannot move a niche source into the broad-search pool or use an arbitrary provider token.\n\nThe existing request budget, caching, HTTPS validation, disabled redirects, rate limiting, and closed-board non-scraping behavior remain unchanged.\n\n## Scope boundary\n\nThis phase adds the source-pool architecture only. It does not add legal taxonomy, new legal sources, credential filtering, or broader early-career matching. Those remain later steps in the agreed Milestone 7 sequence.\n''')
