from app.job_search import _matches_location


def test_multi_word_city_search_uses_explicit_metro_aliases_not_partial_words() -> None:
    assert _matches_location("New York, NY", "New York") is True
    assert _matches_location("Newark, NJ", "New York") is True
    assert _matches_location("New Orleans, LA", "New York") is False


def test_city_search_expands_to_known_metro_but_not_entire_state() -> None:
    assert _matches_location("San Francisco, CA", "San Francisco") is True
    assert _matches_location("San Jose, CA", "San Francisco") is True
    assert _matches_location("Seattle, WA", "Seattle") is True
    assert _matches_location("Spokane, WA", "Seattle") is False


def test_state_or_region_search_can_still_be_broader_than_city_search() -> None:
    assert _matches_location("Philadelphia, PA", "PA") is True
    assert _matches_location("Pittsburgh, PA", "PA") is True
    assert _matches_location("San Jose, CA", "Bay Area") is True
