"""Stability wrapper for role-aware Smart Fit output.

This keeps the Milestone 3 role/capability layer from accidentally hiding the
original evidence-backed requirement gaps that older evaluation cases expect.
It also gives non-pure-technical roles a conservative capability-only report
when the base skill extractor cannot find exact technical requirements.
"""

from app.analysis.role_aware import (
    _alignment_context,
    _capability_coaching_actions,
    _capability_gaps,
    _capability_summary,
    analyze_smart_fit as _role_aware_analyze_smart_fit,
)
from app.analysis.schemas import (
    CategoryCoverage,
    DocumentQuality,
    EvidenceStatus,
    FitBand,
    FitSummary,
    SmartFitAnalysisResponse,
)
from app.analysis.service import AnalysisInputError

_GAP_STATUSES = {
    EvidenceStatus.MISSING,
    EvidenceStatus.RELATED,
    EvidenceStatus.MENTIONED,
    EvidenceStatus.IMPLIED,
}

_CAPABILITY_ONLY_WARNING = (
    "MarketLens found role-capability signals, but the posting did not expose "
    "enough exact skill/tool requirements for a full evidence-backed score. "
    "Treat this as conservative role-context guidance."
)


def _with_preserved_requirement_gaps(analysis: SmartFitAnalysisResponse) -> list[str]:
    """Merge capability gaps with exact high-priority requirement gaps.

    The role-aware layer adds broad capability gaps such as security operations
    or data pipelines. Those should improve ranking explanations, but they
    should not push out concrete missing requirements like TypeScript, C#, or
    Full-Stack Development.
    """

    ordered_gaps = list(analysis.important_gaps)

    for assessment in analysis.requirement_assessments:
        if assessment.weight < 0.5:
            continue
        if assessment.status not in _GAP_STATUSES:
            continue
        ordered_gaps.append(assessment.skill)

    deduped: list[str] = []
    seen: set[str] = set()
    for gap in ordered_gaps:
        key = gap.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(gap)

    return deduped


def _capability_category_coverage(capability_gaps):
    coverage: list[CategoryCoverage] = []
    seen_categories: set[str] = set()

    for gap in capability_gaps:
        if gap.category in seen_categories:
            continue
        seen_categories.add(gap.category)
        coverage.append(
            CategoryCoverage(
                category=gap.category,
                score=0,
                priority_weight=1.0,
                strong_skills=[],
                weak_or_missing_skills=gap.skills,
                summary=gap.summary,
            )
        )

    return coverage


def _capability_only_analysis(
    resume_text: str,
    job_description: str,
    use_model_assisted: bool,
    original_error: AnalysisInputError,
) -> SmartFitAnalysisResponse:
    role_context = _alignment_context(resume_text, job_description)
    capability_gaps = _capability_gaps(
        role_context,
        resume_text,
        job_description,
        existing_gap_groups=[],
    )

    if not capability_gaps:
        raise original_error

    report_summary = [
        role_context.note,
        "Exact requirement extraction: the posting did not expose enough recognized skill/tool requirements for the normal Smart Fit scorer.",
    ]
    capability_note = _capability_summary(capability_gaps)
    if capability_note:
        report_summary.append(capability_note)

    confidence = min(role_context.confidence_cap or 0.55, 0.55)
    return SmartFitAnalysisResponse(
        fit_summary=FitSummary(
            score=10,
            band=FitBand.LIMITED_ALIGNMENT,
            confidence=round(confidence, 2),
            headline=(
                "MarketLens produced a capability-only role-aware report because exact requirement extraction was low-signal."
            ),
        ),
        document_quality=DocumentQuality(
            resume_extraction_confidence=0.7,
            job_extraction_confidence=0.45,
            warnings=[_CAPABILITY_ONLY_WARNING],
        ),
        hard_requirements=[],
        requirement_assessments=[],
        category_coverage=_capability_category_coverage(capability_gaps),
        coaching_actions=_capability_coaching_actions(capability_gaps),
        report_summary=report_summary[:8],
        gap_groups=capability_gaps,
        resume_skills_found=[],
        job_relevant_resume_skills=[],
        other_resume_skills=[],
        strong_matches=[],
        related_matches=[],
        important_gaps=[gap.title for gap in capability_gaps],
        under_sold_experience=[],
        lower_priority_items=[],
        recommendations=[],
        limitations=[
            "This capability-only report is generated only when exact requirement extraction cannot support a normal evidence-backed Smart Fit score.",
            "Capability gaps are directional coaching signals, not proof that a candidate cannot do the role.",
        ],
        analysis_engine="deterministic",
        model_assisted_status="not_requested" if not use_model_assisted else "fallback_capability_only",
    )


def analyze_smart_fit(
    resume_text: str,
    job_description: str,
    use_model_assisted: bool = False,
) -> SmartFitAnalysisResponse:
    try:
        analysis = _role_aware_analyze_smart_fit(
            resume_text=resume_text,
            job_description=job_description,
            use_model_assisted=use_model_assisted,
        )
    except AnalysisInputError as exc:
        analysis = _capability_only_analysis(
            resume_text=resume_text,
            job_description=job_description,
            use_model_assisted=use_model_assisted,
            original_error=exc,
        )

    return analysis.model_copy(
        update={"important_gaps": _with_preserved_requirement_gaps(analysis)}
    )