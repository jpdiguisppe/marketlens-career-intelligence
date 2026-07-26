from __future__ import annotations

import app.analysis.service as service
from app.analysis import analyze_smart_fit
from app.analysis.model_extractor import (
    MODEL_ASSISTED_SCHEMA_VERSION,
    ModelAssistedExtraction,
    ModelJobRequirementSignal,
    ModelSkillSignal,
    ResumeEvidenceBasis,
    SemanticRequirementCategory,
)
from app.analysis.provenance_patch import quote_is_grounded
from app.analysis.schemas import (
    EvidenceStatus,
    JobRequirement,
    ProvenanceSource,
    RequirementType,
    ResumeEvidence,
    SectionKind,
)

RESUME = """SUMMARY
Computer science student building backend services.

PROJECTS
Built a Python FastAPI service and PostgreSQL database for career analysis.

SKILLS
Python, SQL, FastAPI, PostgreSQL
"""

JOB = """Backend Software Engineer

REQUIRED QUALIFICATIONS
Python is required for backend service development.
SQL experience is required.

PREFERRED QUALIFICATIONS
Docker experience is preferred.
"""


def test_quote_grounding_normalizes_whitespace_and_bullets() -> None:
    assert quote_is_grounded(
        "Python is required for backend service development.",
        "Required Qualifications\n- Python is required for backend service development.",
    )
    assert not quote_is_grounded("Five years of Rust", JOB)


def test_deterministic_assessments_include_grounded_provenance() -> None:
    analysis = analyze_smart_fit(RESUME, JOB)

    assert analysis.provenance_version == "8c.1"
    assert analysis.grounding_warnings == []
    assert analysis.requirement_assessments

    for assessment in analysis.requirement_assessments:
        assert assessment.job_provenance is not None
        assert assessment.job_provenance.grounded
        assert assessment.job_provenance.source == ProvenanceSource.DETERMINISTIC
        assert assessment.job_provenance.quote == assessment.job_evidence
        assert assessment.grounded
        if assessment.status != EvidenceStatus.MISSING:
            assert assessment.resume_provenance
            assert all(citation.grounded for citation in assessment.resume_provenance)


def test_gap_group_carries_the_grounded_job_quote() -> None:
    analysis = analyze_smart_fit(RESUME, JOB)
    docker_assessment = next(
        item for item in analysis.requirement_assessments if item.skill == "Docker"
    )

    assert docker_assessment.status == EvidenceStatus.MISSING
    assert docker_assessment.job_provenance is not None
    assert docker_assessment.job_provenance.grounded

    docker_group = next(
        group for group in analysis.gap_groups if "Docker" in group.skills
    )
    assert docker_assessment.job_evidence in docker_group.job_evidence
    assert "Posting evidence:" in docker_group.summary


def test_ungrounded_job_requirement_is_removed_from_scoring(monkeypatch) -> None:
    fabricated = JobRequirement(
        skill="Rust",
        requirement_type=RequirementType.REQUIRED_QUALIFICATION,
        weight=1.0,
        source_text="Five years of Rust leadership is required.",
        source_section=SectionKind.REQUIRED,
    )
    monkeypatch.setattr(service, "extract_job_requirements", lambda sections: [fabricated])

    analysis = analyze_smart_fit(RESUME, JOB)
    assessment = analysis.requirement_assessments[0]

    assert assessment.skill == "Rust"
    assert assessment.weight == 0.0
    assert assessment.status == EvidenceStatus.MISSING
    assert not assessment.grounded
    assert assessment.job_provenance is not None
    assert not assessment.job_provenance.grounded
    assert analysis.fit_summary.score == 0
    assert analysis.strong_matches == []
    assert analysis.important_gaps == []
    assert analysis.grounding_warnings == [
        "Excluded ungrounded requirement conclusion: Rust"
    ]


def test_ungrounded_resume_quote_is_downgraded_to_missing(monkeypatch) -> None:
    fabricated_evidence = ResumeEvidence(
        skill="Python",
        status=EvidenceStatus.DEMONSTRATED,
        strength=1.0,
        source_text="Architected Python systems serving ten million users.",
        source_section=SectionKind.PROJECTS,
        explanation="Fabricated evidence for a grounding regression test.",
    )
    monkeypatch.setattr(
        service,
        "extract_resume_evidence",
        lambda sections: {"Python": fabricated_evidence},
    )

    analysis = analyze_smart_fit(RESUME, JOB)
    python_assessment = next(
        item for item in analysis.requirement_assessments if item.skill == "Python"
    )

    assert python_assessment.status == EvidenceStatus.MISSING
    assert python_assessment.strength == 0.0
    assert python_assessment.resume_evidence == []
    assert not python_assessment.grounded
    assert python_assessment.resume_provenance
    assert not python_assessment.resume_provenance[0].grounded
    assert "Python" not in analysis.strong_matches


def test_model_and_deterministic_signals_report_merged_provenance(monkeypatch) -> None:
    extraction = ModelAssistedExtraction(
        schema_version=MODEL_ASSISTED_SCHEMA_VERSION,
        resume_skills=[
            ModelSkillSignal(
                name="Python",
                category="programming_language",
                semantic_category=SemanticRequirementCategory.TOOL_TECHNOLOGY,
                evidence_basis=ResumeEvidenceBasis.DIRECT_APPLICATION,
                evidence_status=EvidenceStatus.DEMONSTRATED,
                confidence=0.98,
                context="backend",
                source_text="Built a Python FastAPI service",
            )
        ],
        job_requirements=[
            ModelJobRequirementSignal(
                skill="Python",
                category="programming_language",
                semantic_category=SemanticRequirementCategory.TOOL_TECHNOLOGY,
                requirement_type=RequirementType.REQUIRED_QUALIFICATION,
                confidence=0.99,
                context="backend",
                source_text="Python is required for backend service development.",
            )
        ],
        hard_constraints=[],
        unknown_resume_skills=[],
        unknown_job_skills=[],
        uncertainty_notes=[],
    )
    monkeypatch.setattr(service, "extract_model_assisted_signals", lambda *_: extraction)

    analysis = analyze_smart_fit(RESUME, JOB, use_model_assisted=True)
    python_assessment = next(
        item for item in analysis.requirement_assessments if item.skill == "Python"
    )

    assert analysis.analysis_engine == "model_assisted"
    assert python_assessment.conclusion_source == ProvenanceSource.MERGED
    assert python_assessment.job_provenance is not None
    assert python_assessment.job_provenance.source == ProvenanceSource.MERGED
    assert python_assessment.resume_provenance[0].source == ProvenanceSource.MERGED
    assert python_assessment.grounded


def test_hard_requirements_are_grounded_and_remain_conservative() -> None:
    job = f"""{JOB}
Applicants must hold a bachelor's degree in computer science.
"""
    analysis = analyze_smart_fit(RESUME, job)
    degree = next(
        item for item in analysis.hard_requirements if item.category == "degree"
    )

    assert degree.grounded
    assert degree.source_origin == ProvenanceSource.DETERMINISTIC
    assert degree.status.value in {"meets", "unclear"}
