from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f"Expected exactly one match in {path}: {old[:120]!r}")
    path.write_text(text.replace(old, new, 1))


job_search = ROOT / "backend/app/job_search.py"
routing_tests = ROOT / "backend/tests/test_job_source_routing.py"

replace_once(
    job_search,
    '''def _text_matches_role_family(value: str, family: RoleFamily) -> bool:\n    return _contains_any(value.lower(), ROLE_FAMILY_TITLE_TERMS[family])\n\n\ndef _looks_like_software_role(title: str) -> bool:\n''',
    '''def _text_matches_role_family(value: str, family: RoleFamily) -> bool:\n    return _contains_any(value.lower(), ROLE_FAMILY_TITLE_TERMS[family])\n\n\nSTRICT_DESCRIPTION_ONLY_ROLE_FAMILIES: set[RoleFamily] = {\n    "legal",\n    "compliance",\n    "policy",\n    "legal_operations",\n    "contracts",\n}\n\n\ndef _title_matches_other_role_family(title: str, requested_family: RoleFamily) -> bool:\n    return any(\n        family not in {requested_family, "technology"}\n        and _title_matches_role_family(title, family)\n        for family in ROLE_FAMILY_TITLE_TERMS\n    )\n\n\ndef _looks_like_software_role(title: str) -> bool:\n''',
)

replace_once(
    job_search,
    '''    is_generic_early_career_title = _contains_any(\n        title_lower,\n        {"intern", "internship", "summer analyst", "analyst intern", "rotational program", "graduate program"},\n    )\n    return bool(\n''',
    '''    is_generic_early_career_title = _contains_any(\n        title_lower,\n        {"intern", "internship", "summer analyst", "analyst intern", "rotational program", "graduate program"},\n    )\n    if (\n        family in STRICT_DESCRIPTION_ONLY_ROLE_FAMILIES\n        and _title_matches_other_role_family(title, family)\n    ):\n        return False\n    return bool(\n''',
)

replace_once(
    routing_tests,
    '''    assert plan.direct_industry_matches == 2\n    assert {"standtogether", "stradaeducation"}.issubset(plan.lever_identifiers)\n    assert "theathletic" not in plan.lever_identifiers\n    assert "feldinc" not in plan.lever_identifiers\n    assert plan.industry_only_sources_activated == 2\n''',
    '''    assert plan.direct_industry_matches == 3\n    assert "aclu" in plan.greenhouse_identifiers\n    assert {"standtogether", "stradaeducation"}.issubset(plan.lever_identifiers)\n    assert "theathletic" not in plan.lever_identifiers\n    assert "feldinc" not in plan.lever_identifiers\n    assert plan.industry_only_sources_activated == 3\n''',
)

replace_once(
    routing_tests,
    '''    assert plan.greenhouse_identifiers == ("duolingo",)\n    assert plan.lever_identifiers == ("coursera", "standtogether")\n''',
    '''    assert plan.greenhouse_identifiers == ("duolingo",)\n    assert plan.lever_identifiers == (\n        "coursera",\n        "kiddom",\n        "stradaeducation",\n        "standtogether",\n    )\n''',
)

print("Fixed source expansion precision and updated routing expectations.")
