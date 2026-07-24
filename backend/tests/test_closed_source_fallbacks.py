from urllib.parse import parse_qs, unquote_plus, urlparse

from app.job_search import _external_search_links, _external_search_query


def _labels(query: str, level: str) -> set[str]:
    return {link.label for link in _external_search_links(query, "Philadelphia", level)}


def test_external_links_cover_closed_sources_without_claiming_they_were_searched() -> None:
    links = _external_search_links("software engineer", "Philadelphia", "entry")
    labels = {link.label for link in links}

    assert labels == {
        "Google Jobs search",
        "Indeed search",
        "LinkedIn Jobs search",
        "Workday / company career-site search",
        "Handshake search",
    }
    assert all(link.url.startswith("https://") for link in links)
    assert all("MarketLens" in link.note or "Login" in link.note or "requires" in link.note for link in links)


def test_handshake_is_available_for_intern_and_entry_searches_only() -> None:
    assert "Handshake search" in _labels("software engineer", "intern")
    assert "Handshake search" in _labels("software engineer", "entry")
    assert "Handshake search" not in _labels("software engineer", "mid")
    assert "Handshake search" not in _labels("software engineer", "senior")


def test_workday_fallback_uses_google_discovery_instead_of_scraping_workday() -> None:
    workday_link = next(
        link
        for link in _external_search_links("healthcare compliance analyst", "Philadelphia", "entry")
        if link.label == "Workday / company career-site search"
    )
    parsed = urlparse(workday_link.url)
    query = unquote_plus(parse_qs(parsed.query)["q"][0])

    assert parsed.scheme == "https"
    assert parsed.netloc == "www.google.com"
    assert "site:myworkdayjobs.com" in query
    assert "site:myworkdaysite.com" in query
    assert "healthcare compliance analyst" in query
    assert "Philadelphia" in query


def test_external_query_adds_level_and_location_once() -> None:
    assert _external_search_query("software engineer", "Philadelphia", "entry") == (
        "software engineer entry level Philadelphia"
    )
    assert _external_search_query("entry level software engineer", "Philadelphia", "entry") == (
        "entry level software engineer Philadelphia"
    )
    assert _external_search_query("legal internship", "Remote", "intern") == (
        "legal internship remote"
    )
