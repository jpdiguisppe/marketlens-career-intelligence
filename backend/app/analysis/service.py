from collections import defaultdict
from statistics import mean

from app.analysis.evidence import extract_resume_evidence
from app.analysis.model_extractor import (
    ModelAssistedExtraction,
    ModelAssistedExtractionError,
    ModelAssistedUnavailable,
    extract_model_assisted_signals,
)
from app.analysis.normalization import meaningful_lines, normalize_document_text
from app.analysis.requirements import assess_hard_requirements, extract_job_requirements
from app.analysis.schemas import (
    CategoryCoverage,
    CoachingAction,
    CoachingActionType,
    DocumentQuality,
    EvidenceStatus,
    FitBand,
    GapGroup,
    HardRequirementAssessment,
    HardRequirementStatus,
    JobRequirement,
    RequirementAssessment,
    RequirementType,
    ResumeEvidence,
    SectionKind,
    SmartFitAnalysisResponse,
)
from app.analysis.scoring import assess_requirements, build_fit_summary
from app.analysis.section_parser import parse_job_sections, parse_resume_sections
from app.analysis.skill_ontology import SKILL_CATEGORIES

MAX_COACHING_ACTIONS = 5

_GAP_GROUPS: tuple[tuple[str, str, set[str]], ...] = (
    (
        "Full-stack / .NET stack",
        "backend",
        {"Full-Stack Development", ".NET", "ASP.NET Core", "C#", "Entity Framework Core", "ORM"},
    ),
    (
        "Frontend web stack",
        "frontend",
        {"Responsive Web Apps", "React", "Angular", "JavaScript", "TypeScript", "HTML", "CSS", "Sass"},
    ),
    (
        "Architecture and design",
        "software_architecture",
        {"Software Architecture", "Service-Oriented Architecture", "Event-Driven Architecture", "OOP", "Design Patterns"},
    ),
    (
        "Backend and API evidence",
        "backend",
        {"Python", "Java", "Node.js", "FastAPI", "REST APIs", "Software Development Lifecycle", "Code Review"},
    ),
    (
        "Database evidence",
        "database",
        {"SQL", "PostgreSQL", "MySQL"},
    ),
    (
        "Cloud / DevOps evidence",
        "devops",
        {"Docker", "Kubernetes", "AWS", "Azure", "CI/CD"},
    ),
    (
        "Systems and automation",
        "systems",
        {"Linux", "Windows Server", "Scripting"},
    ),
)

_EVIDENCE_STRENGTH_BY_STATUS: dict[EvidenceStatus, float] = {
    EvidenceStatus.DEMONSTRATED: 1.0,
    EvidenceStatus.EXPLICIT: 0.8,
    EvidenceStatus.MENTIONED: 0.55,
    EvidenceStatus.IMPLIED: 0.4,
    EvidenceStatus.RELATED: 0.35,
    EvidenceStatus.MISSING: 0.0,
}


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


def _skill_category(skill: str | None) -> str | None:
    if skill is None:
        return None
    return SKILL_CATEGORIES.get(skill, "other")


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


def _sort_skills(skills: set[str]) -> list[str]:
    return sorted(skills, key=lambda skill: (SKILL_CATEGORIES.get(skill, "zz"), skill.lower()))


def _model_evidence_strength(status: EvidenceStatus, confidence: float) -> float:
    if status == EvidenceStatus.MISSING:
        status = EvidenceStatus.MENTIONED
    base_strength = _EVIDENCE_STRENGTH_BY_STATUS[status]
    confidence_multiplier = 0.75 + (min(max(confidence, 0.0), 1.0) * 0.25)
    return round(base_strength * confidence_multiplier, 2)


def _merge_requirement(existing: JobRequirement | None, candidate: JobRequirement) -> JobRequirement:
    if existing is None:
        return candidate
    if (candidate.weight, candidate.confidence) > (existing.weight, existing.confidence):
        return candidate
    return existing


def _merge_evidence(existing: ResumeEvidence | None, candidate: ResumeEvidence) -> ResumeEvidence:
    if existing is None:
        return candidate
    if candidate.strength > existing.strength:
        return candidate
    return existing


def _model_hard_requirements(extraction: ModelAssistedExtraction) -> list[HardRequirementAssessment]:
    return [
        HardRequirementAssessment(
            category=constraint.category,
            requirement=constraint.requirement,
            status=HardRequirementStatus.UNCLEAR,
            source_text=constraint.source_text,
            explanation=(
                "Model-assisted extraction found this possible hard constraint. "
                "MarketLens does not guess whether the candidate meets it."
            ),
        )
        for constraint in extraction.hard_constraints
    ]


def _merge_model_extraction(
    requirements: list[JobRequirement],
    resume_evidence: dict[str, ResumeEvidence],
    extraction: ModelAssistedExtraction,
) -> tuple[list[JobRequirement], dict[str, ResumeEvidence]]:
    requirements_by_skill = {requirement.skill: requirement for requirement in requirements}
    evidence_by_skill = dict(resume_evidence)

    for signal in extraction.job_requirements:
        skill = signal.skill.strip()
        if not skill:
            continue
        candidate = JobRequirement(
            skill=skill,
            requirement_type=signal.requirement_type,
            weight=signal.weight,
            source_text=signal.source_text,
            source_section=SectionKind.OTHER,
            confidence=signal.confidence,
        )
        requirements_by_skill[skill] = _merge_requirement(requirements_by_skill.get(skill), candidate)

    for skill in extraction.unknown_job_skills:
        cleaned_skill = skill.strip()
        if not cleaned_skill or cleaned_skill in requirements_by_skill:
            continue
        requirements_by_skill[cleaned_skill] = JobRequirement(
            skill=cleaned_skill,
            requirement_type=RequirementType.SUPPORTING_CONTEXT,
            weight=0.45,
            source_text="Model-assisted extraction detected this job skill, but it was not in the curated ontology.",
            source_section=SectionKind.OTHER,
            confidence=0.55,
        )

    for signal in extraction.resume_skills:
        skill = signal.name.strip()
        if not skill:
            continue
        status = signal.evidence_status
        if status == EvidenceStatus.MISSING:
            status = EvidenceStatus.MENTIONED
        candidate = ResumeEvidence(
            skill=skill,
            status=status,
            strength=_model_evidence_strength(status, signal.confidence),
            source_text=signal.source_text,
            source_section=SectionKind.OTHER,
            explanation=(
                "Model-assisted extraction identified this resume skill and classified its evidence context."
            ),
        )
        evidence_by_skill[skill] = _merge_evidence(evidence_by_skill.get(skill), candidate)

    for skill in extraction.unknown_resume_skills:
        cleaned_skill = skill.strip()
        if not cleaned_skill or cleaned_skill in evidence_by_skill:
            continue
        evidence_by_skill[cleaned_skill] = ResumeEvidence(
            skill=cleaned_skill,
            status=EvidenceStatus.MENTIONED,
            strength=0.45,
            source_text="Model-assisted extraction detected this resume skill, but it was not in the curated ontology.",
            source_section=SectionKind.OTHER,
            explanation=(
                "This skill was surfaced by model-assisted extraction as an unknown or uncategorized resume signal."
            ),
        )

    return list(requirements_by_skill.values()), evidence_by_skill


def _coverage_summary(
    category: str,
    score: int,
    strong_skills: list[str],
    weak_or_missing_skills: list[str],
) -> str:
    label = category.replace("_", " ")

    if score >= 80:
        return f"Strong {label} coverage, supported by {', '.join(strong_skills[:3])}."
    if score >= 60:
        if weak_or_missing_skills:
            return f"Credible {label} coverage, but {weak_or_missing_skills[0]} could be clearer or stronger."
        return f"Credible {label} coverage."
    if weak_or_missing_skills:
        return f"Weak {label} coverage; prioritize {weak_or_missing_skills[0]} if this category matters for the role."
    return f"Limited {label} evidence was found."


def _build_category_coverage(assessments: list[RequirementAssessment]) -> list[CategoryCoverage]:
    assessments_by_category: dict[str, list[RequirementAssessment]] = defaultdict(list)

    for assessment in assessments:
        category = SKILL_CATEGORIES.get(assessment.skill, "other")
        assessments_by_category[category].append(assessment)

    category_coverage: list[CategoryCoverage] = []
    for category, category_assessments in assessments_by_category.items():
        total_weight = sum(assessment.weight for assessment in category_assessments)
        weighted_strength = sum(
            assessment.weight * assessment.strength
            for assessment in category_assessments
        )
        score = round((weighted_strength / total_weight) * 100) if total_weight else 0
        strong_skills = sorted(
            {
                assessment.skill
                for assessment in category_assessments
                if assessment.status in {EvidenceStatus.DEMONSTRATED, EvidenceStatus.EXPLICIT}
            }
        )
        weak_or_missing_skills = sorted(
            {
                assessment.skill
                for assessment in category_assessments
                if assessment.status
                in {EvidenceStatus.MENTIONED, EvidenceStatus.IMPLIED, EvidenceStatus.RELATED, EvidenceStatus.MISSING}
            }
        )

        category_coverage.append(
            CategoryCoverage(
                category=category,
                score=score,
                priority_weight=round(total_weight, 2),
                strong_skills=strong_skills,
                weak_or_missing_skills=weak_or_missing_skills,
                summary=_coverage_summary(category, score, strong_skills, weak_or_missing_skills),
            )
        )

    return sorted(category_coverage, key=lambda item: (-item.priority_weight, item.category))


def _build_gap_groups(assessments: list[RequirementAssessment]) -> list[GapGroup]:
    missing_or_weak = [
        assessment
        for assessment in assessments
        if assessment.status in {EvidenceStatus.MISSING, EvidenceStatus.RELATED}
        and assessment.weight >= 0.5
    ]
    if not missing_or_weak:
        return []

    remaining_skills = {assessment.skill for assessment in missing_or_weak}
    assessment_by_skill = {assessment.skill: assessment for assessment in missing_or_weak}
    groups: list[GapGroup] = []

    for title, category, group_skills in _GAP_GROUPS:
        matched_skills = sorted(group_skills & remaining_skills)
        if not matched_skills:
            continue

        high_priority = any(assessment_by_skill[skill].weight >= 0.75 for skill in matched_skills)
        priority = "high" if high_priority else "medium"
        groups.append(
            GapGroup(
                title=title,
                category=category,
                priority=priority,
                skills=matched_skills[:8],
                summary=(
                    f"This posting asks for {', '.join(matched_skills[:4])}. "
                    "MarketLens found this as a resume-proof gap: add direct project, coursework, or work bullets only where accurate."
                ),
            )
        )
        remaining_skills -= set(matched_skills)

    for skill in sorted(remaining_skills):
        assessment = assessment_by_skill[skill]
        # Process terms are useful details, but should not become top-level coaching groups.
        if SKILL_CATEGORIES.get(skill) == "process":
            continue
        groups.append(
            GapGroup(
                title=f"{skill} evidence",
                category=_skill_category(skill) or "other",
                priority="high" if assessment.weight >= 0.75 else "medium",
                skills=[skill],
                summary=(
                    "This requirement appears in the posting, but the resume does not show direct proof for it yet. "
                    "That can mean either a real learning gap or simply an under-written resume."
                ),
            )
        )

    # Preserve product-priority order from _GAP_GROUPS so stack gaps stay above generic details.
    return groups[:4]


def _build_recommendations(
    assessments: list[RequirementAssessment],
    hard_requirements_unclear: list[str],
    gap_groups: list[GapGroup],
) -> list[str]:
    recommendations: list[str] = []

    for group in gap_groups[:2]:
        recommendations.append(
            f"Focus first on {group.title}: {', '.join(group.skills[:4])}. Add proof bullets if you already have the experience; otherwise treat it as a learning target."
        )

    for assessment in assessments:
        if assessment.status == EvidenceStatus.MENTIONED and assessment.weight >= 0.5:
            recommendations.append(
                f"Replace the bare {assessment.skill} mention with a project or experience bullet showing what you built, changed, tested, or improved."
            )
        elif assessment.status == EvidenceStatus.IMPLIED and assessment.weight >= 0.5:
            recommendations.append(
                f"State {assessment.skill} directly and connect it to the existing evidence: “{assessment.resume_evidence[0]}”."
            )
        elif assessment.status == EvidenceStatus.RELATED and assessment.weight >= 0.5:
            recommendations.append(
                f"Clarify the context for {assessment.skill}; the current evidence is related but not the same as the posting's requirement."
            )

        if len(recommendations) >= 5:
            break

    for requirement in hard_requirements_unclear:
        if len(recommendations) >= 5:
            break
        recommendations.append(
            f"Verify this hard constraint before applying: {requirement}"
        )

    return recommendations


def _add_action_once(actions: list[CoachingAction], action: CoachingAction) -> None:
    if len(actions) >= MAX_COACHING_ACTIONS:
        return

    existing_keys = {
        (existing.action_type, existing.skill, existing.category, existing.title)
        for existing in actions
    }
    key = (action.action_type, action.skill, action.category, action.title)
    if key not in existing_keys:
        actions.append(action)


def _top_skills_by_status(
    assessments: list[RequirementAssessment],
    statuses: set[EvidenceStatus],
    minimum_weight: float = 0.5,
    limit: int = 4,
) -> list[str]:
    return [
        assessment.skill
        for assessment in sorted(
            assessments,
            key=lambda item: (-item.weight, item.skill.lower()),
        )
        if assessment.status in statuses and assessment.weight >= minimum_weight
    ][:limit]


def _resume_positioning_action(assessments: list[RequirementAssessment]) -> CoachingAction | None:
    proven = _top_skills_by_status(
        assessments,
        {EvidenceStatus.DEMONSTRATED, EvidenceStatus.EXPLICIT},
        minimum_weight=0.5,
    )
    weak = _top_skills_by_status(
        assessments,
        {EvidenceStatus.MENTIONED, EvidenceStatus.IMPLIED, EvidenceStatus.RELATED},
        minimum_weight=0.5,
    )
    missing = _top_skills_by_status(
        assessments,
        {EvidenceStatus.MISSING},
        minimum_weight=0.75,
    )

    if not (proven or weak or missing):
        return None

    advice_parts: list[str] = []
    if proven:
        advice_parts.append(f"Already proven: {', '.join(proven)}.")
    if weak:
        advice_parts.append(f"Under-written or weakly proven: {', '.join(weak)}.")
    if missing:
        advice_parts.append(f"Missing proof for this posting: {', '.join(missing)}.")
    advice_parts.append(
        "Treat the percentage as documented resume evidence, not your actual ability. The fastest improvement is adding concrete project bullets with tools, actions, and outcomes."
    )

    return CoachingAction(
        action_type=CoachingActionType.RESUME_REWRITE,
        priority="high" if missing or weak else "medium",
        title="Turn background into resume proof",
        category="resume_positioning",
        advice=" ".join(advice_parts),
    )


def _gap_group_action(group: GapGroup) -> CoachingAction:
    return CoachingAction(
        action_type=CoachingActionType.LEARNING_FOCUS,
        priority=group.priority,
        title=group.title,
        category=group.category,
        advice=group.summary,
    )


def _rewrite_action(assessment: RequirementAssessment) -> CoachingAction:
    return CoachingAction(
        action_type=CoachingActionType.RESUME_REWRITE,
        priority="medium",
        title=f"Make {assessment.skill} evidence more explicit",
        skill=assessment.skill,
        category=_skill_category(assessment.skill),
        source_evidence=assessment.resume_evidence,
        job_evidence=assessment.job_evidence,
        advice=(
            f"The resume has some signal for {assessment.skill}, but it is under-explained. "
            "Rewrite the bullet to name the skill directly and describe what was built, improved, deployed, or tested. "
            "A strong bullet should look like: used [skill/tool] to build [thing] that achieved [result]."
        ),
    )


def _related_action(assessment: RequirementAssessment) -> CoachingAction:
    return CoachingAction(
        action_type=CoachingActionType.RESUME_REWRITE,
        priority="medium",
        title=f"Clarify the context for {assessment.skill}",
        skill=assessment.skill,
        category=_skill_category(assessment.skill),
        source_evidence=assessment.resume_evidence,
        job_evidence=assessment.job_evidence,
        advice=(
            f"The resume has related {assessment.skill} evidence, but the job asks for a different use context. "
            "Add wording only if you have direct experience in that context; otherwise leave it as a learning gap instead of stretching the truth."
        ),
    )


def _missing_proof_action(assessment: RequirementAssessment) -> CoachingAction:
    return CoachingAction(
        action_type=CoachingActionType.RESUME_REWRITE,
        priority="high",
        title=f"Add proof for {assessment.skill} if accurate",
        skill=assessment.skill,
        category=_skill_category(assessment.skill),
        job_evidence=assessment.job_evidence,
        advice=(
            f"The posting asks for {assessment.skill}, but the current resume does not document it. "
            "If you already used it in a class, project, internship, or personal build, add a concrete bullet. "
            "If not, treat it as a real skill gap before applying."
        ),
    )


def _hard_requirement_action(requirement: str) -> CoachingAction:
    return CoachingAction(
        action_type=CoachingActionType.HARD_REQUIREMENT_CHECK,
        priority="high",
        title="Verify hard requirement before applying",
        source_evidence=[],
        job_evidence=requirement,
        advice=(
            "This is a non-skill constraint, so MarketLens will not guess from missing resume text. "
            "Confirm it separately before treating the role as a strong fit."
        ),
    )


def _build_coaching_actions(
    assessments: list[RequirementAssessment],
    hard_requirements_unclear: list[str],
    gap_groups: list[GapGroup],
) -> list[CoachingAction]:
    actions: list[CoachingAction] = []

    positioning_action = _resume_positioning_action(assessments)
    if positioning_action:
        _add_action_once(actions, positioning_action)

    for group in gap_groups[:2]:
        _add_action_once(actions, _gap_group_action(group))

    for requirement in hard_requirements_unclear:
        _add_action_once(actions, _hard_requirement_action(requirement))

    for assessment in sorted(assessments, key=lambda item: (-item.weight, item.skill.lower())):
        if assessment.status in {EvidenceStatus.MENTIONED, EvidenceStatus.IMPLIED} and assessment.weight >= 0.5:
            _add_action_once(actions, _rewrite_action(assessment))
        elif assessment.status == EvidenceStatus.RELATED and assessment.weight >= 0.5:
            _add_action_once(actions, _related_action(assessment))
        elif assessment.status == EvidenceStatus.MISSING and assessment.weight >= 0.75:
            _add_action_once(actions, _missing_proof_action(assessment))

    return actions


def _build_report_summary(
    fit_band: FitBand,
    fit_score: int,
    gap_groups: list[GapGroup],
    job_relevant_resume_skills: list[str],
    other_resume_skills: list[str],
    strong_matches: list[str],
    under_sold_experience: list[str],
    important_gaps: list[str],
    hard_requirements_unclear: list[str],
) -> list[str]:
    summary: list[str] = []

    if fit_band == FitBand.LIMITED_ALIGNMENT:
        summary.append(
            f"Resume-proof score: {fit_score}%. MarketLens found limited documented evidence for this exact posting, not limited overall ability."
        )
    elif fit_band == FitBand.PARTIAL_ALIGNMENT:
        summary.append(
            f"Resume-proof score: {fit_score}%. The resume shows useful signal, but several important requirements are weakly proven or absent."
        )
    elif fit_band == FitBand.CREDIBLE_ALIGNMENT:
        summary.append(
            f"Resume-proof score: {fit_score}%. The resume covers several important requirements, with a few areas to clarify or strengthen."
        )
    else:
        summary.append(
            f"Resume-proof score: {fit_score}%. The resume demonstrates most of the posting's high-priority requirements."
        )

    if strong_matches:
        summary.append(
            f"Already proven for this role: {', '.join(strong_matches[:4])}."
        )
    if under_sold_experience:
        summary.append(
            f"Under-sold experience: {', '.join(under_sold_experience[:4])}. These should become stronger bullets if accurate."
        )
    if important_gaps:
        summary.append(
            f"Missing proof for high-priority requirements: {', '.join(important_gaps[:4])}."
        )
    elif gap_groups:
        top_group = gap_groups[0]
        summary.append(
            f"Main proof gap group: {top_group.title} ({', '.join(top_group.skills[:4])})."
        )
    if job_relevant_resume_skills and not strong_matches:
        summary.append(
            f"Relevant resume signal found: {', '.join(job_relevant_resume_skills[:4])}."
        )
    if other_resume_skills:
        summary.append(
            f"Other valid resume skills detected but not central to this role: {', '.join(other_resume_skills[:5])}."
        )
    if hard_requirements_unclear:
        summary.append("Hard constraints need separate review before treating this as a true fit.")

    return summary[:5]


def analyze_smart_fit(
    resume_text: str,
    job_description: str,
    use_model_assisted: bool = False,
) -> SmartFitAnalysisResponse:
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
    resume_evidence = extract_resume_evidence(resume_sections)
    hard_requirements = assess_hard_requirements(normalized_job, normalized_resume)
    analysis_engine = "deterministic"
    model_assisted_status = "not_requested"
    model_uncertainty_notes: list[str] = []

    if use_model_assisted:
        try:
            model_extraction = extract_model_assisted_signals(normalized_resume, normalized_job)
            requirements, resume_evidence = _merge_model_extraction(
                requirements,
                resume_evidence,
                model_extraction,
            )
            hard_requirements.extend(_model_hard_requirements(model_extraction))
            model_uncertainty_notes = model_extraction.uncertainty_notes
            analysis_engine = "model_assisted"
            model_assisted_status = "used"
        except ModelAssistedUnavailable as exc:
            model_assisted_status = f"fallback_unavailable: {exc}"
        except ModelAssistedExtractionError:
            model_assisted_status = "fallback_failed: model-assisted extraction could not produce a valid structured result."

    if not requirements:
        raise AnalysisInputError(
            "No recognizable technical requirements were found in the job description."
        )

    requirement_assessments = assess_requirements(requirements, resume_evidence)

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

    category_coverage = _build_category_coverage(requirement_assessments)
    strong_matches = _unique_skills(
        requirement_assessments,
        {EvidenceStatus.DEMONSTRATED, EvidenceStatus.EXPLICIT},
        minimum_weight=0.5,
    )
    related_matches = _unique_skills(
        requirement_assessments,
        {EvidenceStatus.RELATED},
        minimum_weight=0.0,
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

    matched_or_partial_statuses = {
        EvidenceStatus.DEMONSTRATED,
        EvidenceStatus.EXPLICIT,
        EvidenceStatus.MENTIONED,
        EvidenceStatus.IMPLIED,
        EvidenceStatus.RELATED,
    }
    job_relevant_resume_skills = _sort_skills(
        {
            assessment.skill
            for assessment in requirement_assessments
            if assessment.status in matched_or_partial_statuses
        }
    )
    resume_skills_found = _sort_skills(set(resume_evidence))
    other_resume_skills = _sort_skills(set(resume_evidence) - set(job_relevant_resume_skills))

    unclear_hard_requirements = [
        requirement.requirement
        for requirement in hard_requirements
        if requirement.status.value == "unclear"
    ]
    gap_groups = _build_gap_groups(requirement_assessments)
    recommendations = _build_recommendations(
        requirement_assessments,
        unclear_hard_requirements,
        gap_groups,
    )
    coaching_actions = _build_coaching_actions(
        requirement_assessments,
        unclear_hard_requirements,
        gap_groups,
    )
    report_summary = _build_report_summary(
        fit_summary.band,
        fit_summary.score,
        gap_groups,
        job_relevant_resume_skills,
        other_resume_skills,
        strong_matches,
        under_sold_experience,
        important_gaps,
        unclear_hard_requirements,
    )

    limitations = [
        "Requirement Coverage measures documented resume evidence against this posting; it is not a hiring probability, ATS score, or measure of actual ability.",
        "A low score can mean the resume undersells relevant work, not that the candidate lacks the ability to learn or perform the role.",
        "Related matches mean the resume shows adjacent evidence, not a clean match for the exact job context.",
        "Implied matches are intentionally conservative and should be rewritten as direct evidence when accurate.",
        "Model-assisted extraction is optional, backend-gated, schema-validated, and falls back to deterministic rules when unavailable.",
    ]
    if model_uncertainty_notes:
        limitations.append(f"Model uncertainty note: {model_uncertainty_notes[0]}")
    if fit_summary.band == FitBand.STRONG_ALIGNMENT and hard_requirements:
        limitations.append(
            "Strong technical alignment does not override unresolved citizenship, clearance, degree, authorization, travel, or experience constraints."
        )

    return SmartFitAnalysisResponse(
        fit_summary=fit_summary,
        document_quality=document_quality,
        hard_requirements=hard_requirements,
        requirement_assessments=requirement_assessments,
        category_coverage=category_coverage,
        coaching_actions=coaching_actions,
        report_summary=report_summary,
        gap_groups=gap_groups,
        resume_skills_found=resume_skills_found,
        job_relevant_resume_skills=job_relevant_resume_skills,
        other_resume_skills=other_resume_skills,
        strong_matches=strong_matches,
        related_matches=related_matches,
        important_gaps=important_gaps,
        under_sold_experience=under_sold_experience,
        lower_priority_items=lower_priority_items,
        recommendations=recommendations,
        limitations=limitations,
        analysis_engine=analysis_engine,
        model_assisted_status=model_assisted_status,
    )
