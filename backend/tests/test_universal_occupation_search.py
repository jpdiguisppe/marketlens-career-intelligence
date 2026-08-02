from __future__ import annotations

from app import job_search
from app import job_search_source_expansion as source_expansion
from app.job_search_universal_occupation import _occupation_external_links
from app.occupation_catalog import AMBIGUOUS_ACRONYMS, OCCUPATIONS, SOC_MAJOR_GROUPS
from app.occupation_catalog_runtime import (
    interpret_occupation_query,
    registry_summary,
    title_matches_occupation,
)


def test_registry_covers_every_soc_major_group_and_large_cross_sector_surface() -> None:
    summary = registry_summary()
    assert summary["major_groups"] == 23
    assert set(SOC_MAJOR_GROUPS) == {concept.soc_major_group for concept in OCCUPATIONS}
    assert summary["occupations"] >= 200
    assert summary["accepted_titles"] >= 450
    assert summary["ambiguous_acronyms"] >= 30


def test_every_catalog_occupation_and_alias_is_deterministically_recognized() -> None:
    for concept in OCCUPATIONS:
        canonical = interpret_occupation_query(concept.canonical_title)
        assert canonical.status == "recognized", concept.canonical_title
        assert canonical.concept_key == concept.key
        assert canonical.soc_major_group == concept.soc_major_group

        for alias in concept.aliases:
            interpreted = interpret_occupation_query(alias)
            assert interpreted.status == "recognized", alias
            assert interpreted.concept_key == concept.key, alias


def test_friend_driven_cross_sector_acceptance_set() -> None:
    cases = {
        "staff accountant": "accountant",
        "financial analyst": "financial_analyst",
        "police officer": "police_officer",
        "registered nurse": "registered_nurse",
        "business systems analyst": "business_analyst",
        "journeyman electrician": "electrician",
        "mechanical engineer": "mechanical_engineer",
        "high school teacher": "secondary_school_teacher",
        "associate attorney": "attorney",
        "market research analyst": "market_research_analyst",
        "sports data analyst": "sports_analyst",
        "research economist": "economist",
    }
    for query, expected_key in cases.items():
        interpretation = interpret_occupation_query(query)
        assert interpretation.status == "recognized"
        assert interpretation.concept_key == expected_key


def test_all_ambiguous_acronyms_request_clarification() -> None:
    for acronym, meanings in AMBIGUOUS_ACRONYMS.items():
        interpretation = interpret_occupation_query(f"{acronym.upper()} jobs")
        assert interpretation.status == "ambiguous"
        assert interpretation.suggestions == meanings
        assert interpretation.occupation_phrase is None


def test_safe_acronyms_still_resolve() -> None:
    assert interpret_occupation_query("RN").concept_key == "registered_nurse"
    assert interpret_occupation_query("EMT").concept_key == "emergency_medical_technician"
    assert interpret_occupation_query("CNA").concept_key == "nursing_assistant"
    assert interpret_occupation_query("DBA").concept_key == "database_administrator"


def test_sae_full_title_variants_share_one_concept() -> None:
    variants = (
        "System Application Engineer",
        "Systems Application Engineer",
        "Systems Applications Engineer",
        "Application Systems Engineer",
    )
    for variant in variants:
        interpretation = interpret_occupation_query(variant)
        assert interpretation.status == "recognized"
        assert interpretation.concept_key == "systems_application_engineer"
        assert interpretation.search_family == "software"


def test_high_confidence_misspellings_resolve_without_broad_guessing() -> None:
    assert interpret_occupation_query("acountant").concept_key == "accountant"
    assert interpret_occupation_query("electrial engineer").concept_key == "electrical_engineer"
    assert interpret_occupation_query("marketng manager").concept_key == "marketing_manager"
    assert interpret_occupation_query("xyzq").status == "unrecognized"


def test_specific_occupation_matching_rejects_neighboring_titles() -> None:
    systems_application = interpret_occupation_query("system application engineer")
    assert title_matches_occupation("Senior Systems Applications Engineer", systems_application)
    assert title_matches_occupation("Application Systems Engineer I", systems_application)
    assert not title_matches_occupation("Sales Engineer", systems_application)
    assert not title_matches_occupation("Systems Administrator", systems_application)

    accountant = interpret_occupation_query("accountant")
    assert title_matches_occupation("Senior Staff Accountant", accountant)
    assert not title_matches_occupation("Account Executive", accountant)

    police = interpret_occupation_query("police officer")
    assert title_matches_occupation("Police Officer Recruit", police)
    assert not title_matches_occupation("Security Guard", police)


def test_unlisted_descriptive_occupation_uses_safe_generic_recognition() -> None:
    interpretation = interpret_occupation_query("aerospace propulsion engineer")
    assert interpretation.status == "recognized"
    assert interpretation.concept_key is None
    assert interpretation.search_family == "technology"
    assert title_matches_occupation("Senior Aerospace Propulsion Engineer", interpretation)
    assert not title_matches_occupation("Aerospace Recruiter", interpretation)


def test_live_search_stack_uses_cross_sector_family_hints() -> None:
    expected = {
        "systems application engineer": "software",
        "civil engineer": "technology",
        "registered nurse": "healthcare",
        "accountant": "finance",
        "police officer": "operations",
        "high school teacher": "operations",
        "attorney": "legal",
        "sports analyst": "data",
    }
    for query, family in expected.items():
        intent = job_search.parse_job_search_intent(query=query, level="any")
        assert intent.job_function == family


def test_live_scoring_is_strict_for_specific_occupations() -> None:
    assert job_search._score_job(
        "Systems Applications Engineer",
        "Build and support enterprise applications.",
        "system application engineer",
        "any",
    ) > 0
    assert job_search._score_job(
        "Sales Engineer",
        "Support customer sales.",
        "system application engineer",
        "any",
    ) == 0
    assert job_search._score_job(
        "Police Officer",
        "Patrol and public safety.",
        "police officer",
        "any",
    ) > 0
    assert job_search._score_job(
        "Security Guard",
        "Monitor a private facility.",
        "police officer",
        "any",
    ) == 0


def test_smartrecruiters_search_terms_use_canonical_and_alternate_titles() -> None:
    terms = source_expansion._search_terms("system application engineer")
    assert terms[0] == "systems application engineer"
    assert len(terms) == source_expansion.MAX_SEARCH_PASSES_PER_SOURCE
    assert any("application" in term and "engineer" in term for term in terms)


def test_cross_sector_source_terms_are_enriched() -> None:
    sources = {source.identifier: source for source in source_expansion.SMARTRECRUITERS_SOURCES}
    assert "police officer" in sources["CityofPhiladelphia"].query_terms
    assert "high school teacher" in sources["KIPP"].query_terms
    assert "systems application engineer" in sources["AECOM2"].query_terms
    assert "technology" in sources["AECOM2"].role_families
    assert "registered nurse" in sources["HealthFederationOfPhiladelphia"].query_terms


def test_ambiguous_sae_short_circuits_without_provider_requests() -> None:
    result = job_search.search_external_jobs("SAE", location="Philadelphia, PA", level="entry")
    assert result.results == []
    assert result.providers_searched == []
    assert result.source_coverage == []
    assert any("ambiguous" in warning.lower() for warning in result.warnings)
    assert any("systems application engineer" in item.lower() for item in result.search_suggestions)


def test_unknown_short_acronym_short_circuits_instead_of_guessing() -> None:
    result = job_search.search_external_jobs("XYZ", level="any")
    assert result.results == []
    assert result.providers_searched == []
    assert any("could not safely identify" in warning.lower() for warning in result.warnings)


def test_sector_specific_external_links_expand_honest_coverage() -> None:
    electrician = interpret_occupation_query("electrician")
    electrician_links = _occupation_external_links(
        job_search,
        electrician,
        "Philadelphia, PA",
        "entry",
    )
    assert any("apprenticeship.gov" in link.url for link in electrician_links)
    assert any("governmentjobs.com" in link.url for link in electrician_links)

    police = interpret_occupation_query("police officer")
    police_links = _occupation_external_links(
        job_search,
        police,
        "Philadelphia, PA",
        "entry",
    )
    assert any("usajobs.gov" in link.url for link in police_links)
    assert any("governmentjobs.com" in link.url for link in police_links)
