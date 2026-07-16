from pathlib import Path

from fastapi.testclient import TestClient

from app.analysis.model_extractor import (
    AI_ANALYSIS_ENABLED_ENV,
    OPENAI_API_KEY_ENV,
    OPENAI_MODEL_ENV,
    ModelAssistedExtraction,
    ModelJobRequirementSignal,
    ModelSkillSignal,
)
from app.analysis.normalization import normalize_document_text
from app.analysis.requirements import extract_job_requirements
from app.analysis.schemas import (
    CoachingActionType,
    EvidenceStatus,
    FitBand,
    HardRequirementStatus,
    RequirementType,
    SectionKind,
)
from app.analysis.section_parser import parse_job_sections, parse_resume_sections
from app.analysis.service import analyze_smart_fit
from app.main import app

FIXTURES = Path(__file__).parent / "fixtures"
client = TestClient(app)


FULL_STACK_RESUME = """
Bachelor of Science in Computer Science expected May 2027
Major: Computer Science, Cumulative GPA: 3.915

Highlighted coursework: Java, Python, C, Physics of Digital Circuits, Discrete Mathematics,
Calculus I & II, Data Structures & Algorithms, Graphics, Database Systems covering SQL,
Operating Systems I, Physics I, Intro to Probability.

SKILLS
Computer Languages: Java, Python, C, SQL
Certificates: Building AI Products: Prototyping Essentials Professional Certificate.

RELEVANT EXPERIENCE
IT Department, May-August 2025.
Receiving and responding to company-technology related problems, software and hardware.
Repairing, upgrading, dismantling, and imaging company desktops and chromebooks.
Installing office equipment and repairing company equipment around the office building.
"""

FULL_STACK_JOB = """
What You'll Do:
Perform full-stack development including front end, business logic, and data access layers.
Responsible for the entire development lifecycle from planning to release and support.
Actively contribute to software architecture decisions, design strategies, and code reviews to ensure high-quality, scalable, and maintainable solutions.
Collaborate closely with development team members and stakeholders.

What We're Looking For:
3 or more years of experience developing software in an Agile, team-based environment.
1 or more years of experience developing responsive web applications.
Expertise with Angular, ASP.NET Core, C#, JavaScript, TypeScript, CSS, SASS, and HTML.
BS and/or MS in a technical discipline, Computer Science or Software Engineering required.
Strong understanding of OOP concepts and design patterns.
Experience in building robust APIs and adhering to Service-Oriented Architecture principles.
Familiarity with event-based software design and event-driven architecture.
Experience with PostgreSQL or other relational databases, and Entity Framework Core or similar object-relational mapping frameworks.
Excellent problem solving and communication skills.
"""


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

    # The broader ontology now recognizes more job requirements, so the same
    # fixture should be graded more strictly than the original narrow version.
    assert analysis.fit_summary.band == FitBand.PARTIAL_ALIGNMENT
    assert 45 <= analysis.fit_summary.score < 65
    assert {"Python", "Docker", "PostgreSQL", "Testing", "Git", "REST APIs"} <= set(
        analysis.strong_matches
    )
    assert {"SQL"} <= set(analysis.under_sold_experience)
    assert {"AWS", "Kubernetes"} <= set(analysis.lower_priority_items)
    assert analysis.important_gaps
    assert analysis.report_summary
    assert analysis.gap_groups
    assert analysis.analysis_engine == "deterministic"
    assert analysis.model_assisted_status == "not_requested"

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


def test_smart_fit_analysis_returns_coaching_actions() -> None:
    analysis = analyze_smart_fit(
        resume_text=_fixture_text("messy_resume.txt"),
        job_description=_fixture_text("long_backend_job.txt"),
    )
    actions_by_type = {action.action_type for action in analysis.coaching_actions}

    assert CoachingActionType.LEARNING_FOCUS in actions_by_type
    assert CoachingActionType.RESUME_REWRITE in actions_by_type
    assert CoachingActionType.HARD_REQUIREMENT_CHECK in actions_by_type

    rewrite_actions = [
        action
        for action in analysis.coaching_actions
        if action.action_type == CoachingActionType.RESUME_REWRITE
    ]
    assert any(action.title == "Turn background into resume proof" for action in rewrite_actions)
    assert any("SQL" in action.advice for action in rewrite_actions)
    assert all(action.advice for action in analysis.coaching_actions)


def test_full_stack_role_analysis_captures_specific_stack_and_constraints() -> None:
    analysis = analyze_smart_fit(
        resume_text=FULL_STACK_RESUME,
        job_description=FULL_STACK_JOB,
    )
    requirement_skills = {assessment.skill for assessment in analysis.requirement_assessments}
    hard_requirements = {
        requirement.category: requirement for requirement in analysis.hard_requirements
    }
    gap_group_titles = {group.title for group in analysis.gap_groups}

    assert analysis.fit_summary.band == FitBand.LIMITED_ALIGNMENT
    assert analysis.fit_summary.score < 25
    assert "Agile" not in analysis.fit_summary.headline
    assert "Full-Stack Development" in analysis.fit_summary.headline
    assert "Full-stack / .NET stack" in gap_group_titles
    assert "Frontend web stack" in gap_group_titles

    assert {
        "Full-Stack Development",
        "Angular",
        "ASP.NET Core",
        "C#",
        "JavaScript",
        "TypeScript",
        "CSS",
        "Sass",
        "HTML",
        "REST APIs",
        "Service-Oriented Architecture",
        "Event-Driven Architecture",
        "Entity Framework Core",
        "OOP",
        "Design Patterns",
    } <= requirement_skills

    assert "SQL" in analysis.under_sold_experience
    assert "SQL" not in analysis.strong_matches
    assert "ASP.NET Core" in analysis.important_gaps
    assert "Angular" in analysis.important_gaps
    assert "C#" in analysis.important_gaps
    assert "C" in analysis.resume_skills_found
    assert "C" in analysis.other_resume_skills

    assert hard_requirements["degree"].status == HardRequirementStatus.UNCLEAR
    assert hard_requirements["years_experience"].status == HardRequirementStatus.UNCLEAR


def test_model_assisted_request_falls_back_when_not_configured(monkeypatch) -> None:
    monkeypatch.delenv(AI_ANALYSIS_ENABLED_ENV, raising=False)
    monkeypatch.delenv(OPENAI_API_KEY_ENV, raising=False)
    monkeypatch.delenv(OPENAI_MODEL_ENV, raising=False)

    analysis = analyze_smart_fit(
        resume_text=_fixture_text("messy_resume.txt"),
        job_description=_fixture_text("long_backend_job.txt"),
        use_model_assisted=True,
    )

    assert analysis.analysis_engine == "deterministic"
    assert analysis.model_assisted_status.startswith("fallback_unavailable")
    assert analysis.requirement_assessments


def test_model_assisted_extraction_can_surface_unknown_skills(monkeypatch) -> None:
    def fake_model_extractor(resume_text: str, job_description: str) -> ModelAssistedExtraction:
        return ModelAssistedExtraction(
            resume_skills=[
                ModelSkillSignal(
                    name="RabbitMQ",
                    category="backend",
                    evidence_status=EvidenceStatus.DEMONSTRATED,
                    confidence=0.92,
                    context="backend messaging",
                    source_text="Built a RabbitMQ worker service for async jobs.",
                )
            ],
            job_requirements=[
                ModelJobRequirementSignal(
                    skill="RabbitMQ",
                    category="backend",
                    requirement_type=RequirementType.REQUIRED_QUALIFICATION,
                    weight=1.0,
                    confidence=0.94,
                    context="backend messaging",
                    source_text="Build RabbitMQ messaging workers for backend systems.",
                )
            ],
            hard_constraints=[],
            unknown_resume_skills=["RabbitMQ"],
            unknown_job_skills=[],
            uncertainty_notes=[],
        )

    monkeypatch.setattr("app.analysis.service.extract_model_assisted_signals", fake_model_extractor)

    analysis = analyze_smart_fit(
        resume_text="PROJECTS\n- Built a worker service with message queues for async jobs.",
        job_description="Required Qualifications\nBuild RabbitMQ messaging workers for backend systems.",
        use_model_assisted=True,
    )

    assert analysis.analysis_engine == "model_assisted"
    assert analysis.model_assisted_status == "used"
    assert "RabbitMQ" in analysis.resume_skills_found
    assert "RabbitMQ" in analysis.job_relevant_resume_skills
    assert "RabbitMQ" in analysis.strong_matches


def test_hard_requirements_are_reported_without_guessing() -> None:
    analysis = analyze_smart_fit(
        resume_text=_fixture_text("messy_resume.txt"),
        job_description=_fixture_text("long_backend_job.txt"),
    )
    hard_requirements = {
        requirement.category: requirement for requirement in analysis.hard_requirements
    }

    assert hard_requirements["degree"].status == HardRequirementStatus.UNCLEAR
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
    assert body["fit_summary"]["band"] == "partial_alignment"
    assert body["requirement_assessments"]
    assert body["category_coverage"]
    assert body["coaching_actions"]
    assert body["report_summary"]
    assert body["gap_groups"]
    assert body["resume_skills_found"]
    assert body["recommendations"]
    assert body["analysis_engine"] == "deterministic"
    assert body["model_assisted_status"] == "not_requested"
    assert "match_percentage" not in body
