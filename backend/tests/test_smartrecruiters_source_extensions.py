from app import job_search
from app.job_search_source_expansion import (
    MAX_SOURCES_PER_SEARCH,
    SMARTRECRUITERS_SOURCES,
    select_smartrecruiters_sources,
)


def test_extended_source_registry_is_unique_and_named() -> None:
    identifiers = [source.identifier for source in SMARTRECRUITERS_SOURCES]
    assert len(identifiers) == len(set(identifiers))
    assert "SyngentaGroup" in identifiers
    assert "Dominos" in identifiers

    organizations = {
        source.identifier: source.organization for source in SMARTRECRUITERS_SOURCES
    }
    assert organizations["SyngentaGroup"] == "Syngenta Group"
    assert organizations["Dominos"] == "Domino's"


def test_agriculture_search_selects_verified_public_agriculture_board() -> None:
    selected = select_smartrecruiters_sources(
        job_search,
        "agronomist",
        "Philadelphia",
        "entry",
    )
    selected_ids = {source.identifier for source in selected}
    assert "SyngentaGroup" in selected_ids
    assert len(selected_ids) <= MAX_SOURCES_PER_SEARCH


def test_delivery_search_selects_verified_public_service_board() -> None:
    selected = select_smartrecruiters_sources(
        job_search,
        "delivery driver",
        "Philadelphia",
        "entry",
    )
    selected_ids = {source.identifier for source in selected}
    assert "Dominos" in selected_ids
    assert len(selected_ids) <= MAX_SOURCES_PER_SEARCH


def test_new_sources_do_not_activate_for_unrelated_specific_occupation() -> None:
    selected = select_smartrecruiters_sources(
        job_search,
        "speech language pathologist",
        "Philadelphia",
        "entry",
    )
    selected_ids = {source.identifier for source in selected}
    assert "SyngentaGroup" not in selected_ids
    assert "Dominos" not in selected_ids
