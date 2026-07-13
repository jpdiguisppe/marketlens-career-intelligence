from statistics import mean

from app.analysis.evidence import extract_resume_evidence
from app.analysis.normalization import meaningful_lines, normalize_document_text
from app.analysis.requirements import assess_hard_requirements, extract_job_requirements
from app.analysis.schemas import (
    DocumentQuality,
    EvidenceStatus,
    FitBand,
    RequirementAssessment,
    SectionKind,
    SmartFitAnalysisResponse,
)
from app.analysis.scoring import assess_requirements, build_fit_summary
from app.analysis.section_parser import parse_job_sections, parse_resume_sections


class AnalysisInputError(ValueError):
    """Raised when an analysis request cannot produce a trustworthy report."""


def _document_confidence(text: str, recognized_sections: int) -> float:
    line_count = len(meaningful_lines(text))
    confidence = 0.95

    if len(text) < 120 or line_count < 3:
        confidence -= 0.2
    if recognized_sections == 0:
        confidence -= 0.15

    return max(0.5, round(confidence, 2))


def _build_document_quality(
    resume_text: str,
    job_text: str,
    resume_sections_count: int,
    job_sections_count: int,
) -> DocumentQuality:
    warnings: list[str] = []

    if resume_sections_count == 0:
        warnings.append(
            "No standard resume section headings were detected. Evidence was analyzed from the available text."
        )
    if job_sections_count == 0:
        warnings.append(
            "No standard job-posting headings were detected. Requirement priorities may be less precise."
        )
    if len(resume_text) < 120:
        warnings.append("The resume text is short, so the report may miss relevant experience.")
    if len(job_text) < 120:
        warnings.append("The job description is short, so requirement priority may be incomplete.")

    return DocumentQuality(
        resume_extraction_confidence=_document_confidence(resume_text, resume_sections_count),
        job_extraction_confidence=_document_confidence(job_text, job_sections_count),
        warnings=warnings,
    )


def _unique_skills(
    assessments: list[RequirementAssessment],
    statuses: set[EvidenceStatus],
    minimum_weight: float,
    maximum_weight: float = 1.0,
) -> list[str]:
    return [
        assessment.skill
        for assessment in assessments
        if assessment.status in statuses
        and minimum_weight <= assessment.weight <= maximum_weight
    ]


def _build_recommendations(
    assessments: list[RequirementAssessment],
    hard_requirements_unclear: list[str],
) -> list[str]:
    recommendations: list[str] = []

    for assessment in assessments:
        if assessment.status == EvidenceStatus.MISSING and assessment.weight >= 0.75:
            recommendations.append(
                f"Prioritize gaining or clearly demonstrating {assessment.skill}; the posting treats it as a core or required capability."
            )
        elif assessment.status == EvidenceStatus.MENTIONED and assessment.weight >= 0.5:
            recommendations.append(
                f"Replace the bare {assessment.skill} mention with a project or experience bullet showing what you built, changed, or improved."
            )
        elif assessment.status == EvidenceStatus.IMPLIED and assessment.weight >= 0.5:
            recommendations.append(
                f"State {assessment.skill} directly and connect it to the existing evidence: “{assessment.resume_evidence[0]}”."
            )

        if len(recommendations) >= 5:
            break

    for requirement in hard_requirements_unclear:
        if len(recommendations) >= 5:
            break
        recommendations.append(
            f"Verify the hard constraint before applying because the resume does not establish it: {requirement}"
        )

    return recommendations


def analyze_smart_fit(resume_text: str, job_description: str) -> SmartFitAnalysisResponse:
    normalized_resume = normalize_document_text(resume_text)
    normalized_job = normalize_document_text(job_description)

    if len(normalized_resume) < 20:
        raise AnalysisInputError("Resume text is too short to support a reliable fit analysis.")
    if len(normalized_job) < 40:
        raise AnalysisInputError("Job description is too short to identify meaningful requirements.")

    resume_sections = parse_resume_sections(normalized_resume)
    job_sections = parse_job_sections(normalized_job)

    recognized_resume_sections = sum(
        section.kind != SectionKind.OTHER for section in resume_sections
    )
    recognized_job_sections = sum(
        section.kind != SectionKind.OTHER for section in job_sections
    )

    requirements = extract_job_requirements(job_sections)
    if not requirements:
        raise AnalysisInputError(
            "No recognizable technical requirements were found in the job description."
        )

    resume_evidence = extract_resume_evidence(resume_sections)
    requirement_assessments = assess_requirements(requirements, resume_evidence)
    hard_requirements = assess_hard_requirements(normalized_job, normalized_resume)

    document_quality = _build_document_quality(
        normalized_resume,
        normalized_job,
        recognized_resume_sections,
        recognized_job_sections,
    )
    requirement_confidence = mean(requirement.confidence for requirement in requirements)
    analysis_confidence = requirement_confidence * mean(
        [
            document_quality.resume_extraction_confidence,
            document_quality.job_extraction_confidence,
        ]
    )
    fit_summary = build_fit_summary(requirement_assessments, analysis_confidence)

    strong_matches = _unique_skills(
        requirement_assessments,
        {EvidenceStatus.DEMONSTRATED, EvidenceStatus.EXPLICIT},
        minimum_weight=0.5,
    )
    important_gaps = _unique_skills(
        requirement_assessments,
        {EvidenceStatus.MISSING},
        minimum_weight=0.75,
    )
    under_sold_experience = _unique_skills(
        requirement_assessments,
        {EvidenceStatus.MENTIONED, EvidenceStatus.IMPLIED},
        minimum_weight=0.5,
    )
    lower_priority_items = _unique_skills(
        requirement_assessments,
        {EvidenceStatus.MISSING},
        minimum_weight=0.0,
        maximum_weight=0.74,
    )

    unclear_hard_requirements = [
        requirement.requirement
        for requirement in hard_requirements
        if requirement.status.value == "unclear"
    ]
    recommendations = _build_recommendations(
        requirement_assessments,
        unclear_hard_requirements,
    )

    limitations = [
        "This score measures documented resume evidence against this posting; it is not a hiring probability or ATS score.",
        "Implied matches are intentionally conservative and should be rewritten as direct evidence when accurate.",
        "The current engine uses deterministic rules and a curated skill vocabulary; semantic and model-assisted extraction are planned next.",
    ]
    if fit_summary.band == FitBand.STRONG_ALIGNMENT and hard_requirements:
        limitations.append(
            "Strong technical alignment does not override unresolved citizenship, clearance, degree, authorization, travel, or experience constraints."
        )

    return SmartFitAnalysisResponse(
        fit_summary=fit_summary,
        document_quality=document_quality,
        hard_requirements=hard_requirements,
        requirement_assessments=requirement_assessments,
        strong_matches=strong_matches,
        important_gaps=important_gaps,
        under_sold_experience=under_sold_experience,
        lower_priority_items=lower_priority_items,
        recommendations=recommendations,
        limitations=limitations,
    )
