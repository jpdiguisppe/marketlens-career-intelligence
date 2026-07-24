from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

LegalCredentialBand = Literal["undergraduate", "law_student", "licensed", "unknown"]

LAW_ADJACENT_FAMILIES = frozenset(
    {"legal", "compliance", "policy", "legal_operations", "contracts"}
)

LICENSED_TITLE_TERMS = {
    "attorney",
    "associate attorney",
    "staff attorney",
    "litigation attorney",
    "lawyer",
    "counsel",
    "general counsel",
    "corporate counsel",
    "legal counsel",
    "public defender",
    "prosecutor",
    "solicitor",
    "barrister",
}
LICENSED_DESCRIPTION_TERMS = {
    "active bar membership",
    "active bar license",
    "bar admission required",
    "admitted to practice law",
    "admitted to the bar",
    "licensed attorney",
    "licensed to practice law",
    "member in good standing of the bar",
    "state bar membership",
}
JD_REQUIRED_PATTERN = re.compile(
    r"(?:\b(?:j\.?\s*d\.?|juris doctor|law degree)\b.{0,45}\b(?:required|mandatory|must have|minimum qualification)\b)"
    r"|(?:\b(?:required|mandatory|must have|minimum qualification)\b.{0,45}\b(?:j\.?\s*d\.?|juris doctor|law degree)\b)",
    re.IGNORECASE,
)
BAR_REQUIRED_PATTERN = re.compile(
    r"\b(?:active|current|valid)?\s*(?:state\s+)?bar\s+(?:admission|membership|license)\b"
    r"|\badmitted to (?:practice|the bar)\b"
    r"|\blicensed to practice law\b",
    re.IGNORECASE,
)

LAW_STUDENT_TITLE_TERMS = {
    "summer associate",
    "law clerk",
    "legal extern",
    "judicial intern",
    "judicial extern",
    "law student intern",
    "law student fellow",
}
LAW_STUDENT_DESCRIPTION_TERMS = {
    "currently enrolled in law school",
    "current law student",
    "enrolled in an accredited law school",
    "enrolled in law school",
    "jd candidate",
    "j.d. candidate",
    "juris doctor candidate",
    "pursuing a jd",
    "pursuing a j.d.",
    "pursuing a juris doctor",
    "rising 2l",
    "rising 3l",
    "1l student",
    "2l student",
    "3l student",
    "completed the first year of law school",
    "completion of the first year of law school",
}

INCLUSIVE_UNDERGRAD_ACCESS_TERMS = {
    "undergraduate or law student",
    "undergraduate and law students",
    "college or law school student",
    "college and law school students",
    "undergraduate, graduate, or law student",
    "undergraduate, graduate and law students",
}
UNDERGRAD_TITLE_TERMS = {
    "legal intern",
    "legal assistant",
    "legal analyst",
    "legal coordinator",
    "paralegal",
    "compliance analyst",
    "compliance associate",
    "policy analyst",
    "policy intern",
    "contracts analyst",
    "contract analyst",
    "contract specialist",
    "contract administrator",
    "legal operations",
    "legal ops",
    "regulatory analyst",
    "risk analyst",
}
UNDERGRAD_DESCRIPTION_TERMS = {
    "bachelor's degree",
    "bachelors degree",
    "undergraduate degree",
    "undergraduate student",
    "currently enrolled in college",
    "currently enrolled in a university",
}

LICENSED_QUERY_TERMS = {
    "attorney",
    "lawyer",
    "counsel",
    "licensed attorney",
    "bar admission",
    "admitted to the bar",
    "jd required",
    "j.d. required",
    "juris doctor required",
}
LAW_STUDENT_QUERY_TERMS = {
    "law student",
    "jd candidate",
    "j.d. candidate",
    "1l",
    "2l",
    "3l",
    "summer associate",
    "law clerk",
    "legal extern",
    "judicial intern",
    "judicial extern",
}
UNDERGRAD_QUERY_TERMS = {
    "legal intern",
    "legal internship",
    "legal assistant",
    "legal analyst",
    "legal coordinator",
    "paralegal",
    "compliance analyst",
    "policy analyst",
    "policy intern",
    "contracts analyst",
    "contract analyst",
    "contract specialist",
    "legal operations",
    "legal ops",
    "regulatory analyst",
}


@dataclass(frozen=True)
class LegalCredentialAssessment:
    band: LegalCredentialBand
    evidence: tuple[str, ...] = ()


def _contains_phrase(value: str, phrase: str) -> bool:
    cleaned_phrase = phrase.strip().lower()
    if not cleaned_phrase:
        return False
    words = [
        re.escape(part)
        for part in re.split(r"[\s,./()\-]+", cleaned_phrase)
        if part
    ]
    if not words:
        return False
    separator = r"[\s,./()\-]+"
    pattern = r"(?<![a-z0-9])" + separator.join(words) + r"(?![a-z0-9])"
    return bool(re.search(pattern, value.lower()))


def _matched_terms(value: str, terms: set[str]) -> tuple[str, ...]:
    return tuple(sorted(term for term in terms if _contains_phrase(value, term)))


def classify_posting_legal_credential(
    title: str,
    description: str,
) -> LegalCredentialAssessment:
    title_lower = title.lower()
    description_lower = description.lower()

    licensed_evidence = list(_matched_terms(title_lower, LICENSED_TITLE_TERMS))
    licensed_evidence.extend(
        _matched_terms(description_lower, LICENSED_DESCRIPTION_TERMS)
    )
    if JD_REQUIRED_PATTERN.search(description) is not None:
        licensed_evidence.append("jd_required")
    if BAR_REQUIRED_PATTERN.search(description) is not None:
        licensed_evidence.append("bar_required")
    if licensed_evidence:
        return LegalCredentialAssessment(
            band="licensed",
            evidence=tuple(dict.fromkeys(licensed_evidence)),
        )

    inclusive_evidence = _matched_terms(
        description_lower,
        INCLUSIVE_UNDERGRAD_ACCESS_TERMS,
    )
    if inclusive_evidence:
        return LegalCredentialAssessment(
            band="undergraduate",
            evidence=inclusive_evidence,
        )

    law_student_evidence = list(
        _matched_terms(title_lower, LAW_STUDENT_TITLE_TERMS)
    )
    law_student_evidence.extend(
        _matched_terms(description_lower, LAW_STUDENT_DESCRIPTION_TERMS)
    )
    if law_student_evidence:
        return LegalCredentialAssessment(
            band="law_student",
            evidence=tuple(dict.fromkeys(law_student_evidence)),
        )

    undergrad_evidence = list(_matched_terms(title_lower, UNDERGRAD_TITLE_TERMS))
    undergrad_evidence.extend(
        _matched_terms(description_lower, UNDERGRAD_DESCRIPTION_TERMS)
    )
    if undergrad_evidence:
        return LegalCredentialAssessment(
            band="undergraduate",
            evidence=tuple(dict.fromkeys(undergrad_evidence)),
        )

    return LegalCredentialAssessment(band="unknown")


def infer_requested_legal_credential(
    query: str,
    role_family: str | None,
    level: str,
) -> LegalCredentialBand | None:
    if role_family not in LAW_ADJACENT_FAMILIES:
        return None

    normalized = query.lower()
    if _matched_terms(normalized, LICENSED_QUERY_TERMS):
        return "licensed"
    if _matched_terms(normalized, LAW_STUDENT_QUERY_TERMS):
        return "law_student"
    if _matched_terms(normalized, UNDERGRAD_QUERY_TERMS):
        return "undergraduate"
    if level in {"intern", "entry"}:
        return "undergraduate"
    return "unknown"


def legal_credential_matches_search(
    *,
    title: str,
    description: str,
    query: str,
    role_family: str | None,
    level: str,
) -> bool:
    requested = infer_requested_legal_credential(query, role_family, level)
    if requested is None or requested == "unknown":
        return True

    posting = classify_posting_legal_credential(title, description)
    return posting.band in {requested, "unknown"}
