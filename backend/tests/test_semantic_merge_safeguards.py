from __future__ import annotations

import json
from pathlib import Path

import app.analysis.service as service
from app.analysis import semantic_merge_patch
from app.analysis.model_extractor import ModelAssistedExtraction
from app.analysis.schemas import (
    EvidenceStatus,
    JobRequirement,
    ProvenanceSource,
    RequirementType,
    ResumeEvidence,
    SectionKind,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "model_assisted_extraction_v8b1.json"
)


def _extraction() -> ModelAssistedExtraction:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    fixture["unknown_job_skills"] = ["MysteryDB"]
    fixture["unknown_resume_skills"] = ["MysteryTool"]
    return ModelAssistedExtraction.model_validate(fixture)


def test_model_requirement_weights_are_derived_from_requirement_type() -> None:
    semantic_merge_patch.install_semantic_merge_patch()

    requirements, _ = service._merge_model_extraction([], {}, _extraction())
    by_skill = {item.skill: item for item in requirements}

    assert by_skill["Python"].weight == 1.0
    assert by_skill["Data Pipelines"].weight == 0.85
    assert by_skill["Kubernetes"].weight == 0.5
    assert "MysteryDB" not in by_skill


def test_model_cannot_upgrade_existing_deterministic_resume_evidence() -> None:
    semantic_merge_patch.install_semantic_merge_patch()

    deterministic = ResumeEvidence(
        skill="Python",
        status=EvidenceStatus.MENTIONED,
        strength=0.55,
        source_text="Python",
        source_section=SectionKind.SKILLS,
        explanation="Listed in skills.",
    )

    _, evidence = service._merge_model_extraction(
        [],
        {"Python": deterministic},
        _extraction(),
    )

    merged = evidence["Python"]
    assert merged.model_copy(
        update={"source_origin": ProvenanceSource.DETERMINISTIC}
    ) == deterministic
    assert merged.source_origin == ProvenanceSource.MERGED


def test_model_only_resume_signal_is_capped_at_mentioned() -> None:
    semantic_merge_patch.install_semantic_merge_patch()

    _, evidence = service._merge_model_extraction([], {}, _extraction())

    assert evidence["Terraform"].status == EvidenceStatus.MENTIONED
    assert evidence["Terraform"].strength < 0.8
    assert "MysteryTool" not in evidence


def test_model_requirement_cannot_downgrade_stronger_deterministic_priority() -> None:
    semantic_merge_patch.install_semantic_merge_patch()

    deterministic = JobRequirement(
        skill="Kubernetes",
        requirement_type=RequirementType.REQUIRED_QUALIFICATION,
        weight=1.0,
        source_text="Kubernetes is required for production operations.",
        source_section=SectionKind.REQUIRED,
        confidence=0.95,
    )

    requirements, _ = service._merge_model_extraction(
        [deterministic],
        {},
        _extraction(),
    )
    by_skill = {item.skill: item for item in requirements}

    merged = by_skill["Kubernetes"]
    assert merged.model_copy(
        update={"source_origin": ProvenanceSource.DETERMINISTIC}
    ) == deterministic
    assert merged.source_origin == ProvenanceSource.MERGED
