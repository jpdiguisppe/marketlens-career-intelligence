from __future__ import annotations

from app.occupation_catalog_runtime import (
    interpret_occupation_query,
    title_matches_occupation,
)


def test_single_word_food_server_does_not_admit_server_engineering() -> None:
    interpretation = interpret_occupation_query("server")
    assert interpretation.status == "recognized"
    assert title_matches_occupation("Restaurant Server", interpretation)
    assert not title_matches_occupation("Server Infrastructure Engineer", interpretation)


def test_server_infrastructure_query_is_interpreted_as_technology() -> None:
    interpretation = interpret_occupation_query("server infrastructure engineer")
    assert interpretation.status == "recognized"
    assert interpretation.concept_key is None
    assert interpretation.search_family == "technology"
    assert title_matches_occupation("Senior Server Infrastructure Engineer", interpretation)
    assert not title_matches_occupation("Restaurant Server", interpretation)


def test_school_principal_does_not_admit_principal_engineer() -> None:
    interpretation = interpret_occupation_query("school principal")
    assert interpretation.status == "recognized"
    assert interpretation.concept_key == "education_administrator"
    assert title_matches_occupation("High School Principal", interpretation)
    assert not title_matches_occupation("Principal Software Engineer", interpretation)


def test_principal_software_engineer_uses_complete_technology_context() -> None:
    interpretation = interpret_occupation_query("principal software engineer")
    assert interpretation.status == "recognized"
    assert interpretation.concept_key is None
    assert interpretation.search_family == "software"
    assert title_matches_occupation("Principal Software Engineer", interpretation)
    assert not title_matches_occupation("High School Principal", interpretation)


def test_software_architect_is_not_a_building_architect() -> None:
    interpretation = interpret_occupation_query("software architect")
    assert interpretation.status == "recognized"
    assert interpretation.concept_key is None
    assert interpretation.search_family == "software"
    assert title_matches_occupation("Software Architect", interpretation)
    assert not title_matches_occupation("Residential Architect", interpretation)
