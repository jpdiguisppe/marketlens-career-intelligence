import re

from app.analysis.normalization import split_text_fragments
from app.analysis.schemas import EvidenceStatus, ParsedSection, ResumeEvidence, SectionKind
from app.skill_extractor import extract_skills

_ACTION_VERBS = {
    "architected",
    "automated",
    "built",
    "configured",
    "created",
    "deployed",
    "designed",
    "developed",
    "implemented",
    "improved",
    "integrated",
    "maintained",
    "managed",
    "migrated",
    "optimized",
    "programmed",
    "refactored",
    "tested",
    "troubleshot",
}

_IMPLIED_SKILLS: dict[str, list[tuple[str, float, str]]] = {
    "FastAPI": [
        (
            "REST APIs",
            0.4,
            "FastAPI work can support REST API experience, but the resume should state the API behavior directly.",
        )
    ],
    "PostgreSQL": [
        (
            "SQL",
            0.4,
            "PostgreSQL experience implies some SQL exposure, but query and schema work are not directly described.",
        )
    ],
    "MySQL": [
        (
            "SQL",
            0.4,
            "MySQL experience implies some SQL exposure, but query and schema work are not directly described.",
        )
    ],
    "Node.js": [
        (
            "JavaScript",
            0.35,
            "Node.js usually uses JavaScript, but the language is not directly demonstrated in this evidence.",
        )
    ],
}


def _starts_with_action_verb(fragment: str) -> bool:
    first_word_match = re.match(r"^[^A-Za-z]*([A-Za-z]+)", fragment)
    return bool(first_word_match and first_word_match.group(1).lower() in _ACTION_VERBS)


def _classify_explicit_evidence(section: ParsedSection, fragment: str) -> tuple[EvidenceStatus, float, str]:
    if section.kind == SectionKind.SKILLS:
        return (
            EvidenceStatus.MENTIONED,
            0.55,
            "The skill is listed, but this line does not show how it was applied.",
        )

    if section.kind in {SectionKind.EXPERIENCE, SectionKind.PROJECTS} and _starts_with_action_verb(fragment):
        return (
            EvidenceStatus.DEMONSTRATED,
            1.0,
            "A project or experience bullet directly demonstrates use of this skill.",
        )

    if section.kind in {SectionKind.EXPERIENCE, SectionKind.PROJECTS}:
        return (
            EvidenceStatus.EXPLICIT,
            0.8,
            "The skill is explicitly connected to project or work experience.",
        )

    return (
        EvidenceStatus.EXPLICIT,
        0.75,
        "The skill is explicitly present, but the surrounding evidence is limited.",
    )


def extract_resume_evidence(sections: list[ParsedSection]) -> dict[str, ResumeEvidence]:
    """Build the strongest evidence object found for each resume skill."""
    strongest_evidence: dict[str, ResumeEvidence] = {}

    for section in sections:
        for fragment in split_text_fragments(section.text):
            status, strength, explanation = _classify_explicit_evidence(section, fragment)
            for skill in extract_skills(fragment):
                evidence = ResumeEvidence(
                    skill=skill,
                    status=status,
                    strength=strength,
                    source_text=fragment,
                    source_section=section.kind,
                    explanation=explanation,
                )
                existing = strongest_evidence.get(skill)
                if existing is None or evidence.strength > existing.strength:
                    strongest_evidence[skill] = evidence

    # Add conservative implied evidence only when no stronger direct evidence exists.
    for source_skill, implications in _IMPLIED_SKILLS.items():
        source_evidence = strongest_evidence.get(source_skill)
        if source_evidence is None:
            continue

        for implied_skill, strength, explanation in implications:
            existing = strongest_evidence.get(implied_skill)
            if existing is not None and existing.strength >= strength:
                continue

            strongest_evidence[implied_skill] = ResumeEvidence(
                skill=implied_skill,
                status=EvidenceStatus.IMPLIED,
                strength=strength,
                source_text=source_evidence.source_text,
                source_section=source_evidence.source_section,
                explanation=explanation,
            )

    return strongest_evidence
