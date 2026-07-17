"""Intent-specific patches for MarketLens job search.

This module keeps the main job_search provider code stable while tightening the
product behavior we learned from UI testing:

- SWE searches should stay narrow.
- Computer Science/technology searches can be broader, but not clerical/admin.
- Data Analyst searches need a real data/analytics signal, not any analyst role.
- Internship searches should try internship-specific source queries.
"""

from __future__ import annotations

from typing import Any


EXTRA_NON_US_LOCATION_TERMS = {
    "argentina",
    "colombia",
    "czech republic",
    "italy",
    "netherlands",
    "pakistan",
    "philippines",
    "poland",
    "polska",
    "turkey",
    "ukraine",
    "vietnam",
}

EXTRA_INTERN_TERMS = {
    "summer analyst",
    "summer intern",
    "summer internship",
    "student intern",
    "university intern",
    "internship program",
    "intern program",
    "apprentice",
    "apprenticeship",
}

CLERICAL_ADMIN_TITLE_TERMS = {
    "administrative assistant",
    "admin assistant",
    "customer service representative",
    "data entry",
    "data entry clerk",
    "data entry specialist",
    "office assistant",
    "office clerk",
    "records clerk",
    "receptionist",
    "virtual assistant",
}

NON_DATA_ANALYST_TITLE_TERMS = {
    "compliance analyst",
    "credit analyst",
    "derivative sales analyst",
    "finance analyst",
    "financial analyst",
    "marketing analyst",
    "operations analyst",
    "policy analyst",
    "pricing analyst",
    "risk analyst",
    "sales analyst",
}

TECHNOLOGY_ADJACENT_TITLE_TERMS = {
    "technical analyst",
    "systems analyst",
    "it analyst",
    "information technology analyst",
}


def apply_job_search_intent_patch(job_search: Any) -> None:
    """Patch app.job_search helpers with stricter intent behavior.

    The project currently keeps provider fetching, normalization, and ranking in
    app.job_search. These overrides are intentionally small and idempotent so we
    can harden behavior without rewriting the whole provider layer mid-milestone.
    """

    if getattr(job_search, "_INTENT_PATCH_APPLIED", False):
        return

    original_title_matches_role_family = job_search._title_matches_role_family

    job_search.NON_US_LOCATION_TERMS.update(EXTRA_NON_US_LOCATION_TERMS)
    job_search.INTERN_TERMS.update(EXTRA_INTERN_TERMS)

    def _is_clerical_admin_title(title: str) -> bool:
        return job_search._contains_any(title.lower(), CLERICAL_ADMIN_TITLE_TERMS)

    def _is_non_data_analyst_title(title: str) -> bool:
        return job_search._contains_any(title.lower(), NON_DATA_ANALYST_TITLE_TERMS)

    def _is_blocked_for_data_or_technology(title: str, family: str | None) -> bool:
        if family not in {"data", "technology"}:
            return False
        return _is_clerical_admin_title(title) or _is_non_data_analyst_title(title)

    def _title_matches_role_family(title: str, family: str) -> bool:
        if _is_blocked_for_data_or_technology(title, family):
            return False
        if family == "technology" and job_search._contains_any(title.lower(), TECHNOLOGY_ADJACENT_TITLE_TERMS):
            return True
        return original_title_matches_role_family(title, family)

    def _is_generic_early_career_title(title: str) -> bool:
        return job_search._contains_any(
            title.lower(),
            {
                "intern",
                "internship",
                "summer analyst",
                "analyst intern",
                "rotational program",
                "graduate program",
                "apprentice",
                "apprenticeship",
            },
        )

    def _matches_requested_role(title: str, description: str, query: str, level: str | None = None) -> bool:
        family = job_search._query_role_family(query)
        if family is None:
            return True

        if _is_blocked_for_data_or_technology(title, family):
            return False

        if _title_matches_role_family(title, family):
            return True

        # Data searches should require a real data/analytics title or a generic
        # early-career title whose body strongly names data/analytics work. Do
        # not let generic "analyst" admit compliance/sales/finance analysts.
        if family == "data":
            return bool(
                (level in {"intern", "entry"} or job_search._infer_level_from_query(query) in {"intern", "entry"})
                and _is_generic_early_career_title(title)
                and job_search._text_matches_role_family(description, family)
            )

        # Computer Science / technology is broader than SWE, but it still should
        # mean technical roles. Avoid the old core-term fallback that allowed
        # clerical "Data Entry" results just because the title contained "data".
        if family == "technology":
            return bool(
                (level in {"intern", "entry"} or job_search._infer_level_from_query(query) in {"intern", "entry"})
                and _is_generic_early_career_title(title)
                and job_search._text_matches_role_family(description, family)
            )

        if family != "software" and job_search._title_contains_core_query_term(title, query):
            return True
        if family == "software" and not job_search._is_strict_software_query(query) and job_search._title_contains_core_query_term(title, query):
            return True

        return bool(
            (level in {"intern", "entry"} or job_search._infer_level_from_query(query) in {"intern", "entry"})
            and _is_generic_early_career_title(title)
            and job_search._text_matches_role_family(description, family)
        )

    def _remotive_search_terms(query: str, level: str) -> list[str | None]:
        family = job_search._query_role_family(query)
        core_terms = sorted(job_search._core_query_terms(query))
        normalized = query.lower().strip()

        terms: list[str | None] = []
        if normalized:
            terms.append(normalized)

        if family == "technology":
            if level == "intern":
                terms.extend(["software intern", "data intern", "analytics intern", "cybersecurity intern", "intern"])
            else:
                terms.extend(["software", "data", "analytics", "cybersecurity", "developer"])
        elif family == "software":
            if level == "intern":
                terms.extend([
                    "software intern",
                    "software internship",
                    "software engineer intern",
                    "software engineering internship",
                    "developer intern",
                    "engineering intern",
                    "intern",
                ])
            elif "backend" in normalized:
                terms.extend(["backend", "backend developer"])
            elif "frontend" in normalized or "front end" in normalized:
                terms.extend(["frontend", "frontend developer"])
            elif "full stack" in normalized or "full-stack" in normalized:
                terms.extend(["full stack", "full stack developer"])
            else:
                terms.extend(["software", "developer"])
        elif family == "finance":
            terms.extend(["finance", "accounting", "financial analyst", "audit", "tax"])
            if level == "intern":
                terms.extend(["finance intern", "finance internship", "accounting intern", "accounting internship", "summer analyst", "intern"])
            elif level == "entry":
                terms.extend(["junior financial analyst", "entry level finance", "junior accountant"])
        elif family == "data":
            terms.extend(["data analyst", "analytics", "business intelligence"])
            if level == "intern":
                terms.extend(["data analyst intern", "data analytics intern", "analytics intern", "data science intern", "intern"])
            elif level == "entry":
                terms.extend(["junior data analyst", "entry level data analyst", "analytics associate"])
        elif family == "cybersecurity":
            terms.extend(["cybersecurity", "security analyst", "information security"])
            if level == "intern":
                terms.extend(["cybersecurity intern", "security intern", "information security intern"])
        elif family:
            terms.extend(core_terms)
            if level == "intern":
                terms.extend([f"{term} intern" for term in core_terms if len(term) > 2])
        elif level == "intern":
            terms.extend(["intern", "internship"])
        elif level == "entry":
            terms.extend(["junior", "entry level"])

        if family in {"software", "finance", "technology"}:
            terms.append(None)

        seen: set[str | None] = set()
        unique_terms: list[str | None] = []
        for term in terms:
            normalized_term = term.strip().lower() if isinstance(term, str) else None
            if normalized_term in seen:
                continue
            seen.add(normalized_term)
            unique_terms.append(normalized_term)
            if len(unique_terms) >= 10:
                break
        return unique_terms

    def _warnings_for_no_results(query: str, location: str | None, level: str, role_family: str | None) -> list[str]:
        query_lower = query.lower()
        if role_family == "finance" and any(term in query_lower for term in ("account", "audit", "tax")):
            role_text = "finance/accounting"
        elif role_family == "technology":
            role_text = "computer science/technology"
        elif role_family:
            role_text = role_family
        else:
            role_text = "requested"

        if level == "intern":
            noun = f"{role_text} internship jobs"
        elif level == "entry":
            noun = f"entry-level {role_text} jobs"
        elif level == "mid":
            noun = f"mid-level {role_text} jobs"
        elif level == "senior":
            noun = f"senior {role_text} jobs"
        else:
            noun = f"{role_text} jobs"

        warning = (
            f"No matching {noun} were found in MarketLens' configured API-friendly public sources. "
            "This does not mean no such jobs exist; it means the current public sources did not return a matching posting."
        )

        if role_family == "finance" and level == "intern":
            warning += " Finance/accounting internships are especially likely to live on campus boards, Workday/company career pages, LinkedIn, or Indeed."
        elif level == "intern":
            warning += " Internship coverage is especially dependent on what the configured public APIs currently expose."

        if location and location.lower() != "remote" and job_search._is_us_city_or_state_request(location):
            warning += " U.S.-remote roles are included for city searches, but no matching results were found."

        return [warning]

    job_search._title_matches_role_family = _title_matches_role_family
    job_search._matches_requested_role = _matches_requested_role
    job_search._remotive_search_terms = _remotive_search_terms
    job_search._warnings_for_no_results = _warnings_for_no_results
    job_search._INTENT_PATCH_APPLIED = True
