"""Metro-aware location semantics and user-facing search guidance.

Explicit city searches remain strict: they include recognized places in that
city's metro area, but never silently include remote-only postings. State and
region searches continue to match their normal abbreviations.
"""

from __future__ import annotations

from typing import Any


METRO_LOCATION_ALIASES: dict[str, set[str]] = {
    "philadelphia": {
        "philadelphia",
        "philly",
        "king of prussia",
        "conshohocken",
        "malvern",
        "wayne",
        "radnor",
        "exton",
        "west chester",
        "newtown square",
        "fort washington",
        "horsham",
        "blue bell",
        "plymouth meeting",
        "audubon",
        "camden",
        "cherry hill",
        "mount laurel",
        "wilmington",
    },
    "philly": {
        "philadelphia",
        "philly",
        "king of prussia",
        "conshohocken",
        "malvern",
        "wayne",
        "radnor",
        "exton",
        "west chester",
        "newtown square",
        "fort washington",
        "horsham",
        "blue bell",
        "plymouth meeting",
        "audubon",
        "camden",
        "cherry hill",
        "mount laurel",
        "wilmington",
    },
    "new york": {
        "new york",
        "new york city",
        "nyc",
        "manhattan",
        "brooklyn",
        "queens",
        "bronx",
        "staten island",
        "jersey city",
        "hoboken",
        "newark",
        "white plains",
        "long island city",
    },
    "new york city": {
        "new york",
        "new york city",
        "nyc",
        "manhattan",
        "brooklyn",
        "queens",
        "bronx",
        "staten island",
        "jersey city",
        "hoboken",
        "newark",
        "white plains",
        "long island city",
    },
    "nyc": {
        "new york",
        "new york city",
        "nyc",
        "manhattan",
        "brooklyn",
        "queens",
        "bronx",
        "staten island",
        "jersey city",
        "hoboken",
        "newark",
        "white plains",
        "long island city",
    },
    "washington dc": {
        "washington dc",
        "washington, dc",
        "district of columbia",
        "dc",
        "arlington",
        "alexandria",
        "bethesda",
        "silver spring",
        "mclean",
        "tysons",
        "reston",
    },
    "washington, dc": {
        "washington dc",
        "washington, dc",
        "district of columbia",
        "dc",
        "arlington",
        "alexandria",
        "bethesda",
        "silver spring",
        "mclean",
        "tysons",
        "reston",
    },
    "dc": {
        "washington dc",
        "washington, dc",
        "district of columbia",
        "dc",
        "arlington",
        "alexandria",
        "bethesda",
        "silver spring",
        "mclean",
        "tysons",
        "reston",
    },
    "san francisco": {
        "san francisco",
        "sf",
        "oakland",
        "berkeley",
        "daly city",
        "san mateo",
        "redwood city",
        "palo alto",
        "mountain view",
        "sunnyvale",
        "santa clara",
        "san jose",
    },
    "sf": {
        "san francisco",
        "sf",
        "oakland",
        "berkeley",
        "daly city",
        "san mateo",
        "redwood city",
        "palo alto",
        "mountain view",
        "sunnyvale",
        "santa clara",
        "san jose",
    },
    "boston": {
        "boston",
        "cambridge",
        "somerville",
        "brookline",
        "quincy",
        "waltham",
        "newton",
    },
    "chicago": {
        "chicago",
        "evanston",
        "oak brook",
        "schaumburg",
        "naperville",
        "rosemont",
    },
    "seattle": {
        "seattle",
        "bellevue",
        "redmond",
        "kirkland",
        "renton",
    },
    "los angeles": {
        "los angeles",
        "la",
        "santa monica",
        "culver city",
        "burbank",
        "glendale",
        "pasadena",
        "long beach",
        "universal city",
    },
}


def apply_job_search_location_patch(job_search: Any) -> None:
    if getattr(job_search, "_LOCATION_PATCH_APPLIED", False):
        return

    for location_name, aliases in METRO_LOCATION_ALIASES.items():
        job_search.LOCATION_ALIASES.setdefault(location_name, set()).update(aliases)

    original_search_suggestions = job_search._search_suggestions

    def _search_suggestions(
        query: str,
        location: str | None,
        level: str,
        role_family: str | None,
    ) -> list[str]:
        suggestions = original_search_suggestions(
            query,
            location,
            level,
            role_family,
        )
        stale_text = (
            "City searches stay city-specific but include U.S.-remote roles; "
            "use a state/region for broader local coverage."
        )
        corrected_text = (
            "City searches include recognized metro-area locations but exclude "
            "remote-only roles. Search Remote or a broader state/region deliberately "
            "to expand coverage."
        )
        return [
            corrected_text if suggestion == stale_text else suggestion
            for suggestion in suggestions
        ]

    job_search._search_suggestions = _search_suggestions
    job_search._LOCATION_PATCH_APPLIED = True
