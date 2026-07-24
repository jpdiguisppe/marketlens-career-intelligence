from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one match in {path}: found {count} for {old[:120]!r}")
    path.write_text(text.replace(old, new, 1))


job_search = ROOT / "backend/app/job_search.py"
intent_engine = ROOT / "backend/app/job_intent_engine.py"

replace_once(
    job_search,
    '''LEVEL_QUERY_TERMS = {
    "intern",
    "internship",
    "co-op",
    "coop",
    "co",
    "op",
    "entry",
    "level",
    "junior",
    "associate",
    "new",
    "grad",
    "graduate",
    "senior",
    "staff",
    "principal",
    "lead",
    "mid",
}
GENERIC_SOFTWARE_QUERY_TERMS = {"engineer", "engineering", "developer", "development"}
INTERN_TERMS = {"intern", "internship", "co-op", "coop", "co op"}
ENTRY_TITLE_TERMS = {
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
ENTRY_DESCRIPTION_TERMS = {
    "entry level",
    "entry-level",
    "junior engineer",
    "junior developer",
    "junior analyst",
    "junior accountant",
    "new grad",
    "new graduate",
    "university grad",
    "university graduate",
    "early career",
}
''',
    '''LEVEL_QUERY_TERMS = {
    "intern",
    "internship",
    "co-op",
    "coop",
    "co",
    "op",
    "apprentice",
    "apprenticeship",
    "fellowship",
    "summer",
    "fall",
    "spring",
    "winter",
    "student",
    "entry",
    "level",
    "junior",
    "associate",
    "new",
    "recent",
    "grad",
    "graduate",
    "rotational",
    "rotation",
    "program",
    "early",
    "career",
    "campus",
    "university",
    "senior",
    "staff",
    "principal",
    "lead",
    "mid",
}
GENERIC_SOFTWARE_QUERY_TERMS = {"engineer", "engineering", "developer", "development"}
INTERN_TERMS = {
    "intern",
    "internship",
    "co-op",
    "coop",
    "co op",
    "cooperative education",
    "apprentice",
    "apprenticeship",
    "fellowship",
    "summer associate",
    "student trainee",
    "industrial placement",
    "graduate internship",
}
INTERN_TITLE_TERMS = INTERN_TERMS | {
    "fellow",
    "student program",
    "university program",
    "campus program",
}
INTERN_DESCRIPTION_TERMS = {
    "internship program",
    "intern program",
    "co-op program",
    "cooperative education",
    "apprenticeship program",
    "fellowship program",
}
STUDENT_ELIGIBILITY_TERMS = {
    "currently enrolled",
    "enrolled in a bachelor's",
    "enrolled in a bachelor",
    "enrolled in a master's",
    "enrolled in a master",
    "pursuing a bachelor's",
    "pursuing a bachelor",
    "pursuing a master's",
    "pursuing a master",
    "returning to school",
    "return to school",
    "graduation date",
    "expected graduation",
    "current student",
    "undergraduate student",
    "graduate student",
}
SEASONAL_EARLY_CAREER_TERMS = {"summer", "fall", "spring", "winter"}
ENTRY_TITLE_TERMS = {
    "entry level",
    "entry-level",
    "junior",
    "associate",
    "new grad",
    "new graduate",
    "recent graduate",
    "university grad",
    "university graduate",
    "early career",
    "early talent",
    "campus hire",
    "university hire",
}
ENTRY_PROGRAM_TITLE_TERMS = {
    "graduate program",
    "graduate scheme",
    "rotational program",
    "rotation program",
    "leadership development program",
    "analyst development program",
    "career development program",
    "early career program",
    "early talent program",
}
ENTRY_DESCRIPTION_TERMS = {
    "entry level",
    "entry-level",
    "junior engineer",
    "junior developer",
    "junior analyst",
    "junior accountant",
    "new grad",
    "new graduate",
    "recent graduate",
    "university grad",
    "university graduate",
    "early career",
    "early talent",
    "campus hire",
    "university hire",
}
ZERO_EXPERIENCE_TERMS = {
    "no experience required",
    "no prior experience required",
    "no professional experience required",
    "no prior professional experience required",
    "0 years of experience",
    "zero years of experience",
}
''',
)

replace_once(
    job_search,
    '''        "intern": ["intern"],
        "internship": ["intern"],
        "entry level": ["entry", "level"],
        "entry-level": ["entry", "level"],
        "new grad": ["new", "grad"],
''',
    '''        "intern": ["intern"],
        "internship": ["intern"],
        "co-op": ["intern"],
        "apprenticeship": ["intern"],
        "fellowship": ["intern"],
        "summer associate": ["intern"],
        "entry level": ["entry", "level"],
        "entry-level": ["entry", "level"],
        "new grad": ["new", "grad"],
        "new graduate": ["new", "grad"],
        "recent graduate": ["new", "grad"],
        "rotational program": ["entry", "program"],
        "graduate program": ["entry", "program"],
''',
)

replace_once(
    job_search,
    '''def _infer_level_from_query(query: str) -> JobLevel:
    normalized = query.lower()
    if _contains_any(normalized, INTERN_TERMS):
        return "intern"
    if _contains_any(normalized, ENTRY_TITLE_TERMS):
        return "entry"
    if _contains_any(normalized, SENIOR_TERMS) or SENIOR_NUMBERED_TITLE_PATTERN.search(normalized):
        return "senior"
    if _contains_any(normalized, MID_TERMS) or MID_LEVEL_TITLE_PATTERN.search(normalized):
        return "mid"
    return "any"
''',
    '''def _infer_level_from_query(query: str) -> JobLevel:
    normalized = query.lower()
    if _contains_any(normalized, INTERN_TERMS):
        return "intern"
    if _contains_any(normalized, ENTRY_TITLE_TERMS | ENTRY_PROGRAM_TITLE_TERMS):
        return "entry"
    if _contains_any(normalized, SENIOR_TERMS) or SENIOR_NUMBERED_TITLE_PATTERN.search(normalized):
        return "senior"
    if _contains_any(normalized, MID_TERMS) or MID_LEVEL_TITLE_PATTERN.search(normalized):
        return "mid"
    return "any"
''',
)

replace_once(
    job_search,
    '''    is_generic_early_career_title = _contains_any(
        title_lower,
        {"intern", "internship", "summer analyst", "analyst intern", "rotational program", "graduate program"},
    )
''',
    '''    is_generic_early_career_title = _contains_any(
        title_lower,
        INTERN_TITLE_TERMS | ENTRY_PROGRAM_TITLE_TERMS,
    )
''',
)

replace_once(
    job_search,
    '''def _looks_like_intern_role(title: str, description: str) -> bool:
    searchable = f"{title} {description}".lower()
    return _contains_any(searchable, INTERN_TERMS)
''',
    '''def _title_has_seasonal_early_career_signal(title: str) -> bool:
    title_lower = title.lower()
    if not _contains_any(title_lower, SEASONAL_EARLY_CAREER_TERMS):
        return False
    return bool(
        _contains_any(
            title_lower,
            {"program", "student", "associate", "fellowship", "co-op", "coop", "intern", "internship"},
        )
        or re.search(r"\\b20\\d{2}\\b", title_lower)
    )


def _looks_like_intern_role(title: str, description: str) -> bool:
    title_lower = title.lower()
    description_lower = description.lower()

    if _title_has_senior_signal(title) or _title_has_mid_signal(title):
        return False
    if _contains_any(title_lower, INTERN_TITLE_TERMS):
        return True
    if _title_has_seasonal_early_career_signal(title):
        return _contains_any(
            description_lower,
            STUDENT_ELIGIBILITY_TERMS | INTERN_DESCRIPTION_TERMS,
        )
    return False
''',
)

replace_once(
    job_search,
    '''def _looks_like_entry_role(title: str, description: str) -> bool:
    title_lower = title.lower()
    description_lower = description.lower()

    if _looks_like_intern_role(title, description):
        return False

    if _title_has_senior_signal(title) or _title_has_mid_signal(title):
        return False

    if _contains_any(title_lower, ENTRY_TITLE_TERMS) or ENTRY_NUMBERED_TITLE_PATTERN.search(title):
        return True

    if _contains_any(description_lower, ENTRY_DESCRIPTION_TERMS):
        return True

    max_years = _max_required_years(description)
    return 0 < max_years <= 3 and not _looks_like_senior_role(title, description)
''',
    '''def _looks_like_entry_role(title: str, description: str) -> bool:
    title_lower = title.lower()
    description_lower = description.lower()

    if _looks_like_intern_role(title, description):
        return False

    if _title_has_senior_signal(title) or _title_has_mid_signal(title):
        return False

    max_years = _max_required_years(description)
    if max_years >= 4:
        return False

    if (
        _contains_any(title_lower, ENTRY_TITLE_TERMS | ENTRY_PROGRAM_TITLE_TERMS)
        or ENTRY_NUMBERED_TITLE_PATTERN.search(title)
    ):
        return True

    if _contains_any(description_lower, ENTRY_DESCRIPTION_TERMS | ZERO_EXPERIENCE_TERMS):
        return True

    return 0 < max_years <= 3 and not _looks_like_senior_role(title, description)
''',
)

replace_once(
    job_search,
    '''    if level == "intern" and _contains_any(title_lower, INTERN_TERMS):
        return 10
    if level == "entry" and (_contains_any(title_lower, ENTRY_TITLE_TERMS) or ENTRY_NUMBERED_TITLE_PATTERN.search(title)):
        return 8
''',
    '''    if level == "intern" and (
        _contains_any(title_lower, INTERN_TITLE_TERMS)
        or _title_has_seasonal_early_career_signal(title)
    ):
        return 10
    if level == "entry" and (
        _contains_any(title_lower, ENTRY_TITLE_TERMS | ENTRY_PROGRAM_TITLE_TERMS)
        or ENTRY_NUMBERED_TITLE_PATTERN.search(title)
    ):
        return 8
''',
)

replace_once(
    intent_engine,
    '''INTERN_TITLE_TERMS = {
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
''',
    '''INTERN_TITLE_TERMS = {
    "intern",
    "internship",
    "co-op",
    "coop",
    "co op",
    "cooperative education",
    "summer analyst",
    "summer intern",
    "summer internship",
    "summer associate",
    "student intern",
    "student trainee",
    "university intern",
    "internship program",
    "intern program",
    "apprentice",
    "apprenticeship",
    "fellow",
    "fellowship",
    "industrial placement",
    "graduate internship",
}

ENTRY_TEXT_TERMS = {
    "entry level",
    "entry-level",
    "junior",
    "associate",
    "new grad",
    "new graduate",
    "recent graduate",
    "university grad",
    "university graduate",
    "early career",
    "early talent",
    "campus hire",
    "university hire",
    "graduate program",
    "graduate scheme",
    "rotational program",
    "rotation program",
    "leadership development program",
    "analyst development program",
    "career development program",
}
''',
)

replace_once(
    intent_engine,
    '''def _can_use_description_fallback(job: JobIntent, description: str, intent: SearchIntent) -> bool:
    # Description fallback is intentionally narrow. It is for true generic
    # internship postings like "Summer Analyst" or "Engineering Intern", not
    # arbitrary entry-level business/admin roles that merely mention data.
    if intent.level != "intern":
        return False
    if not (job.has_internship_title or _contains_any(description.lower(), INTERN_TITLE_TERMS)):
        return False
    return any(_description_matches_family(description, family) for family in intent.accepted_families)
''',
    '''def _can_use_description_fallback(job: JobIntent, description: str, intent: SearchIntent) -> bool:
    # Description fallback is intentionally narrow. It is reserved for generic
    # early-career program titles whose descriptions clearly identify the
    # requested occupation family.
    if intent.level == "intern":
        if not job.has_internship_title:
            return False
    elif intent.level == "entry":
        if not job.has_entry_title:
            return False
    else:
        return False
    return any(_description_matches_family(description, family) for family in intent.accepted_families)
''',
)

replace_once(
    intent_engine,
    '''            ["software intern", "data intern", "analytics intern", "cybersecurity intern", "intern"]
            if level == "intern"
            else ["software", "data", "analytics", "cybersecurity", "developer"]
''',
    '''            [
                "software intern",
                "data intern",
                "analytics intern",
                "cybersecurity intern",
                "software co-op",
                "technology apprenticeship",
                "technology fellowship",
                "intern",
            ]
            if level == "intern"
            else (
                ["software", "data", "analytics", "cybersecurity", "developer"]
                if level != "entry"
                else ["new grad software", "entry level data", "early career technology", "technology rotational program"]
            )
''',
)

replace_once(
    intent_engine,
    '''                "engineering intern",
                "intern",
            ])
''',
    '''                "engineering intern",
                "software co-op",
                "software apprentice",
                "software fellowship",
                "intern",
            ])
        elif level == "entry":
            terms.extend([
                "new grad software engineer",
                "entry level software engineer",
                "associate software engineer",
                "software engineer i",
                "software rotational program",
            ])
''',
)

replace_once(
    intent_engine,
    '''        elif level == "entry":
            terms.extend(["junior financial analyst", "entry level finance", "junior accountant"])
''',
    '''        elif level == "entry":
            terms.extend([
                "junior financial analyst",
                "entry level finance",
                "junior accountant",
                "finance rotational program",
                "recent graduate finance",
            ])
''',
)

replace_once(
    intent_engine,
    '''        elif level == "entry":
            terms.extend(["junior data analyst", "entry level data analyst", "analytics associate"])
''',
    '''        elif level == "entry":
            terms.extend([
                "junior data analyst",
                "entry level data analyst",
                "analytics associate",
                "new grad data analyst",
                "data rotational program",
            ])
''',
)

replace_once(
    intent_engine,
    '''        if level == "intern":
            terms.extend([f"{term} intern" for term in sorted(ROLE_QUERY_TERMS.get(family, set()))[:3]])
    elif level == "intern":
        terms.extend(["intern", "internship"])
    elif level == "entry":
        terms.extend(["junior", "entry level"])
''',
    '''        if level == "intern":
            base_terms = sorted(ROLE_QUERY_TERMS.get(family, set()))[:3]
            terms.extend([f"{term} intern" for term in base_terms])
            terms.extend([f"{term} co-op" for term in base_terms[:2]])
            terms.extend([f"{term} fellowship" for term in base_terms[:2]])
        elif level == "entry":
            base_terms = sorted(ROLE_QUERY_TERMS.get(family, set()))[:3]
            terms.extend([f"entry level {term}" for term in base_terms])
            terms.extend([f"new grad {term}" for term in base_terms[:2]])
    elif level == "intern":
        terms.extend(["intern", "internship", "co-op", "apprenticeship", "fellowship"])
    elif level == "entry":
        terms.extend(["junior", "entry level", "new grad", "recent graduate", "rotational program"])
''',
)

(ROOT / "backend/tests/test_early_career_recall.py").write_text(
    '''import pytest

from app.job_search import (
    _matches_level,
    _remotive_search_terms,
    _score_job,
    resolve_job_level,
)


@pytest.mark.parametrize(
    ("query", "expected_level"),
    [
        ("software engineering co-op", "intern"),
        ("public policy fellowship", "intern"),
        ("legal summer associate", "intern"),
        ("finance rotational program", "entry"),
        ("recent graduate data analyst", "entry"),
        ("early talent cybersecurity", "entry"),
    ],
)
def test_resolve_job_level_recognizes_broader_early_career_language(
    query: str,
    expected_level: str,
) -> None:
    assert resolve_job_level(query) == expected_level


@pytest.mark.parametrize(
    ("title", "description"),
    [
        ("2027 Software Engineering Co-op", "Students rotate through backend engineering teams."),
        ("Public Policy Fellowship", "Fellows support policy research and advocacy."),
        ("Summer 2027 Software Engineering", "Candidates must be currently enrolled and returning to school."),
        ("Technology Apprentice", "Apprentices receive structured software engineering training."),
    ],
)
def test_intern_matching_recalls_coops_fellowships_and_seasonal_programs(
    title: str,
    description: str,
) -> None:
    assert _matches_level(title, description, "intern") is True


def test_intern_matching_rejects_roles_that_only_mention_interns() -> None:
    assert _matches_level(
        "Senior Software Engineer",
        "Lead platform architecture and mentor interns during the summer program.",
        "intern",
    ) is False
    assert _matches_level(
        "Software Engineer",
        "Partner internally with recruiting and occasionally support the internship program.",
        "intern",
    ) is False


@pytest.mark.parametrize(
    ("title", "description"),
    [
        ("Software Engineer I", "Build backend services with Python and SQL."),
        ("Associate Software Engineer", "Early career role for recent graduates."),
        ("Technology Rotational Program", "Recent graduates rotate through software engineering and data teams."),
        ("Software Engineer", "No prior professional experience required. Training is provided."),
        ("Data Analyst", "Candidates should have 0-2 years of analytics experience."),
    ],
)
def test_entry_matching_recalls_numbered_program_and_low_experience_roles(
    title: str,
    description: str,
) -> None:
    assert _matches_level(title, description, "entry") is True


def test_entry_matching_rejects_senior_titles_and_high_experience_requirements() -> None:
    assert _matches_level(
        "Senior Software Engineer",
        "Join an early career mentorship initiative while requiring 7+ years of experience.",
        "entry",
    ) is False
    assert _matches_level(
        "Software Engineer",
        "This entry-level branded role requires 5+ years of production experience.",
        "entry",
    ) is False


def test_scoring_accepts_generic_program_only_with_requested_role_evidence() -> None:
    assert _score_job(
        "Technology Rotational Program",
        "Recent graduates rotate through software engineering, backend, and data platform teams.",
        "software engineer entry level",
        level="entry",
    ) > 0
    assert _score_job(
        "Business Rotational Program",
        "Recent graduates rotate through sales, recruiting, and account management.",
        "software engineer entry level",
        level="entry",
    ) == 0


def test_scoring_rejects_intern_mentions_in_unrelated_experienced_roles() -> None:
    assert _score_job(
        "Senior Software Engineer",
        "Own backend systems and mentor software engineering interns.",
        "software engineering internship",
        level="intern",
    ) == 0


def test_remote_search_terms_include_early_career_aliases() -> None:
    intern_terms = _remotive_search_terms("software engineering co-op", "intern")
    entry_terms = _remotive_search_terms("software engineer entry level", "entry")

    assert "software co-op" in intern_terms
    assert "software fellowship" in intern_terms
    assert "new grad software engineer" in entry_terms
    assert "software engineer i" in entry_terms
'''
)

(ROOT / "docs/milestone-7-early-career-recall.md").write_text(
    '''# Milestone 7 — Internship and Entry-Level Recall

This phase broadens early-career matching while retaining strict title, occupation, and experience safeguards.

## Added recall signals

Internship searches now recognize co-ops, cooperative education, apprenticeships, fellowships, summer-associate programs, student-trainee roles, graduate internships, industrial placements, and seasonal programs backed by student-eligibility language.

Entry-level searches now recognize recent-graduate and early-talent language, Engineer/Analyst I titles, rotational and graduate programs, campus/university hiring language, explicit no-experience-required postings, and descriptions requiring no more than three years of experience.

Remote-provider search passes now include co-op, apprenticeship, fellowship, new-grad, rotational-program, and numbered entry-level variants.

## Precision boundaries

- A description that merely says an employee will mentor interns does not make an experienced role an internship.
- Seasonal titles require student or program evidence rather than the word `summer` alone.
- Senior and mid-level titles remain excluded from internship and entry-level searches.
- A posting requiring four or more years of experience is not treated as entry-level even when the description uses entry-level branding.
- Generic rotational/program titles must contain description evidence for the requested job function.

Credential-aware legal filtering remains the next separate legal-specific phase; this work only improves general early-career level recognition and recall.
'''
)

print("Applied Milestone 7 early-career recall improvements.")
