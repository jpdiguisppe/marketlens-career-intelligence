from app.job_search import _matches_location


def test_multi_word_city_search_does_not_match_on_single_words() -> None:
    assert _matches_location("New York, NY", "New York") is True
    assert _matches_location("Newark, NJ", "New York") is False
    assert _matches_location("New Orleans, LA", "New York") is False


def test_city_search_does_not_expand_to_entire_state_unless_requested() -> None:
    assert _matches_location("San Francisco, CA", "San Francisco") is True
    assert _matches_location("San Jose, CA", "San Francisco") is False
    assert _matches_location("Seattle, WA", "Seattle") is True
    assert _matches_location("Spokane, WA", "Seattle") is False


def test_state_or_region_search_can_still_be_broader_than_city_search() -> None:
    assert _matches_location("Philadelphia, PA", "PA") is True
    assert _matches_location("Pittsburgh, PA", "PA") is True
    assert _matches_location("San Jose, CA", "Bay Area") is True
