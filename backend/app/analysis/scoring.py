from app.analysis.schemas import (
    EvidenceStatus,
    FitBand,
    FitSummary,
    JobRequirement,
    RequirementAssessment,
    ResumeEvidence,
)
from app.analysis.skill_ontology import SKILL_CATEGORIES

_CATEGORY_GAP_PRIORITY: dict[str, int] = {
    "full_stack": 12,
    "backend": 11,
    "frontend": 10,
    "programming_language": 9,
    "software_architecture": 8,
    "database": 7,
    "software_design": 6,
    "software_engineering": 5,
    "devops": 4,
    "quality": 3,
    "cloud": 2,
    "process": 1,
}


def assess_requirements(
    requirements: list[JobRequirement],
    resume_evidence: dict[str, ResumeEvidence],
) -> list[RequirementAssessment]:
    assessments: list[RequirementAssessment] = []

    for requirement in requirements:
        evidence = resume_evidence.get(requirement.skill)

        if evidence is None:
            assessments.append(
                RequirementAssessment(
                    skill=requirement.skill,
                    requirement_type=requirement.requirement_type,
                    weight=requirement.weight,
                    status=EvidenceStatus.MISSING,
                    strength=0.0,
                    resume_evidence=[],
                    job_evidence=requirement.source_text,
                    explanation="No reliable resume evidence was found for this requirement.",
                )
            )
            continue

        assessments.append(
            RequirementAssessment(
                skill=requirement.skill,
                requirement_type=requirement.requirement_type,
                weight=requirement.weight,
                status=evidence.status,
                strength=evidence.strength,
                resume_evidence=[evidence.source_text],
                job_evidence=requirement.source_text,
                explanation=evidence.explanation,
            )
        )

    return assessments


def _fit_band(score: int) -> FitBand:
    if score >= 80:
        return FitBand.STRONG_ALIGNMENT
    if score >= 65:
        return FitBand.CREDIBLE_ALIGNMENT
    if score >= 45:
        return FitBand.PARTIAL_ALIGNMENT
    return FitBand.LIMITED_ALIGNMENT


def calculate_fit_score(assessments: list[RequirementAssessment]) -> int:
    total_weight = sum(assessment.weight for assessment in assessments)
    if total_weight <= 0:
        return 0

    weighted_evidence = sum(
        assessment.weight * assessment.strength for assessment in assessments
    )
    return round((weighted_evidence / total_weight) * 100)


def _primary_gap(assessments: list[RequirementAssessment]) -> str | None:
    important_gaps = [
        assessment
        for assessment in assessments
        if assessment.status == EvidenceStatus.MISSING and assessment.weight >= 0.75
    ]
    if not important_gaps:
        return None

    return sorted(
        important_gaps,
        key=lambda assessment: (
            -_CATEGORY_GAP_PRIORITY.get(SKILL_CATEGORIES.get(assessment.skill, "other"), 0),
            -assessment.weight,
            assessment.skill.lower(),
        ),
    )[0].skill


def build_fit_summary(
    assessments: list[RequirementAssessment],
    confidence: float,
) -> FitSummary:
    score = calculate_fit_score(assessments)
    band = _fit_band(score)

    primary_gap = _primary_gap(assessments)
    under_sold = [
        assessment.skill
        for assessment in assessments
        if assessment.status in {EvidenceStatus.MENTIONED, EvidenceStatus.IMPLIED}
        and assessment.weight >= 0.5
    ]

    if band == FitBand.STRONG_ALIGNMENT:
        headline = "The resume demonstrates most high-priority technical requirements."
    elif band == FitBand.CREDIBLE_ALIGNMENT:
        headline = "The resume shows credible alignment, with some evidence that could be clearer."
    elif band == FitBand.PARTIAL_ALIGNMENT:
        headline = "The resume demonstrates part of the role, but several important requirements are weak or absent."
    else:
        headline = "The resume currently provides limited evidence for the role's core technical requirements."

    if primary_gap:
        headline += f" The largest documented gap is {primary_gap}."
    elif under_sold:
        headline += f" {under_sold[0]} appears under-explained."

    return FitSummary(
        score=score,
        band=band,
        confidence=round(confidence, 2),
        headline=headline,
    )
