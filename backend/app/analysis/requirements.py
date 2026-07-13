import re
from collections import defaultdict

from app.analysis.normalization import split_text_fragments
from app.analysis.schemas import (
    HardRequirementAssessment,
    HardRequirementStatus,
    JobRequirement,
    ParsedSection,
    RequirementType,
    SectionKind,
)
from app.skill_extractor import extract_skills

_REQUIRED_CUES = re.compile(
    r"\b(must|required|requires|minimum|need to|needs to|strong experience|proficiency)\b",
    re.IGNORECASE,
)
_PREFERRED_CUES = re.compile(
    r"\b(preferred|nice to have|nice-to-have|bonus|desired|a plus)\b",
    re.IGNORECASE,
)
_RESPONSIBILITY_CUES = re.compile(
    r"\b(responsible for|you will|you'll|design|build|develop|maintain|implement|support|deploy)\b",
    re.IGNORECASE,
)

_REQUIREMENT_WEIGHTS: dict[RequirementType, float] = {
    RequirementType.REQUIRED_QUALIFICATION: 1.0,
    RequirementType.CORE_RESPONSIBILITY: 0.85,
    RequirementType.PREFERRED_QUALIFICATION: 0.5,
    RequirementType.SUPPORTING_CONTEXT: 0.25,
}

_HARD_REQUIREMENT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "citizenship",
        re.compile(r"\b(?:u\.?s\.?|united states)\s+citizen(?:ship)?\b", re.IGNORECASE),
    ),
    (
        "security_clearance",
        re.compile(
            r"\b(?:active\s+)?(?:security\s+)?(?:secret|top secret|ts/sci)\s+clearance\b|\bsecurity clearance\b",
            re.IGNORECASE,
        ),
    ),
    (
        "degree",
        re.compile(
            r"\b(?:bachelor(?:'s)?|master(?:'s)?|b\.?s\.?|b\.?a\.?|m\.?s\.?)\s+(?:degree\s+)?(?:in\s+)?[^.;\n]{0,80}",
            re.IGNORECASE,
        ),
    ),
    (
        "work_authorization",
        re.compile(
            r"\b(?:authorized to work|work authorization|without sponsorship|visa sponsorship)\b[^.;\n]*",
            re.IGNORECASE,
        ),
    ),
    (
        "years_experience",
        re.compile(
            r"\b\d+\+?\s+years?\s+(?:of\s+)?[^.;\n]{0,80}?\bexperience\b[^.;\n]*",
            re.IGNORECASE,
        ),
    ),
    (
        "travel",
        re.compile(r"\b(?:up to\s+)?\d{1,3}%\s+travel\b|\btravel\s+(?:is\s+)?required\b", re.IGNORECASE),
    ),
]


def _classify_requirement(section: ParsedSection, fragment: str) -> tuple[RequirementType, float, float]:
    if section.kind == SectionKind.PREFERRED or _PREFERRED_CUES.search(fragment):
        requirement_type = RequirementType.PREFERRED_QUALIFICATION
        confidence = 0.95 if section.kind == SectionKind.PREFERRED else 0.8
    elif section.kind == SectionKind.REQUIRED or _REQUIRED_CUES.search(fragment):
        requirement_type = RequirementType.REQUIRED_QUALIFICATION
        confidence = 0.95 if section.kind == SectionKind.REQUIRED else 0.82
    elif section.kind == SectionKind.RESPONSIBILITIES or _RESPONSIBILITY_CUES.search(fragment):
        requirement_type = RequirementType.CORE_RESPONSIBILITY
        confidence = 0.92 if section.kind == SectionKind.RESPONSIBILITIES else 0.75
    else:
        requirement_type = RequirementType.SUPPORTING_CONTEXT
        confidence = 0.65

    return requirement_type, _REQUIREMENT_WEIGHTS[requirement_type], confidence


def extract_job_requirements(sections: list[ParsedSection]) -> list[JobRequirement]:
    """Extract and prioritize technical requirements from parsed job sections."""
    candidates_by_skill: dict[str, list[JobRequirement]] = defaultdict(list)

    for section in sections:
        # Company marketing and benefits should not inflate a candidate's fit score.
        if section.kind in {SectionKind.COMPANY, SectionKind.BENEFITS}:
            continue

        for fragment in split_text_fragments(section.text):
            skills = extract_skills(fragment)
            if not skills:
                continue

            requirement_type, weight, confidence = _classify_requirement(section, fragment)
            for skill in skills:
                candidates_by_skill[skill].append(
                    JobRequirement(
                        skill=skill,
                        requirement_type=requirement_type,
                        weight=weight,
                        source_text=fragment,
                        source_section=section.kind,
                        confidence=confidence,
                    )
                )

    requirements: list[JobRequirement] = []
    for skill, candidates in candidates_by_skill.items():
        strongest = max(candidates, key=lambda item: (item.weight, item.confidence))
        mention_count = len(candidates)
        repetition_boost = min(0.1, max(0, mention_count - 1) * 0.025)
        requirements.append(
            strongest.model_copy(
                update={
                    "weight": min(1.0, strongest.weight + repetition_boost),
                    "mention_count": mention_count,
                }
            )
        )

    return sorted(requirements, key=lambda item: (-item.weight, item.skill.lower()))


def _find_source_fragment(text: str, match: re.Match[str]) -> str:
    start = max(text.rfind("\n", 0, match.start()), text.rfind(".", 0, match.start())) + 1
    newline_end = text.find("\n", match.end())
    sentence_end = text.find(".", match.end())
    possible_ends = [end for end in (newline_end, sentence_end) if end != -1]
    end = min(possible_ends) + 1 if possible_ends else len(text)
    return text[start:end].strip().removeprefix("- ")


def _evaluate_hard_requirement(category: str, source_text: str, resume_text: str) -> HardRequirementAssessment:
    resume_evidence: str | None = None
    status = HardRequirementStatus.UNCLEAR

    if category == "citizenship":
        evidence_match = re.search(r"\b(?:u\.?s\.?|united states)\s+citizen\b", resume_text, re.IGNORECASE)
        if evidence_match:
            status = HardRequirementStatus.MEETS
            resume_evidence = evidence_match.group(0)
    elif category == "security_clearance":
        evidence_match = re.search(
            r"\b(?:active\s+)?(?:secret|top secret|ts/sci)\s+clearance\b",
            resume_text,
            re.IGNORECASE,
        )
        if evidence_match:
            status = HardRequirementStatus.MEETS
            resume_evidence = evidence_match.group(0)
    elif category == "degree":
        evidence_match = re.search(
            r"\b(?:bachelor(?:'s)?|b\.?s\.?|b\.?a\.?|master(?:'s)?|m\.?s\.?)\b[^\n.;]{0,80}",
            resume_text,
            re.IGNORECASE,
        )
        if evidence_match:
            status = HardRequirementStatus.MEETS
            resume_evidence = evidence_match.group(0).strip()
    elif category == "work_authorization":
        evidence_match = re.search(
            r"\b(?:authorized to work|work authorization|without sponsorship)\b[^\n.;]*",
            resume_text,
            re.IGNORECASE,
        )
        if evidence_match:
            status = HardRequirementStatus.MEETS
            resume_evidence = evidence_match.group(0).strip()
    elif category == "years_experience":
        # Dates and overlapping roles require a proper timeline parser. Do not guess from a resume.
        status = HardRequirementStatus.UNCLEAR
    elif category == "travel":
        status = HardRequirementStatus.UNCLEAR

    explanation = (
        "The resume contains direct evidence for this constraint."
        if status == HardRequirementStatus.MEETS
        else "The resume does not provide enough reliable information to evaluate this constraint."
    )

    return HardRequirementAssessment(
        category=category,
        requirement=source_text,
        status=status,
        source_text=source_text,
        resume_evidence=resume_evidence,
        explanation=explanation,
    )


def assess_hard_requirements(job_text: str, resume_text: str) -> list[HardRequirementAssessment]:
    assessments: list[HardRequirementAssessment] = []
    seen_categories: set[str] = set()

    for category, pattern in _HARD_REQUIREMENT_PATTERNS:
        match = pattern.search(job_text)
        if match is None or category in seen_categories:
            continue

        seen_categories.add(category)
        source_text = _find_source_fragment(job_text, match) or match.group(0)
        assessments.append(_evaluate_hard_requirement(category, source_text, resume_text))

    return assessments