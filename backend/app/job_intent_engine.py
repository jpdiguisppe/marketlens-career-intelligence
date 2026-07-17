"""Reusable job-search intent classification for MarketLens.

The provider layer returns imperfect job postings from several public APIs. This
module owns the product-level matching rules so search behavior does not become
an endless pile of one-off patches.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

RoleFamily = str
JobLevel = str

EXPERIENCE_YEARS_PATTERN = re.compile(r"\b(\d{1,2})\s*\+?\s*(?:years?|yrs?)\b", re.IGNORECASE)

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

INTERN_TITLE_TERMS = {
    "intern",
    "internship",
    "co-op",
    "coop",
    "co op",
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

ENTRY_TEXT_TERMS = {
    "entry level",
    "entry-level",
    "junior",
    "associate",
    "new grad",
    "new graduate",
    "university grad",
    "university graduate",
    "early career",
}

SOFTWARE_TITLE_TERMS = {
    "software engineer",
    "software engineering",
    "software developer",
    "backend engineer",
    "backend developer",
    "back-end engineer",
    "back-end developer",
    "frontend engineer",
    "frontend developer",
    "front-end engineer",
    "front-end developer",
    "full stack engineer",
    "full stack developer",
    "full-stack engineer",
    "full-stack developer",
    "web developer",
    "application developer",
    "app developer",
    "python developer",
    "java developer",
    "javascript developer",
    "typescript developer",
    "react developer",
    "node developer",
    "mobile engineer",
    "mobile developer",
    "ios engineer",
    "ios developer",
    "android engineer",
    "android developer",
    "platform engineer",
    "infrastructure engineer",
    "devops engineer",
    "programmer",
    "developer",
    "forward deployed software engineer",
}

DATA_TITLE_TERMS = {
    "analytics engineer",
    "data analyst",
    "data analytics",
    "data scientist",
    "data science",
    "data engineer",
    "business intelligence",
    "bi analyst",
    "machine learning",
    "ml engineer",
    "research analyst",
    "reporting analyst",
}

CYBERSECURITY_TITLE_TERMS = {
    "cybersecurity",
    "cyber security",
    "security analyst",
    "soc analyst",
    "information security",
    "infosec",
    "security engineer",
    "threat analyst",
    "insider threat",
}

FINANCE_TITLE_TERMS = {
    "finance",
    "financial",
    "fp&a",
    "fpa",
    "accounting",
    "accountant",
    "audit",
    "auditor",
    "tax",
    "treasury",
    "investment",
    "investment banking",
    "banking",
    "private equity",
    "equity research",
    "valuation",
    "wealth",
    "risk analyst",
    "credit analyst",
    "financial analyst",
    "finance analyst",
    "business analyst",
    "quantitative analyst",
    "portfolio analyst",
    "corporate finance",
    "summer analyst",
    "analyst intern",
    "rotational finance",
}

PRODUCT_TITLE_TERMS = {
    "product manager",
    "product analyst",
    "product owner",
    "program manager",
    "project manager",
    "scrum master",
}

MARKETING_TITLE_TERMS = {
    "marketing",
    "growth",
    "content marketing",
    "seo",
    "social media",
    "brand",
    "communications",
    "market specialist",
    "crypto market specialist",
}

OPERATIONS_TITLE_TERMS = {
    "operations",
    "business operations",
    "strategy",
    "supply chain",
    "logistics",
    "procurement",
    "customer success",
    "human resources",
    "hr intern",
}

HEALTHCARE_TITLE_TERMS = {
    "healthcare",
    "health care",
    "clinical",
    "patient",
    "medical",
    "hospital",
    "health analyst",
}

DESIGN_TITLE_TERMS = {
    "designer",
    "product designer",
    "ux",
    "ui designer",
    "visual designer",
    "graphic designer",
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

CLERICAL_ADMIN_QUERY_TERMS = CLERICAL_ADMIN_TITLE_TERMS | {
    "clerical",
    "admin",
    "administrative",
}

NON_DATA_ANALYST_TITLE_TERMS = {
    "compliance analyst",
    "credit analyst",
    "derivative sales analyst",
    "finance analyst",
    "financial analyst",
    "marketing analyst",
    "market specialist",
    "crypto market specialist",
    "operations analyst",
    "policy analyst",
    "pricing analyst",
    "risk analyst",
    "sales analyst",
    "trading specialist",
}

SALES_SUPPORT_TITLE_TERMS = {
    "account executive",
    "business development",
    "customer success",
    "customer support",
    "developer advocate",
    "developer relations",
    "sales",
    "sales engineer",
    "solutions engineer",
    "support engineer",
    "technical support",
}

TECHNOLOGY_ADJACENT_TITLE_TERMS = {
    "technical analyst",
    "systems analyst",
    "it analyst",
    "information technology analyst",
}

ROLE_TITLE_TERMS: dict[RoleFamily, set[str]] = {
    "software": SOFTWARE_TITLE_TERMS,
    "data": DATA_TITLE_TERMS,
    "cybersecurity": CYBERSECURITY_TITLE_TERMS,
    "finance": FINANCE_TITLE_TERMS,
    "product": PRODUCT_TITLE_TERMS,
    "marketing": MARKETING_TITLE_TERMS,
    "operations": OPERATIONS_TITLE_TERMS | CLERICAL_ADMIN_TITLE_TERMS,
    "healthcare": HEALTHCARE_TITLE_TERMS,
    "design": DESIGN_TITLE_TERMS,
}

TECHNOLOGY_FAMILIES = frozenset({"software", "data", "cybersecurity"})
NON_TECHNICAL_FAMILIES = frozenset({"finance", "product", "marketing", "operations", "healthcare", "design"})
ENGINE_HANDLED_FAMILIES = frozenset({
    "technology",
    "software",
    "data",
    "cybersecurity",
    "finance",
    "operations",
})

ROLE_QUERY_TERMS: dict[RoleFamily, set[str]] = {
    "technology": {"computer science", "cs jobs", "tech jobs", "technology", "technical roles"},
    "software": {
        "swe",
        "software",
        "software engineer",
        "software engineering",
        "software developer",
        "backend",
        "frontend",
        "front end",
        "back end",
        "full stack",
        "developer",
        "programmer",
    },
    "finance": {
        "finance",
        "financial",
        "accounting",
        "accountant",
        "audit",
        "tax",
        "fp&a",
        "fpa",
        "investment",
        "banking",
        "equity",
        "valuation",
        "treasury",
        "wealth",
        "portfolio",
        "credit",
    },
    "data": {
        "data analyst",
        "data analytics",
        "analytics engineer",
        "business intelligence",
        "bi",
        "data scientist",
        "data science",
        "data engineer",
        "machine learning",
        "ml",
        "reporting",
        "analytics",
        "data",
    },
    "cybersecurity": {"cybersecurity", "cyber security", "security analyst", "soc", "infosec", "information security"},
    "product": {"product manager", "product management", "product analyst", "project manager", "program manager", "scrum"},
    "marketing": {"marketing", "growth", "seo", "social media", "brand", "communications"},
    "operations": CLERICAL_ADMIN_QUERY_TERMS | {"operations", "strategy", "supply chain", "logistics", "procurement", "human resources", "hr"},
    "healthcare": {"healthcare", "health care", "clinical", "patient", "medical", "hospital"},
    "design": {"design", "designer", "ux", "ui", "visual design", "graphic design"},
}


@dataclass(frozen=True)
class SearchIntent:
    query: str
    level: JobLevel
    role_family: RoleFamily | None
    accepted_families: frozenset[RoleFamily]
    accounting_focus: bool = False
    broad_technology: bool = False


@dataclass(frozen=True)
class JobIntent:
    title: str
    families: frozenset[RoleFamily]
    is_clerical_admin: bool = False
    is_sales_support: bool = False
    is_non_data_analyst: bool = False
    has_internship_title: bool = False
    has_entry_title: bool = False
    is_technology_adjacent: bool = False


def _contains_phrase(value: str, phrase: str) -> bool:
    cleaned_phrase = phrase.strip().lower()
    if not cleaned_phrase:
        return False

    escaped_words = [re.escape(part) for part in re.split(r"[\s,./()\-]+", cleaned_phrase) if part]
    if not escaped_words:
        return False

    separator = r"[\s,./()\-]+"
    pattern = r"(?<![a-z0-9])" + separator.join(escaped_words) + r"(?![a-z0-9])"
    return bool(re.search(pattern, value.lower()))


def _contains_any(value: str, terms: set[str] | frozenset[str]) -> bool:
    return any(_contains_phrase(value, term) for term in terms)


def _max_required_years(text: str) -> int:
    years = [int(match.group(1)) for match in EXPERIENCE_YEARS_PATTERN.finditer(text)]
    return max(years, default=0)


def _infer_accepted_families(role_family: RoleFamily | None) -> frozenset[RoleFamily]:
    if role_family == "technology":
        return TECHNOLOGY_FAMILIES
    if role_family:
        return frozenset({role_family})
    return frozenset()


def _first_matching_family(query: str) -> RoleFamily | None:
    # Specific admin/clerical requests must be handled before generic "data".
    if _contains_any(query, CLERICAL_ADMIN_QUERY_TERMS):
        return "operations"

    priority: tuple[RoleFamily, ...] = (
        "technology",
        "software",
        "finance",
        "data",
        "cybersecurity",
        "product",
        "marketing",
        "operations",
        "healthcare",
        "design",
    )
    for family in priority:
        if _contains_any(query, ROLE_QUERY_TERMS[family]):
            return family
    return None


def classify_search_intent(query: str, level: JobLevel = "any") -> SearchIntent:
    normalized = query.lower().strip()
    role_family = _first_matching_family(normalized)
    return SearchIntent(
        query=query,
        level=level,
        role_family=role_family,
        accepted_families=_infer_accepted_families(role_family),
        accounting_focus=bool(_contains_any(normalized, {"accounting", "accountant", "audit", "tax"})),
        broad_technology=role_family == "technology",
    )


def _title_matches_family(title: str, family: RoleFamily) -> bool:
    if family == "technology":
        return bool(classify_job(title, "").families & TECHNOLOGY_FAMILIES) or _contains_any(title.lower(), TECHNOLOGY_ADJACENT_TITLE_TERMS)
    return _contains_any(title.lower(), ROLE_TITLE_TERMS.get(family, set()))


def _description_matches_family(description: str, family: RoleFamily) -> bool:
    description_lower = description.lower()
    if family == "technology":
        return any(_description_matches_family(description, technical_family) for technical_family in TECHNOLOGY_FAMILIES)
    if family == "data":
        strong_data_terms = {
            "data analyst",
            "data analytics",
            "data science",
            "data pipeline",
            "data pipelines",
            "datasets",
            "sql",
            "dashboard",
            "dashboards",
            "business intelligence",
            "analytics models",
        }
        return _contains_any(description_lower, strong_data_terms)
    return _contains_any(description_lower, ROLE_TITLE_TERMS.get(family, set()))


def _generic_analyst_without_technical_signal(title: str, families: set[RoleFamily]) -> bool:
    title_lower = title.lower()
    if not _contains_phrase(title_lower, "analyst"):
        return False
    if families & {"data", "cybersecurity", "finance"}:
        return False
    if _contains_any(title_lower, TECHNOLOGY_ADJACENT_TITLE_TERMS):
        return False
    return True


def classify_job(title: str, description: str = "") -> JobIntent:
    title_lower = title.lower()
    families: set[RoleFamily] = set()

    is_clerical_admin = _contains_any(title_lower, CLERICAL_ADMIN_TITLE_TERMS)
    is_technology_adjacent = _contains_any(title_lower, TECHNOLOGY_ADJACENT_TITLE_TERMS)

    for family, terms in ROLE_TITLE_TERMS.items():
        if _contains_any(title_lower, terms):
            families.add(family)

    if is_clerical_admin:
        families.add("operations")
    if is_technology_adjacent:
        families.add("technology")

    is_sales_support = bool(
        _contains_any(title_lower, SALES_SUPPORT_TITLE_TERMS)
        and not (families & {"software", "data", "cybersecurity", "finance"})
    )
    is_non_data_analyst = _contains_any(title_lower, NON_DATA_ANALYST_TITLE_TERMS) or _generic_analyst_without_technical_signal(title, families)
    has_internship_title = _contains_any(title_lower, INTERN_TITLE_TERMS)
    has_entry_title = _contains_any(title_lower, ENTRY_TEXT_TERMS)

    return JobIntent(
        title=title,
        families=frozenset(families),
        is_clerical_admin=is_clerical_admin,
        is_sales_support=is_sales_support,
        is_non_data_analyst=is_non_data_analyst,
        has_internship_title=has_internship_title,
        has_entry_title=has_entry_title,
        is_technology_adjacent=is_technology_adjacent,
    )


def _has_early_career_description(description: str) -> bool:
    description_lower = description.lower()
    max_years = _max_required_years(description_lower)
    return _contains_any(description_lower, ENTRY_TEXT_TERMS | INTERN_TITLE_TERMS) or (0 < max_years <= 3)


def _has_non_target_title_family(job: JobIntent, intent: SearchIntent) -> bool:
    if intent.role_family not in {"software", "data", "technology", "cybersecurity"}:
        return False
    return bool((job.families & NON_TECHNICAL_FAMILIES) and not (job.families & intent.accepted_families))


def _can_use_description_fallback(job: JobIntent, description: str, intent: SearchIntent) -> bool:
    # Description fallback is intentionally narrow. It is for true generic
    # internship postings like "Summer Analyst" or "Engineering Intern", not
    # arbitrary entry-level business/admin roles that merely mention data.
    if intent.level != "intern":
        return False
    if not (job.has_internship_title or _contains_any(description.lower(), INTERN_TITLE_TERMS)):
        return False
    return any(_description_matches_family(description, family) for family in intent.accepted_families)


def job_matches_search_intent(title: str, description: str, intent: SearchIntent) -> bool:
    if intent.role_family is None:
        return True

    job = classify_job(title, description)

    if intent.role_family in {"software", "data", "technology", "cybersecurity"} and (
        job.is_clerical_admin or job.is_sales_support or _has_non_target_title_family(job, intent)
    ):
        return False

    if intent.role_family in {"data", "technology"} and job.is_non_data_analyst and not (job.families & intent.accepted_families):
        return False

    if job.families & intent.accepted_families:
        return True

    if intent.role_family == "technology" and job.is_technology_adjacent:
        return True

    return _can_use_description_fallback(job, description, intent)


def title_matches_search_family(title: str, family: RoleFamily) -> bool:
    job = classify_job(title, "")
    accepted_families = _infer_accepted_families(family)
    if family in {"software", "data", "technology", "cybersecurity"} and (
        job.is_clerical_admin
        or job.is_sales_support
        or bool((job.families & NON_TECHNICAL_FAMILIES) and not (job.families & accepted_families))
    ):
        return False
    if family in {"data", "technology"} and job.is_non_data_analyst and not (job.families & accepted_families):
        return False
    if family == "technology":
        return bool(job.families & TECHNOLOGY_FAMILIES) or job.is_technology_adjacent
    return family in job.families or _title_matches_family(title, family)


def remotive_search_terms(query: str, level: JobLevel) -> list[str | None]:
    intent = classify_search_intent(query, level)
    normalized = query.lower().strip()
    terms: list[str | None] = []
    if normalized:
        terms.append(normalized)

    family = intent.role_family
    if family == "technology":
        terms.extend(
            ["software intern", "data intern", "analytics intern", "cybersecurity intern", "intern"]
            if level == "intern"
            else ["software", "data", "analytics", "cybersecurity", "developer"]
        )
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
    elif family == "operations":
        terms.extend(["data entry", "administrative assistant", "office assistant", "operations"])
    elif family:
        terms.extend(sorted(ROLE_QUERY_TERMS.get(family, set()))[:4])
        if level == "intern":
            terms.extend([f"{term} intern" for term in sorted(ROLE_QUERY_TERMS.get(family, set()))[:3]])
    elif level == "intern":
        terms.extend(["intern", "internship"])
    elif level == "entry":
        terms.extend(["junior", "entry level"])

    if level == "intern" or family in {"software", "finance", "technology"}:
        terms.append(None)

    seen: set[str | None] = set()
    unique_terms: list[str | None] = []
    for term in terms:
        normalized_term = term.strip().lower() if isinstance(term, str) else None
        if normalized_term in seen:
            continue
        seen.add(normalized_term)
        unique_terms.append(normalized_term)
        if len(unique_terms) >= 12:
            break
    return unique_terms


def no_results_warning(query: str, location: str | None, level: JobLevel, role_family: RoleFamily | None) -> str:
    intent = classify_search_intent(query, level)
    family = intent.role_family or role_family
    if family == "finance" and intent.accounting_focus:
        role_text = "finance/accounting"
    elif family == "technology":
        role_text = "computer science/technology"
    elif family == "operations" and _contains_any(query.lower(), CLERICAL_ADMIN_QUERY_TERMS):
        role_text = "admin/operations"
    elif family:
        role_text = family
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
    if family == "finance" and level == "intern":
        warning += " Finance/accounting internships are especially likely to live on campus boards, Workday/company career pages, LinkedIn, or Indeed."
    elif level == "intern":
        warning += " Internship coverage is especially dependent on what the configured public APIs currently expose."
    if location and location.lower() != "remote":
        warning += " U.S.-remote roles are included for city searches, but no matching results were found."
    return warning
