from __future__ import annotations

from app.analysis import analyze_smart_fit
from app.analysis import personalized_coaching
from app.analysis.model_extractor import (
    ModelAssistedExtraction,
    ModelJobRequirementSignal,
)
from app.analysis.responsibility_label_normalization import (
    canonicalize_grounded_model_skill_label,
    canonicalize_model_skill_label,
)
from app.analysis.schemas import EvidenceStatus, RequirementType
from app.analysis.semantic_contract import SemanticRequirementCategory
from app.skill_extractor import extract_skills


RESUME_TEXT = """PROJECTS
Built a Python FastAPI service backed by PostgreSQL.
SKILLS
Python, SQL, FastAPI, PostgreSQL
"""

JOB_TEXT = """Backend Engineer
REQUIRED QUALIFICATIONS
Python and SQL are required.
PREFERRED QUALIFICATIONS
Docker is preferred.
RESPONSIBILITIES
Build reliable backend APIs.
"""


def _assessment_by_skill(analysis, skill: str):
    return next(
        assessment
        for assessment in analysis.requirement_assessments
        if assessment.skill == skill
    )


def test_exact_responsibility_aliases_use_canonical_capability_label() -> None:
    assert canonicalize_model_skill_label("Build reliable backend APIs") == (
        "Backend API Reliability"
    )
    assert canonicalize_model_skill_label("  reliable backend APIs. ") == (
        "Backend API Reliability"
    )
    assert canonicalize_grounded_model_skill_label(
        "backend APIs",
        "Build reliable backend APIs",
    ) == "Backend API Reliability"
    assert canonicalize_grounded_model_skill_label(
        "RabbitMQ",
        "Build RabbitMQ messaging workers",
    ) == "RabbitMQ"
    assert canonicalize_model_skill_label("RabbitMQ") == "RabbitMQ"
    assert extract_skills("Build reliable backend APIs.") == [
        "Backend API Reliability"
    ]


def test_live_shaped_model_requirement_keeps_quote_score_and_single_reference(
    monkeypatch,
) -> None:
    deterministic = analyze_smart_fit(
        resume_text=RESUME_TEXT,
        job_description=JOB_TEXT,
        use_model_assisted=False,
    )

    def fake_model_extractor(
        resume_text: str,
        job_description: str,
    ) -> ModelAssistedExtraction:
        return ModelAssistedExtraction(
            resume_skills=[],
            job_requirements=[
                ModelJobRequirementSignal(
                    skill="backend APIs",
                    category="backend reliability",
                    semantic_category=SemanticRequirementCategory.RESPONSIBILITY,
                    requirement_type=RequirementType.CORE_RESPONSIBILITY,
                    confidence=0.96,
                    context="backend API reliability",
                    source_text="Build reliable backend APIs",
                )
            ],
            hard_constraints=[],
            unknown_resume_skills=[],
            unknown_job_skills=[],
            uncertainty_notes=[],
        )

    monkeypatch.setattr(
        "app.analysis.service.extract_model_assisted_signals",
        fake_model_extractor,
    )

    analysis = analyze_smart_fit(
        resume_text=RESUME_TEXT,
        job_description=JOB_TEXT,
        use_model_assisted=True,
    )

    assessment = _assessment_by_skill(analysis, "Backend API Reliability")

    assert analysis.analysis_engine == "model_assisted"
    assert analysis.model_assisted_status == "used"
    assert analysis.fit_summary.score == deterministic.fit_summary.score
    assert assessment.status == EvidenceStatus.MISSING
    assert assessment.job_evidence == "Build reliable backend APIs"
    assert assessment.job_provenance is not None
    assert assessment.job_provenance.quote == "Build reliable backend APIs"
    assert assessment.job_provenance.grounded is True
    assert assessment.grounded is True

    labels = [item.skill for item in analysis.requirement_assessments]
    assert labels.count("Backend API Reliability") == 1
    assert "backend APIs" not in labels
    assert "Build reliable backend APIs" not in labels

    backend_coverage = next(
        item for item in analysis.category_coverage if item.category == "backend"
    )
    assert backend_coverage.weak_or_missing_skills.count("Backend API Reliability") == 1
    assert analysis.important_gaps.count("Backend API Reliability") == 1
    assert "backend APIs" not in analysis.important_gaps

    coaching_context = personalized_coaching._analysis_context(analysis)
    allowed_references = coaching_context["allowed_references"]
    assert allowed_references.count("Backend API Reliability") == 1
    assert "backend APIs" not in allowed_references

    assert any(
        "Backend API Reliability" in action.title
        or "Backend API Reliability" in action.advice
        for action in analysis.coaching_actions
    )
