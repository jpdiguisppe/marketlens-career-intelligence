from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f"Expected exactly one match in {path}: {old[:100]!r}")
    path.write_text(text.replace(old, new, 1))


registry = ROOT / "backend/app/job_source_registry.py"
routing = ROOT / "backend/app/job_source_routing.py"
job_search = ROOT / "backend/app/job_search.py"
registry_tests = ROOT / "backend/tests/test_job_source_registry.py"
routing_tests = ROOT / "backend/tests/test_job_source_routing.py"

replace_once(
    registry,
    '''ENTERTAINMENT_ROLE_FAMILIES = (\n    "data",\n    "product",\n    "design",\n    "marketing",\n    "operations",\n)\n''',
    '''ENTERTAINMENT_ROLE_FAMILIES = (\n    "data",\n    "product",\n    "design",\n    "marketing",\n    "operations",\n)\nLEGAL_ROLE_FAMILIES = (\n    "legal",\n    "compliance",\n    "policy",\n    "legal_operations",\n    "contracts",\n    "operations",\n    "marketing",\n    "data",\n)\nHEALTH_POLICY_ROLE_FAMILIES = HEALTH_ROLE_FAMILIES + (\n    "legal",\n    "compliance",\n    "policy",\n    "contracts",\n)\nMEDIA_POLICY_ROLE_FAMILIES = ENTERTAINMENT_ROLE_FAMILIES + (\n    "software",\n    "legal",\n    "compliance",\n    "policy",\n    "legal_operations",\n    "contracts",\n)\nEDUCATION_ROLE_FAMILIES = TECH_ROLE_FAMILIES + ("policy",)\nMISSION_POLICY_ROLE_FAMILIES = MISSION_ROLE_FAMILIES + (\n    "legal",\n    "compliance",\n    "policy",\n)\n''',
)

replace_once(
    registry,
    '''    _source("greenhouse", "affirm", "Affirm", ("financial_services", "fintech", "technology"), FINTECH_ROLE_FAMILIES),\n    _source("lever", "github", "GitHub", ("technology", "software")),\n''',
    '''    _source("greenhouse", "affirm", "Affirm", ("financial_services", "fintech", "technology"), FINTECH_ROLE_FAMILIES),\n    _source(\n        "greenhouse",\n        "aclu",\n        "ACLU",\n        ("legal_services", "public_interest", "nonprofit", "government", "public_policy"),\n        LEGAL_ROLE_FAMILIES,\n        geographic_focus=("united_states", "varies_by_posting"),\n        source_pool="industry_only",\n        coverage_note="Official public Greenhouse board for national civil-liberties, legal, policy, and advocacy roles.",\n    ),\n    _source("lever", "github", "GitHub", ("technology", "software")),\n''',
)

replace_once(
    registry,
    '''    _source("lever", "addepar", "Addepar", ("financial_services", "fintech", "technology"), FINTECH_ROLE_FAMILIES),\n    _source(\n        "lever",\n        "theathletic",\n''',
    '''    _source("lever", "addepar", "Addepar", ("financial_services", "fintech", "technology"), FINTECH_ROLE_FAMILIES),\n    _source(\n        "lever",\n        "avalerehealth",\n        "Avalere Health",\n        ("healthcare", "life_sciences", "public_policy", "government"),\n        HEALTH_POLICY_ROLE_FAMILIES,\n        geographic_focus=("united_states", "remote", "varies_by_posting"),\n        source_pool="industry_only",\n        coverage_note="Official public Lever board spanning healthcare policy, advisory, medical, marketing, and operations roles.",\n    ),\n    _source(\n        "lever",\n        "wattpad",\n        "WEBTOON / Wattpad",\n        ("media", "entertainment", "publishing", "corporate_legal"),\n        MEDIA_POLICY_ROLE_FAMILIES,\n        early_career_relevance="strong",\n        geographic_focus=("united_states", "varies_by_posting"),\n        source_pool="industry_only",\n        coverage_note="Official public Lever board with media, content-policy, legal-business, and internship roles.",\n    ),\n    _source(\n        "lever",\n        "thedispatch",\n        "The Dispatch",\n        ("media", "journalism", "public_policy", "legal_services"),\n        ("policy", "legal", "marketing", "operations", "design"),\n        early_career_relevance="strong",\n        geographic_focus=("united_states", "remote", "varies_by_posting"),\n        source_pool="industry_only",\n        coverage_note="Official public Lever board for journalism, policy-adjacent media, and recurring internship roles.",\n    ),\n    _source(\n        "lever",\n        "kiddom",\n        "Kiddom",\n        ("education", "technology"),\n        EDUCATION_ROLE_FAMILIES,\n        geographic_focus=("united_states", "remote", "varies_by_posting"),\n        source_pool="industry_only",\n        coverage_note="Official public Lever board for K-12 education technology, curriculum, product, and operations roles.",\n    ),\n    _source(\n        "lever",\n        "stradaeducation",\n        "Strada Education Foundation",\n        ("education", "nonprofit", "public_interest", "public_policy", "social_impact"),\n        MISSION_POLICY_ROLE_FAMILIES,\n        early_career_relevance="strong",\n        geographic_focus=("united_states", "varies_by_posting"),\n        source_pool="industry_only",\n        coverage_note="Official public Lever board for education, workforce policy, nonprofit, internship, and co-op pathways.",\n    ),\n    _source(\n        "lever",\n        "theathletic",\n''',
)

replace_once(
    routing,
    '''INDUSTRY_ADJACENCIES: dict[str, frozenset[str]] = {\n    "sports": frozenset({"entertainment", "media", "gaming"}),\n    "entertainment": frozenset({"media", "gaming", "sports"}),\n    "healthcare": frozenset({"life_sciences", "technology"}),\n    "financial_services": frozenset({"fintech", "technology"}),\n    "education": frozenset({"technology"}),\n    "nonprofit": frozenset({"education", "healthcare", "media"}),\n    "media": frozenset({"entertainment", "gaming", "technology"}),\n}\n''',
    '''INDUSTRY_ADJACENCIES: dict[str, frozenset[str]] = {\n    "sports": frozenset({"entertainment", "media", "gaming"}),\n    "entertainment": frozenset({"media", "gaming", "sports"}),\n    "healthcare": frozenset({"life_sciences", "technology", "public_policy"}),\n    "financial_services": frozenset({"fintech", "technology", "corporate_legal"}),\n    "education": frozenset({"technology", "nonprofit", "public_policy"}),\n    "nonprofit": frozenset({"education", "healthcare", "media", "public_interest", "public_policy"}),\n    "media": frozenset({"entertainment", "gaming", "technology", "corporate_legal"}),\n    "legal_services": frozenset({"public_interest", "government", "nonprofit", "corporate_legal", "public_policy"}),\n    "public_interest": frozenset({"nonprofit", "government", "legal_services", "public_policy"}),\n    "government": frozenset({"public_policy", "legal_services", "public_interest", "nonprofit"}),\n    "corporate_legal": frozenset({"legal_services", "financial_services", "healthcare", "media"}),\n    "public_policy": frozenset({"government", "nonprofit", "healthcare", "education", "legal_services"}),\n}\n''',
)

replace_once(
    job_search,
    '''    "healthcare",\n    "design",\n]\nIndustry = Literal[\n''',
    '''    "healthcare",\n    "design",\n    "legal",\n    "compliance",\n    "policy",\n    "legal_operations",\n    "contracts",\n]\nIndustry = Literal[\n''',
)
replace_once(
    job_search,
    '''    "nonprofit",\n    "media",\n]\n''',
    '''    "nonprofit",\n    "media",\n    "legal_services",\n    "government",\n    "public_interest",\n    "corporate_legal",\n    "public_policy",\n]\n''',
)

replace_once(
    job_search,
    '''DESIGN_TITLE_TERMS = {\n    "designer",\n    "product designer",\n    "ux",\n    "ui designer",\n    "visual designer",\n    "graphic designer",\n}\nTECHNOLOGY_TITLE_TERMS = SOFTWARE_TITLE_TERMS | DATA_TITLE_TERMS | CYBERSECURITY_TITLE_TERMS\n''',
    '''DESIGN_TITLE_TERMS = {\n    "designer",\n    "product designer",\n    "ux",\n    "ui designer",\n    "visual designer",\n    "graphic designer",\n}\nLEGAL_TITLE_TERMS = {\n    "legal intern",\n    "legal assistant",\n    "legal analyst",\n    "legal coordinator",\n    "paralegal",\n    "law clerk",\n    "attorney",\n    "counsel",\n    "litigation",\n}\nCOMPLIANCE_TITLE_TERMS = {\n    "compliance",\n    "regulatory",\n    "risk and compliance",\n    "aml",\n    "kyc",\n    "ethics",\n}\nPOLICY_TITLE_TERMS = {\n    "policy analyst",\n    "policy associate",\n    "policy intern",\n    "public policy",\n    "government affairs",\n    "public affairs",\n    "legislative",\n    "advocacy",\n}\nLEGAL_OPERATIONS_TITLE_TERMS = {\n    "legal operations",\n    "legal ops",\n    "litigation support",\n    "legal project manager",\n    "legal technology",\n    "e-billing",\n}\nCONTRACTS_TITLE_TERMS = {\n    "contracts analyst",\n    "contract analyst",\n    "contracts specialist",\n    "contract specialist",\n    "contract administrator",\n    "commercial contracts",\n}\nTECHNOLOGY_TITLE_TERMS = SOFTWARE_TITLE_TERMS | DATA_TITLE_TERMS | CYBERSECURITY_TITLE_TERMS\n''',
)

replace_once(
    job_search,
    '''    "healthcare": HEALTHCARE_TITLE_TERMS,\n    "design": DESIGN_TITLE_TERMS,\n}\n''',
    '''    "healthcare": HEALTHCARE_TITLE_TERMS,\n    "design": DESIGN_TITLE_TERMS,\n    "legal": LEGAL_TITLE_TERMS,\n    "compliance": COMPLIANCE_TITLE_TERMS,\n    "policy": POLICY_TITLE_TERMS,\n    "legal_operations": LEGAL_OPERATIONS_TITLE_TERMS,\n    "contracts": CONTRACTS_TITLE_TERMS,\n}\n''',
)

replace_once(
    job_search,
    '''    "healthcare": {"healthcare", "health care", "clinical", "patient", "medical", "hospital"},\n    "design": {"design", "designer", "ux", "ui", "visual design", "graphic design"},\n}\n''',
    '''    "healthcare": {"healthcare", "health care", "clinical", "patient", "medical", "hospital"},\n    "design": {"design", "designer", "ux", "ui", "visual design", "graphic design"},\n    "legal": {"legal", "law", "paralegal", "attorney", "counsel", "litigation", "law clerk"},\n    "compliance": {"compliance", "regulatory", "regulatory affairs", "aml", "kyc", "ethics", "risk and compliance"},\n    "policy": {"policy", "public policy", "government affairs", "public affairs", "legislative", "advocacy"},\n    "legal_operations": {"legal operations", "legal ops", "litigation support", "legal technology"},\n    "contracts": {"contracts", "contract analyst", "contracts analyst", "contract specialist", "contract administrator"},\n}\n''',
)

replace_once(
    job_search,
    '''    "nonprofit": {"nonprofit", "non-profit", "charity", "foundation", "social impact"},\n    "media": {"media", "journalism", "publishing", "news", "broadcast", "broadcasting"},\n}\n''',
    '''    "nonprofit": {"nonprofit", "non-profit", "charity", "foundation", "social impact"},\n    "media": {"media", "journalism", "publishing", "news", "broadcast", "broadcasting"},\n    "public_interest": {"public interest", "civil liberties", "civil rights", "legal aid"},\n    "government": {"government", "public sector", "federal government", "state government", "municipal"},\n    "corporate_legal": {"corporate legal", "in-house legal", "in house legal", "legal department"},\n    "public_policy": {"public policy", "policy research", "regulatory policy"},\n    "legal_services": {"legal", "law firm", "law office", "litigation", "paralegal", "attorney"},\n}\n''',
)

replace_once(
    job_search,
    '''CROSS_INDUSTRY_FUNCTION_QUERY_TERMS: dict[RoleFamily, set[str]] = {\n    "software": ROLE_FAMILY_QUERY_TERMS["software"],\n''',
    '''CROSS_INDUSTRY_FUNCTION_QUERY_TERMS: dict[RoleFamily, set[str]] = {\n    "legal_operations": ROLE_FAMILY_QUERY_TERMS["legal_operations"],\n    "contracts": ROLE_FAMILY_QUERY_TERMS["contracts"],\n    "compliance": ROLE_FAMILY_QUERY_TERMS["compliance"],\n    "policy": ROLE_FAMILY_QUERY_TERMS["policy"],\n    "legal": ROLE_FAMILY_QUERY_TERMS["legal"],\n    "software": ROLE_FAMILY_QUERY_TERMS["software"],\n''',
)

replace_once(
    registry_tests,
    '''EXPECTED_GREENHOUSE_INDUSTRY_BOARDS: tuple[str, ...] = ()\nEXPECTED_LEVER_INDUSTRY_SITES = (\n    "theathletic",\n''',
    '''EXPECTED_GREENHOUSE_INDUSTRY_BOARDS = ("aclu",)\nEXPECTED_LEVER_INDUSTRY_SITES = (\n    "avalerehealth",\n    "wattpad",\n    "thedispatch",\n    "kiddom",\n    "stradaeducation",\n    "theathletic",\n''',
)

replace_once(
    registry_tests,
    '''    stand_together = find_source("standtogether", "lever")\n\n    assert duolingo is not None\n''',
    '''    stand_together = find_source("standtogether", "lever")\n    aclu = find_source("aclu", "greenhouse")\n    avalere = find_source("avalerehealth", "lever")\n    wattpad = find_source("wattpad", "lever")\n    dispatch = find_source("thedispatch", "lever")\n    strada = find_source("stradaeducation", "lever")\n\n    assert duolingo is not None\n''',
)
replace_once(
    registry_tests,
    '''    assert stand_together.early_career_relevance == "strong"\n\n\ndef test_registry_lookup_and_company_name_fallbacks_are_stable() -> None:\n''',
    '''    assert stand_together.early_career_relevance == "strong"\n\n    assert aclu is not None\n    assert {"legal_services", "public_interest"}.issubset(aclu.industries)\n    assert aclu.source_pool == "industry_only"\n\n    assert avalere is not None\n    assert {"healthcare", "public_policy"}.issubset(avalere.industries)\n    assert "compliance" in avalere.role_families\n\n    assert wattpad is not None\n    assert {"media", "corporate_legal"}.issubset(wattpad.industries)\n    assert wattpad.early_career_relevance == "strong"\n\n    assert dispatch is not None\n    assert {"media", "legal_services"}.issubset(dispatch.industries)\n    assert dispatch.early_career_relevance == "strong"\n\n    assert strada is not None\n    assert {"education", "public_interest"}.issubset(strada.industries)\n    assert strada.early_career_relevance == "strong"\n\n\ndef test_registry_lookup_and_company_name_fallbacks_are_stable() -> None:\n''',
)

replace_once(
    routing_tests,
    '''    assert {"theathletic", "feldinc", "standtogether"}.isdisjoint(plan.lever_identifiers)\n''',
    '''    assert {\n        "avalerehealth",\n        "wattpad",\n        "thedispatch",\n        "kiddom",\n        "stradaeducation",\n        "theathletic",\n        "feldinc",\n        "standtogether",\n    }.isdisjoint(plan.lever_identifiers)\n    assert "aclu" not in plan.greenhouse_identifiers\n''',
)
replace_once(
    routing_tests,
    '''    assert {"theathletic", "feldinc", "standtogether"}.isdisjoint(selected)\n''',
    '''    assert {\n        "aclu",\n        "avalerehealth",\n        "wattpad",\n        "thedispatch",\n        "kiddom",\n        "stradaeducation",\n        "theathletic",\n        "feldinc",\n        "standtogether",\n    }.isdisjoint(selected)\n''',
)
replace_once(
    routing_tests,
    '''    assert "standtogether" in plan.lever_identifiers\n    assert plan.industry_only_sources_activated == 1\n    assert "Activated 1 matching industry-only Lever board" in plan.lever_note\n''',
    '''    assert {"standtogether", "kiddom", "stradaeducation"}.issubset(plan.lever_identifiers)\n    assert plan.industry_only_sources_activated == 3\n    assert "Activated 3 matching industry-only Lever boards" in plan.lever_note\n''',
)
replace_once(
    routing_tests,
    '''def test_nonprofit_search_activates_only_stand_together() -> None:\n''',
    '''def test_nonprofit_search_activates_mission_driven_sources() -> None:\n''',
)
replace_once(
    routing_tests,
    '''    assert plan.direct_industry_matches == 1\n    assert "standtogether" in plan.lever_identifiers\n    assert "theathletic" not in plan.lever_identifiers\n    assert "feldinc" not in plan.lever_identifiers\n    assert plan.industry_only_sources_activated == 1\n''',
    '''    assert plan.direct_industry_matches == 2\n    assert {"standtogether", "stradaeducation"}.issubset(plan.lever_identifiers)\n    assert "theathletic" not in plan.lever_identifiers\n    assert "feldinc" not in plan.lever_identifiers\n    assert plan.industry_only_sources_activated == 2\n''',
)

routing_tests.write_text(
    routing_tests.read_text()
    + '''\n\ndef test_legal_services_search_activates_public_interest_and_media_legal_sources() -> None:\n    plan = _plan(\n        industry="legal_services",\n        job_function="legal",\n        level="intern",\n        location="Philadelphia",\n    )\n\n    assert "aclu" in plan.greenhouse_identifiers\n    assert "thedispatch" in plan.lever_identifiers\n    assert plan.industry_only_sources_activated == 2\n\n\ndef test_healthcare_compliance_search_activates_avalere_health() -> None:\n    plan = _plan(\n        industry="healthcare",\n        job_function="compliance",\n        level="entry",\n    )\n\n    assert "avalerehealth" in plan.lever_identifiers\n    assert "wattpad" not in plan.lever_identifiers\n\n\ndef test_media_policy_search_activates_media_and_internship_sources() -> None:\n    plan = _plan(\n        industry="media",\n        job_function="policy",\n        level="intern",\n    )\n\n    assert {"wattpad", "thedispatch"}.issubset(plan.lever_identifiers)\n    assert "avalerehealth" not in plan.lever_identifiers\n'''
)

(ROOT / "backend/tests/test_legal_search_intent.py").write_text(
    '''from app.job_search import _score_job, parse_job_search_intent\n\n\ndef test_legal_internship_intent_is_separated_from_location_and_level() -> None:\n    intent = parse_job_search_intent(\n        query="legal internship",\n        location="Philadelphia",\n    )\n\n    assert intent.job_function == "legal"\n    assert intent.industry == "legal_services"\n    assert intent.level == "intern"\n    assert intent.location == "Philadelphia"\n\n\ndef test_cross_industry_legal_examples_parse_independent_dimensions() -> None:\n    sports = parse_job_search_intent("sports legal operations internship")\n    healthcare = parse_job_search_intent("healthcare compliance analyst entry level")\n    public_interest = parse_job_search_intent("public interest policy internship")\n    finance = parse_job_search_intent("financial services regulatory analyst")\n\n    assert (sports.job_function, sports.industry, sports.level) == (\n        "legal_operations",\n        "sports",\n        "intern",\n    )\n    assert (healthcare.job_function, healthcare.industry, healthcare.level) == (\n        "compliance",\n        "healthcare",\n        "entry",\n    )\n    assert (public_interest.job_function, public_interest.industry, public_interest.level) == (\n        "policy",\n        "public_interest",\n        "intern",\n    )\n    assert (finance.job_function, finance.industry) == (\n        "compliance",\n        "financial_services",\n    )\n\n\ndef test_legal_role_scoring_rejects_unrelated_internships() -> None:\n    assert _score_job(\n        "Legal Intern",\n        "Support legal research, contracts, and policy projects.",\n        "legal internship",\n        level="intern",\n        company="Example Legal Organization",\n    ) > 0\n    assert _score_job(\n        "Software Engineering Intern",\n        "Build backend services for the legal team.",\n        "legal internship",\n        level="intern",\n        company="Example Technology Company",\n    ) == 0\n'''
)

(ROOT / "docs/milestone-7-source-expansion-tranche-2.md").write_text(
    '''# Milestone 7 — Broader Source Coverage, Tranche 2\n\nThis tranche uses the secondary industry-only source pool to expand healthcare, education, media, legal/public-interest, policy, and early-career coverage without increasing broad-search provider fan-out.\n\n## Added verified public ATS boards\n\n- **ACLU** (`greenhouse:aclu`) — legal services, public interest, government, policy, advocacy, and nonprofit roles\n- **Avalere Health** (`lever:avalerehealth`) — healthcare, life sciences, policy, compliance, advisory, and operations roles\n- **WEBTOON / Wattpad** (`lever:wattpad`) — media, entertainment, content policy, legal-business, and internship roles\n- **The Dispatch** (`lever:thedispatch`) — journalism, policy-adjacent media, legal-current-events work, and recurring internships\n- **Kiddom** (`lever:kiddom`) — education technology, curriculum, product, and operations roles\n- **Strada Education Foundation** (`lever:stradaeducation`) — education, workforce policy, nonprofit, internship, and co-op pathways\n\nAll six sources are classified as `industry_only`. They stay inactive for broad searches and are activated only when an exact registered industry is detected.\n\n## Taxonomy expansion\n\nJob functions now include `legal`, `compliance`, `policy`, `legal_operations`, and `contracts`. Industries now include `legal_services`, `government`, `public_interest`, `corporate_legal`, and `public_policy`. This supports searches such as:\n\n- `legal internship Philadelphia`\n- `sports legal operations internship`\n- `healthcare compliance analyst entry level`\n- `public interest policy internship`\n- `financial services regulatory analyst`\n\n## Deliberate boundary\n\nThis tranche improves intent parsing, routing, and source coverage. It does not yet classify JD, bar-admission, law-school, or undergraduate credential requirements. Credential-aware legal filtering remains a separate later phase.\n'''
)

print("Applied Milestone 7 source expansion tranche 2.")
