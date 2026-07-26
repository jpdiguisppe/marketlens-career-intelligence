"""Evidence provenance and grounding enforcement for Smart Fit.

Milestone 8C keeps the existing response fields intact while adding auditable
citations. A conclusion is never allowed to score from a job or resume quote
that cannot be verified against the current request text.
"""

from __future__ import annotations

import re
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Callable

from app.analysis.normalization import normalize_document_text
from app.analysis.schemas import (
    DocumentKind,
    EvidenceCitation,
    EvidenceStatus,
    HardRequirementAssessment,
    HardRequirementStatus,
    JobRequirement,
    ProvenanceSource,
    RequirementAssessment,
    ResumeEvidence,
    SmartFitAnalysisResponse,
)

_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class _AnalysisDocuments:
    resume_text: str
    job_description: str


_CURRENT_DOCUMENTS: ContextVar[_AnalysisDocuments | None] = ContextVar(
    "marketlens_analysis_documents",
    default=None,
)
_INSTALLED = False


def _normalized_source(value: str) -> str:
    return _WHITESPACE.sub(" ", value.strip().strip('"\'`-• ')).casefold()


def quote_is_grounded(quote: str, document_text: str) -> bool:
    """Return whether a quoted span appears in the current normalized document."""

    source = _normalized_source(quote)
    document = _normalized_source(document_text)
    return len(source) >= 2 and source in document


def _combined_source(
    requirement_source: ProvenanceSource,
    evidence_source: ProvenanceSource | None,
) -> ProvenanceSource:
    if evidence_source is None:
        return requirement_source
    if ProvenanceSource.MERGED in {requirement_source, evidence_source}:
        return ProvenanceSource.MERGED
    if requirement_source != evidence_source:
        return ProvenanceSource.MERGED
    return requirement_source


def _citation_for_requirement(
    requirement: JobRequirement,
    *,
    grounded: bool,
) -> EvidenceCitation:
    return EvidenceCitation(
        document_kind=DocumentKind.JOB_POSTING,
        source=requirement.source_origin,
        quote=requirement.source_text,
        section=requirement.source_section,
        grounded=grounded,
    )


def _citation_for_resume(
    evidence: ResumeEvidence,
    *,
    grounded: bool,
) -> EvidenceCitation:
    return EvidenceCitation(
        document_kind=DocumentKind.RESUME,
        source=evidence.source_origin,
        quote=evidence.source_text,
        section=evidence.source_section,
        grounded=grounded,
    )


def _grounded_assessments(
    requirements: list[JobRequirement],
    resume_evidence: dict[str, ResumeEvidence],
    original_assess_requirements: Callable[
        [list[JobRequirement], dict[str, ResumeEvidence]],
        list[RequirementAssessment],
    ],
) -> list[RequirementAssessment]:
    assessments = original_assess_requirements(requirements, resume_evidence)
    documents = _CURRENT_DOCUMENTS.get()
    if documents is None:
        return assessments

    grounded_assessments: list[RequirementAssessment] = []
    for requirement, assessment in zip(requirements, assessments, strict=True):
        evidence = resume_evidence.get(requirement.skill)
        job_grounded = quote_is_grounded(
            requirement.source_text,
            documents.job_description,
        )
        resume_grounded = (
            quote_is_grounded(evidence.source_text, documents.resume_text)
            if evidence is not None
            else True
        )
        job_citation = _citation_for_requirement(
            requirement,
            grounded=job_grounded,
        )
        resume_citations = (
            [_citation_for_resume(evidence, grounded=resume_grounded)]
            if evidence is not None
            else []
        )
        conclusion_source = _combined_source(
            requirement.source_origin,
            evidence.source_origin if evidence is not None else None,
        )

        if not job_grounded:
            grounded_assessments.append(
                assessment.model_copy(
                    update={
                        "weight": 0.0,
                        "status": EvidenceStatus.MISSING,
                        "strength": 0.0,
                        "resume_evidence": [],
                        "explanation": (
                            "MarketLens excluded this conclusion from scoring because "
                            "the quoted job requirement could not be verified against "
                            "the current job description."
                        ),
                        "job_provenance": job_citation,
                        "resume_provenance": resume_citations,
                        "conclusion_source": conclusion_source,
                        "grounded": False,
                    }
                )
            )
            continue

        if evidence is not None and not resume_grounded:
            grounded_assessments.append(
                assessment.model_copy(
                    update={
                        "status": EvidenceStatus.MISSING,
                        "strength": 0.0,
                        "resume_evidence": [],
                        "explanation": (
                            "The job requirement is grounded, but the proposed resume "
                            "quote could not be verified against the current resume. "
                            "MarketLens therefore downgraded this to missing proof."
                        ),
                        "job_provenance": job_citation,
                        "resume_provenance": resume_citations,
                        "conclusion_source": conclusion_source,
                        "grounded": False,
                    }
                )
            )
            continue

        source_label = conclusion_source.value.replace("_", " ")
        if assessment.status == EvidenceStatus.MISSING:
            explanation = (
                f"No reliable resume evidence was found for this requirement. "
                f"Verified job evidence: “{requirement.source_text}”. "
                f"Conclusion source: {source_label}."
            )
        else:
            explanation = (
                f"{assessment.explanation} Verified job evidence: "
                f"“{requirement.source_text}”. Conclusion source: {source_label}."
            )

        grounded_assessments.append(
            assessment.model_copy(
                update={
                    "explanation": explanation,
                    "job_provenance": job_citation,
                    "resume_provenance": resume_citations,
                    "conclusion_source": conclusion_source,
                    "grounded": True,
                }
            )
        )

    return grounded_assessments


def _ground_hard_requirements(
    requirements: list[HardRequirementAssessment],
    job_description: str,
) -> list[HardRequirementAssessment]:
    grounded_requirements: list[HardRequirementAssessment] = []
    for requirement in requirements:
        grounded = quote_is_grounded(requirement.source_text, job_description)
        if grounded:
            grounded_requirements.append(
                requirement.model_copy(update={"grounded": True})
            )
            continue

        grounded_requirements.append(
            requirement.model_copy(
                update={
                    "status": HardRequirementStatus.UNCLEAR,
                    "grounded": False,
                    "explanation": (
                        "MarketLens could not verify this quoted hard constraint "
                        "against the current job description, so it was not treated "
                        "as a confirmed requirement."
                    ),
                }
            )
        )
    return grounded_requirements


def _attach_gap_evidence(
    analysis: SmartFitAnalysisResponse,
) -> list:
    assessments_by_skill = {
        assessment.skill: assessment
        for assessment in analysis.requirement_assessments
    }
    updated_groups = []
    for group in analysis.gap_groups:
        quotes: list[str] = []
        for skill in group.skills:
            assessment = assessments_by_skill.get(skill)
            if (
                assessment is not None
                and assessment.job_provenance is not None
                and assessment.job_provenance.grounded
                and assessment.job_evidence not in quotes
            ):
                quotes.append(assessment.job_evidence)

        summary = group.summary
        if quotes and "Posting evidence:" not in summary:
            summary = f"{summary} Posting evidence: “{quotes[0]}”."
        updated_groups.append(
            group.model_copy(
                update={
                    "job_evidence": quotes,
                    "summary": summary,
                }
            )
        )
    return updated_groups


def install_provenance_patch() -> None:
    """Install request-scoped grounding around the existing analysis service."""

    global _INSTALLED
    if _INSTALLED:
        return

    import app.analysis.service as service

    original_assess_requirements = service.assess_requirements
    original_analyze_smart_fit = service.analyze_smart_fit
    original_model_hard_requirements = service._model_hard_requirements

    def assess_requirements_with_provenance(
        requirements: list[JobRequirement],
        resume_evidence: dict[str, ResumeEvidence],
    ) -> list[RequirementAssessment]:
        return _grounded_assessments(
            requirements,
            resume_evidence,
            original_assess_requirements,
        )

    def model_hard_requirements_with_provenance(extraction):
        return [
            requirement.model_copy(
                update={"source_origin": ProvenanceSource.MODEL_ASSISTED}
            )
            for requirement in original_model_hard_requirements(extraction)
        ]

    def analyze_smart_fit_with_provenance(
        resume_text: str,
        job_description: str,
        use_model_assisted: bool = False,
    ) -> SmartFitAnalysisResponse:
        documents = _AnalysisDocuments(
            resume_text=normalize_document_text(resume_text),
            job_description=normalize_document_text(job_description),
        )
        token = _CURRENT_DOCUMENTS.set(documents)
        try:
            analysis = original_analyze_smart_fit(
                resume_text=resume_text,
                job_description=job_description,
                use_model_assisted=use_model_assisted,
            )
        finally:
            _CURRENT_DOCUMENTS.reset(token)

        hard_requirements = _ground_hard_requirements(
            analysis.hard_requirements,
            documents.job_description,
        )
        grounding_warnings = [
            f"Excluded ungrounded requirement conclusion: {assessment.skill}"
            for assessment in analysis.requirement_assessments
            if not assessment.grounded
        ]
        grounding_warnings.extend(
            f"Unverified hard requirement: {requirement.category}"
            for requirement in hard_requirements
            if not requirement.grounded
        )

        limitations = list(analysis.limitations)
        provenance_note = (
            "Every scored requirement includes request-time job provenance; "
            "non-missing matches also require grounded resume provenance."
        )
        if provenance_note not in limitations:
            limitations.append(provenance_note)

        return analysis.model_copy(
            update={
                "hard_requirements": hard_requirements,
                "gap_groups": _attach_gap_evidence(analysis),
                "grounding_warnings": grounding_warnings,
                "limitations": limitations,
            }
        )

    service.assess_requirements = assess_requirements_with_provenance
    service._model_hard_requirements = model_hard_requirements_with_provenance
    service.analyze_smart_fit = analyze_smart_fit_with_provenance
    _INSTALLED = True


__all__ = ["install_provenance_patch", "quote_is_grounded"]
