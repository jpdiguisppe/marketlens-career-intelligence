from app.job_search import _matches_location, _search_suggestions


def test_philadelphia_search_includes_recognized_metro_locations() -> None:
    for job_location in (
        "Philadelphia, PA",
        "King of Prussia, PA",
        "West Chester, PA",
        "Malvern, PA",
        "Conshohocken, PA",
        "Camden, NJ",
        "Cherry Hill, NJ",
        "Mount Laurel, NJ",
        "Wilmington, DE",
    ):
        assert _matches_location(job_location, "Philadelphia"), job_location


def test_philadelphia_search_stays_inside_the_metro_and_excludes_remote() -> None:
    for job_location in (
        "Pittsburgh, PA",
        "New York, NY",
        "Remote - United States",
        "Remote (Worldwide)",
        "Remote (California, United States)",
    ):
        assert not _matches_location(job_location, "Philadelphia"), job_location


def test_other_recognized_metros_expand_without_becoming_statewide() -> None:
    assert _matches_location("Jersey City, NJ", "New York")
    assert _matches_location("San Jose, CA", "San Francisco")
    assert _matches_location("Cambridge, MA", "Boston")
    assert _matches_location("Bellevue, WA", "Seattle")
    assert not _matches_location("Albany, NY", "New York")
    assert not _matches_location("Sacramento, CA", "San Francisco")


def test_no_result_guidance_describes_actual_location_behavior() -> None:
    suggestions = _search_suggestions(
        "electrical engineer",
        "Philadelphia",
        "entry",
        None,
    )
    combined = " ".join(suggestions).lower()
    assert "metro-area" in combined
    assert "exclude remote-only" in combined
    assert "include u.s.-remote" not in combined
