"""Stability wrapper for role-aware Smart Fit output.

This keeps the Milestone 3 role/capability layer from accidentally hiding the
original evidence-backed requirement gaps that older evaluation cases expect.
"""

from app.analysis.role_aware import analyze_smart_fit as _role_aware_analyze_smart_fit
from app.analysis.schemas import EvidenceStatus, SmartFitAnalysisResponse

_GAP_STATUSES = {
    EvidenceStatus.MISSING,
    EvidenceStatus.RELATED,
    EvidenceStatus.MENTIONED,
    EvidenceStatus.IMPLIED,
}


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


def analyze_smart_fit(
    resume_text: str,
    job_description: str,
    use_model_assisted: bool = False,
) -> SmartFitAnalysisResponse:
    analysis = _role_aware_analyze_smart_fit(
        resume_text=resume_text,
        job_description=job_description,
        use_model_assisted=use_model_assisted,
    )

    return analysis.model_copy(
        update={"important_gaps": _with_preserved_requirement_gaps(analysis)}
    )
