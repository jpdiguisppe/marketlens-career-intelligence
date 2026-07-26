"""Conservative merge rules for versioned model-assisted extraction.

The model may improve semantic recall, but deterministic evidence remains the
authoritative source for resume-proof strength and scoring boundaries.
"""

from __future__ import annotations

import re

import app.analysis.service as _service
from app.analysis.model_extractor import (
    ModelAssistedExtraction,
    ModelSkillSignal,
    ResumeEvidenceBasis,
)
from app.analysis.schemas import (
    EvidenceStatus,
    JobRequirement,
    ProvenanceSource,
    RequirementType,
    ResumeEvidence,
    SectionKind,
)

_MODEL_REQUIREMENT_WEIGHTS: dict[RequirementType, float] = {
    RequirementType.REQUIRED_QUALIFICATION: 1.0,
    RequirementType.CORE_RESPONSIBILITY: 0.85,
    RequirementType.PREFERRED_QUALIFICATION: 0.5,
    RequirementType.SUPPORTING_CONTEXT: 0.25,
}

_WHITESPACE = re.compile(r"\s+")
_ACTION_VERB = re.compile(
    r"^[^A-Za-z]*(?:analyzed|architected|assessed|automated|built|configured|"
    r"created|deployed|designed|developed|evaluated|implemented|improved|"
    r"integrated|maintained|managed|migrated|optimized|programmed|refactored|"
    r"tested|troubleshot)\b",
    re.IGNORECASE,
)


def _key(value: str) -> str:
    return _WHITESPACE.sub(" ", value.strip()).casefold()


def _model_only_evidence_status(signal: ModelSkillSignal) -> EvidenceStatus:
    """Accept strong proof only when deterministic syntax verifies application.

    Provider output is source-grounded before this merge in production. This
    second check requires an application-oriented evidence basis and an action
    verb before a new skill can count as demonstrated.
    """

    if (
        signal.evidence_basis == ResumeEvidenceBasis.DIRECT_APPLICATION
        and signal.evidence_status
        in {EvidenceStatus.DEMONSTRATED, EvidenceStatus.EXPLICIT}
        and _ACTION_VERB.search(signal.source_text)
    ):
        return EvidenceStatus.DEMONSTRATED
    if signal.evidence_status in {EvidenceStatus.IMPLIED, EvidenceStatus.RELATED}:
        return signal.evidence_status
    return EvidenceStatus.MENTIONED


def _merge_requirement_with_provenance(
    existing: JobRequirement | None,
    candidate: JobRequirement,
) -> JobRequirement:
    selected = _service._merge_requirement(existing, candidate)
    if existing is None:
        return selected
    if existing.source_origin != candidate.source_origin:
        return selected.model_copy(update={"source_origin": ProvenanceSource.MERGED})
    return selected


def _merge_semantic_model_extraction(
    requirements: list[JobRequirement],
    resume_evidence: dict[str, ResumeEvidence],
    extraction: ModelAssistedExtraction,
) -> tuple[list[JobRequirement], dict[str, ResumeEvidence]]:
    requirements_by_key = {_key(item.skill): item for item in requirements}
    evidence_by_key = {_key(skill): item for skill, item in resume_evidence.items()}

    for signal in extraction.job_requirements:
        skill = signal.skill.strip()
        if not skill:
            continue

        candidate = JobRequirement(
            skill=skill,
            requirement_type=signal.requirement_type,
            weight=_MODEL_REQUIREMENT_WEIGHTS[signal.requirement_type],
            source_text=signal.source_text,
            source_section=SectionKind.OTHER,
            confidence=signal.confidence,
            source_origin=ProvenanceSource.MODEL_ASSISTED,
        )
        key = _key(skill)
        requirements_by_key[key] = _merge_requirement_with_provenance(
            requirements_by_key.get(key),
            candidate,
        )

    # Legacy unknown lists contain no quoted source evidence. They are retained
    # in the schema for compatibility but are not accepted into scored output.
    # Unknown technologies should be emitted as normal signals with source_text.

    for signal in extraction.resume_skills:
        skill = signal.name.strip()
        if not skill:
            continue

        key = _key(skill)
        if key in evidence_by_key:
            # Deterministic parsing already found grounded evidence. The model may
            # not upgrade, replace, or relabel it, but the audit trail records that
            # both extraction paths identified the same signal.
            evidence_by_key[key] = evidence_by_key[key].model_copy(
                update={"source_origin": ProvenanceSource.MERGED}
            )
            continue

        status = _model_only_evidence_status(signal)
        candidate = ResumeEvidence(
            skill=skill,
            status=status,
            strength=_service._model_evidence_strength(status, signal.confidence),
            source_text=signal.source_text,
            source_section=SectionKind.OTHER,
            explanation=(
                "Model-assisted extraction surfaced this resume signal. "
                "MarketLens accepted strong proof only when the grounded source "
                "also passed deterministic action-language verification; other "
                "model-only signals remain conservatively capped."
            ),
            source_origin=ProvenanceSource.MODEL_ASSISTED,
        )
        evidence_by_key[key] = candidate

    return list(requirements_by_key.values()), {
        evidence.skill: evidence for evidence in evidence_by_key.values()
    }


def install_semantic_merge_patch() -> None:
    _service._merge_model_extraction = _merge_semantic_model_extraction
