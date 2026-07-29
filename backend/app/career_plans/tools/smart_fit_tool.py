from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.analysis import AnalysisInputError, SmartFitAnalysisResponse, analyze_smart_fit
from app.career_plans.tools.job_search_tool import CareerPlanSearchCandidate

SMART_FIT_TOOL_NAME = "career.smart_fit_batch.v1"


class CareerPlanSmartFitToolError(RuntimeError):
    def __init__(self, safe_code: str, message: str) -> None:
        super().__init__(message)
        self.safe_code = safe_code


@dataclass(frozen=True)
class CareerPlanSmartFitResult:
    candidate: CareerPlanSearchCandidate
    rank: int
    analysis: SmartFitAnalysisResponse
    safe_summary: dict[str, Any]


@dataclass(frozen=True)
class CareerPlanSmartFitToolOutput:
    results: list[CareerPlanSmartFitResult]
    safe_summary: dict[str, Any]
    safe_status_code: str


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized[:70] or "item"


def _safe_evidence_refs(
    candidate: CareerPlanSearchCandidate,
    analysis: SmartFitAnalysisResponse,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for assessment in analysis.requirement_assessments[:60]:
        status = _enum_value(assessment.status)
        source_section = None
        if assessment.resume_provenance:
            source_section = _enum_value(assessment.resume_provenance[0].section)
        refs.append(
            {
                "id": f"ev-{candidate.job_ref}-{_slug(assessment.skill)}",
                "kind": "resume_evidence" if status != "missing" else "job_requirement",
                "job_ref": candidate.job_ref,
                "capability": assessment.skill,
                "assessment_status": status,
                "source_section": source_section,
                "source_origin": _enum_value(assessment.conclusion_source),
                "smart_fit_schema_version": analysis.provenance_version,
                "analysis_ref": f"smart-fit/{candidate.job_ref}/requirements/{_slug(assessment.skill)}",
                "summary": (
                    f"{assessment.skill} is assessed as {status.replace('_', ' ')} for this opportunity."
                )[:240],
            }
        )
    return refs


def _safe_result_summary(
    candidate: CareerPlanSearchCandidate,
    rank: int,
    analysis: SmartFitAnalysisResponse,
) -> dict[str, Any]:
    return {
        **candidate.safe_metadata(),
        "rank": rank,
        "fit_summary": {
            "score": analysis.fit_summary.score,
            "band": _enum_value(analysis.fit_summary.band),
            "confidence": analysis.fit_summary.confidence,
            "headline": analysis.fit_summary.headline[:255],
        },
        "hard_requirements": [
            {
                "category": item.category[:120],
                "status": _enum_value(item.status),
                "grounded": item.grounded,
                "source_origin": _enum_value(item.source_origin),
            }
            for item in analysis.hard_requirements[:30]
        ],
        "requirement_assessments": [
            {
                "skill": item.skill[:255],
                "requirement_type": _enum_value(item.requirement_type),
                "status": _enum_value(item.status),
                "strength": item.strength,
                "grounded": item.grounded,
                "conclusion_source": _enum_value(item.conclusion_source),
            }
            for item in analysis.requirement_assessments[:60]
        ],
        "category_coverage": [
            {
                "category": item.category[:255],
                "score": item.score,
                "priority_weight": item.priority_weight,
                "strong_skills": item.strong_skills[:20],
                "weak_or_missing_skills": item.weak_or_missing_skills[:20],
                "summary": item.summary[:500],
            }
            for item in analysis.category_coverage[:30]
        ],
        "strong_matches": analysis.strong_matches[:50],
        "related_matches": analysis.related_matches[:50],
        "important_gaps": analysis.important_gaps[:50],
        "under_sold_experience": analysis.under_sold_experience[:30],
        "coaching_actions": [
            {
                "action_type": _enum_value(item.action_type),
                "priority": item.priority[:20],
                "title": item.title[:255],
                "skill": item.skill[:255] if item.skill else None,
                "category": item.category[:255] if item.category else None,
            }
            for item in analysis.coaching_actions[:30]
        ],
        "limitations": analysis.limitations[:30],
        "grounding_warnings": analysis.grounding_warnings[:20],
        "analysis_engine": analysis.analysis_engine,
        "model_assisted_status": analysis.model_assisted_status,
        "provenance_version": analysis.provenance_version,
        "coaching_engine": analysis.coaching_engine,
        "coaching_status": analysis.coaching_status,
        "coaching_version": analysis.coaching_version,
        "evidence_refs": _safe_evidence_refs(candidate, analysis),
    }


def run_smart_fit_tool(
    resume_text: str,
    candidates: list[CareerPlanSearchCandidate],
) -> CareerPlanSmartFitToolOutput:
    if not candidates:
        return CareerPlanSmartFitToolOutput(
            results=[],
            safe_summary={
                "tool_name": SMART_FIT_TOOL_NAME,
                "analyzed_count": 0,
                "results": [],
                "safe_status_code": "ok",
            },
            safe_status_code="ok",
        )

    analyzed: list[tuple[CareerPlanSearchCandidate, SmartFitAnalysisResponse]] = []
    for candidate in candidates:
        try:
            analysis = analyze_smart_fit(
                resume_text=resume_text,
                job_description=candidate.job.description,
                use_model_assisted=False,
            )
        except AnalysisInputError as exc:
            raise CareerPlanSmartFitToolError(
                "smart_fit_invalid_input",
                f"Smart Fit could not analyze {candidate.job_ref}.",
            ) from exc
        except Exception as exc:
            raise CareerPlanSmartFitToolError(
                "smart_fit_failure",
                f"Smart Fit failed for {candidate.job_ref}.",
            ) from exc
        analyzed.append((candidate, analysis))

    ranked = sorted(
        analyzed,
        key=lambda item: (
            -item[1].fit_summary.score,
            -item[1].fit_summary.confidence,
            item[0].search_rank,
            item[0].job_ref,
        ),
    )
    results = [
        CareerPlanSmartFitResult(
            candidate=candidate,
            rank=index,
            analysis=analysis,
            safe_summary=_safe_result_summary(candidate, index, analysis),
        )
        for index, (candidate, analysis) in enumerate(ranked, start=1)
    ]
    return CareerPlanSmartFitToolOutput(
        results=results,
        safe_summary={
            "tool_name": SMART_FIT_TOOL_NAME,
            "analyzed_count": len(results),
            "results": [result.safe_summary for result in results],
            "safe_status_code": "ok",
        },
        safe_status_code="ok",
    )
