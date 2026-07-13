from pathlib import Path

from fastapi.testclient import TestClient

from app.analysis.normalization import normalize_document_text
from app.analysis.requirements import extract_job_requirements
from app.analysis.schemas import (
    EvidenceStatus,
    FitBand,
    HardRequirementStatus,
    SectionKind,
)
from app.analysis.section_parser import parse_job_sections, parse_resume_sections
from app.analysis.service import analyze_smart_fit
from app.main import app

FIXTURES = Path(__file__).parent / "fixtures"
client = TestClient(app)


def _fixture_text(filename: str) -> str:
    return (FIXTURES / filename).read_text(encoding="utf-8")


def test_normalization_repairs_pdf_wraps_and_bullets() -> None:
    normalized = normalize_document_text(
        "PROJECTS\n• Built a Python service.\n• Wrote docu-\nmentation.\nPage 2 of 2"
    )

    assert "- Built a Python service." in normalized
    assert "- Wrote documentation." in normalized
    assert "Page 2 of 2" not in normalized


def test_section_parsers_recognize_real_world_headings() -> None:
    resume_sections = parse_resume_sections(
        normalize_document_text(_fixture_text("messy_resume.txt"))
    )
    job_sections = parse_job_sections(
        normalize_document_text(_fixture_text("long_backend_job.txt"))
    )

    assert {section.kind for section in resume_sections} >= {
        SectionKind.SKILLS,
        SectionKind.PROJECTS,
        SectionKind.EDUCATION,
    }
    assert {section.kind for section in job_sections} >= {
        SectionKind.COMPANY,
        SectionKind.RESPONSIBILITIES,
        SectionKind.REQUIRED,
        SectionKind.PREFERRED,
    }


def test_company_marketing_language_does_not_inflate_requirements() -> None:
    job_sections = parse_job_sections(
        normalize_document_text(_fixture_text("long_backend_job.txt"))
    )
    requirements = extract_job_requirements(job_sections)
    requirement_skills = {requirement.skill for requirement in requirements}

    assert "Python" in requirement_skills
    assert "AWS" in requirement_skills
    assert "Azure" not in requirement_skills
    assert "Machine Learning" not in requirement_skills


def test_smart_fit_analysis_uses_evidence_and_priority() -> None:
    analysis = analyze_smart_fit(
        resume_text=_fixture_text("messy_resume.txt"),
        job_description=_fixture_text("long_backend_job.txt"),
    )

    assert analysis.fit_summary.band == FitBand.CREDIBLE_ALIGNMENT
    assert 65 <= analysis.fit_summary.score < 80
    assert {"Python", "Docker", "PostgreSQL", "Testing", "Git", "REST APIs"} <= set(
        analysis.strong_matches
    )
    assert {"SQL"} <= set(analysis.under_sold_experience)
    assert {"AWS", "Kubernetes"} <= set(analysis.lower_priority_items)
    assert analysis.important_gaps == []

    assessment_by_skill = {
        assessment.skill: assessment for assessment in analysis.requirement_assessments
    }
    assert assessment_by_skill["Python"].status == EvidenceStatus.DEMONSTRATED
    assert assessment_by_skill["REST APIs"].status == EvidenceStatus.DEMONSTRATED
    assert assessment_by_skill["AWS"].status == EvidenceStatus.MISSING


def test_smart_fit_analysis_reports_category_coverage() -> None:
    analysis = analyze_smart_fit(
        resume_text=_fixture_text("messy_resume.txt"),
        job_description=_fixture_text("long_backend_job.txt"),
    )
    coverage_by_category = {
        coverage.category: coverage for coverage in analysis.category_coverage
    }

    assert coverage_by_category["backend"].score >= 80
    assert "REST APIs" in coverage_by_category["backend"].strong_skills
    assert coverage_by_category["cloud"].score == 0
    assert coverage_by_category["cloud"].weak_or_missing_skills == ["AWS"]
    assert coverage_by_category["devops"].priority_weight > coverage_by_category["cloud"].priority_weight


def test_hard_requirements_are_reported_without_guessing() -> None:
    analysis = analyze_smart_fit(
        resume_text=_fixture_text("messy_resume.txt"),
        job_description=_fixture_text("long_backend_job.txt"),
    )
    hard_requirements = {
        requirement.category: requirement for requirement in analysis.hard_requirements
    }

    assert hard_requirements["degree"].status == HardRequirementStatus.MEETS
    assert hard_requirements["citizenship"].status == HardRequirementStatus.UNCLEAR
    assert hard_requirements["years_experience"].status == HardRequirementStatus.UNCLEAR


def test_smart_analysis_endpoint_returns_structured_report() -> None:
    response = client.post(
        "/analysis/smart",
        json={
            "resume_text": _fixture_text("messy_resume.txt"),
            "job_description": _fixture_text("long_backend_job.txt"),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["fit_summary"]["band"] == "credible_alignment"
    assert body["requirement_assessments"]
    assert body["category_coverage"]
    assert body["recommendations"]
    assert "match_percentage" not in body
