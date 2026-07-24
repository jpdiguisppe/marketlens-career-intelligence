from app.job_search import _score_job, parse_job_search_intent
from app.legal_credentials import (
    classify_posting_legal_credential,
    infer_requested_legal_credential,
)


def test_requested_credential_band_is_inferred_from_query_and_level() -> None:
    assert infer_requested_legal_credential(
        "legal internship",
        "legal",
        "intern",
    ) == "undergraduate"
    assert infer_requested_legal_credential(
        "law student internship",
        "legal",
        "intern",
    ) == "law_student"
    assert infer_requested_legal_credential(
        "2L summer associate",
        "legal",
        "intern",
    ) == "law_student"
    assert infer_requested_legal_credential(
        "attorney jobs",
        "legal",
        "any",
    ) == "licensed"
    assert infer_requested_legal_credential(
        "legal jobs",
        "legal",
        "any",
    ) == "unknown"
    assert infer_requested_legal_credential(
        "software internship",
        "software",
        "intern",
    ) is None


def test_law_student_queries_parse_as_legal_searches() -> None:
    law_student = parse_job_search_intent("law student internship")
    summer_associate = parse_job_search_intent("2L summer associate")
    judicial = parse_job_search_intent("judicial internship")

    assert (law_student.job_function, law_student.level) == ("legal", "intern")
    assert (summer_associate.job_function, summer_associate.level) == (
        "legal",
        "intern",
    )
    assert (judicial.job_function, judicial.level) == ("legal", "intern")


def test_posting_credential_classification_uses_title_and_requirements() -> None:
    assert classify_posting_legal_credential(
        "Legal Intern",
        "Open to undergraduate or law student applicants.",
    ).band == "undergraduate"
    assert classify_posting_legal_credential(
        "Legal Intern",
        "Applicants must be a current 2L student enrolled in law school.",
    ).band == "law_student"
    assert classify_posting_legal_credential(
        "Summer Associate",
        "Seeking a JD candidate who has completed the first year of law school.",
    ).band == "law_student"
    assert classify_posting_legal_credential(
        "Associate Attorney",
        "A Juris Doctor is required along with active bar membership.",
    ).band == "licensed"
    assert classify_posting_legal_credential(
        "Compliance Counsel",
        "Must be licensed to practice law in at least one state.",
    ).band == "licensed"
    assert classify_posting_legal_credential(
        "Legal Specialist",
        "Support document review and internal requests.",
    ).band == "unknown"


def test_undergraduate_legal_internship_excludes_law_student_only_roles() -> None:
    assert _score_job(
        "Legal Intern",
        "Open to undergraduate students pursuing a bachelor's degree.",
        "legal internship",
        level="intern",
        company="Example Organization",
    ) > 0
    assert _score_job(
        "Summer Associate",
        "Applicants must be current 2L or 3L law students.",
        "legal internship",
        level="intern",
        company="Example Law Firm",
    ) == 0
    assert _score_job(
        "Law Clerk Intern",
        "Must be currently enrolled in an accredited law school.",
        "legal internship",
        level="intern",
        company="Example Court",
    ) == 0


def test_entry_level_legal_search_excludes_attorney_only_roles() -> None:
    assert _score_job(
        "Legal Assistant",
        "Bachelor's degree preferred. Requires 1 year of experience.",
        "entry level legal",
        level="entry",
        company="Example Company",
    ) > 0
    assert _score_job(
        "Associate Attorney",
        "Requires 1 year of experience, a JD, and active bar membership.",
        "entry level legal",
        level="entry",
        company="Example Law Firm",
    ) == 0
    assert _score_job(
        "Compliance Counsel",
        "Entry-level opportunity. JD required; must be admitted to the bar.",
        "entry level compliance",
        level="entry",
        company="Example Company",
    ) == 0


def test_law_student_search_targets_law_school_roles() -> None:
    assert _score_job(
        "Summer Associate",
        "Seeking a current 2L JD candidate for the summer program.",
        "law student internship",
        level="intern",
        company="Example Law Firm",
    ) > 0
    assert _score_job(
        "Judicial Intern",
        "Applicants must be currently enrolled in law school.",
        "law student internship",
        level="intern",
        company="Example Court",
    ) > 0
    assert _score_job(
        "Legal Intern",
        "Open to undergraduate students currently enrolled in college.",
        "law student internship",
        level="intern",
        company="Example Company",
    ) == 0


def test_licensed_search_targets_attorney_roles() -> None:
    assert _score_job(
        "Associate Attorney",
        "JD required. Must have active bar membership.",
        "attorney jobs",
        company="Example Law Firm",
    ) > 0
    assert _score_job(
        "Legal Assistant",
        "Bachelor's degree preferred and no prior experience required.",
        "attorney jobs",
        company="Example Law Firm",
    ) == 0
    assert _score_job(
        "Compliance Analyst",
        "Bachelor's degree and 1 year of experience required.",
        "compliance counsel jobs",
        company="Example Company",
    ) == 0


def test_non_legal_search_scoring_is_unchanged() -> None:
    assert _score_job(
        "Software Engineer I",
        "Early-career backend role requiring 1 year of experience.",
        "entry level software engineer",
        level="entry",
        company="Example Technology Company",
    ) > 0
