from __future__ import annotations

from app.occupation_catalog import interpret_occupation_query, title_matches_occupation


def test_single_word_food_server_does_not_admit_server_engineering() -> None:
    interpretation = interpret_occupation_query("server")
    assert interpretation.status == "recognized"
    assert title_matches_occupation("Restaurant Server", interpretation)
    assert not title_matches_occupation("Server Infrastructure Engineer", interpretation)


def test_school_principal_does_not_admit_principal_engineer() -> None:
    interpretation = interpret_occupation_query("school principal")
    assert interpretation.status == "recognized"
    assert interpretation.concept_key == "education_administrator"
    assert title_matches_occupation("High School Principal", interpretation)
    assert not title_matches_occupation("Principal Software Engineer", interpretation)
