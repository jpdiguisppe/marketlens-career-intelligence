from app.analysis.skill_ontology import RELATED_SKILLS, SKILL_CATEGORIES, SKILL_PATTERNS
from app.skill_extractor import count_skills, extract_skills


def test_extract_skills_returns_normalized_skill_names() -> None:
    text = "Built Python APIs with PostgreSQL, Docker, GitHub Actions, and Azure."

    skills = extract_skills(text)

    assert skills == [
        "Azure",
        "CI/CD",
        "Docker",
        "PostgreSQL",
        "Python",
    ]


def test_extract_skills_does_not_confuse_java_and_javascript() -> None:
    text = "Frontend experience with JavaScript, TypeScript, React, and Node.js."

    skills = extract_skills(text)

    assert "JavaScript" in skills
    assert "Java" not in skills
    assert "TypeScript" in skills
    assert "React" in skills
    assert "Node.js" in skills


def test_extract_skills_recognizes_automated_tests_wording() -> None:
    skills = extract_skills("Write automated tests and participate in code review.")

    assert "Testing" in skills


def test_extract_skills_recognizes_restful_services_wording() -> None:
    skills = extract_skills("Design and maintain RESTful services in Python.")

    assert "REST APIs" in skills


def test_extract_skills_recognizes_real_world_aliases() -> None:
    text = (
        "Built backend endpoints for containerized workloads, maintained deployment pipelines, "
        "and used source control for code review."
    )

    skills = extract_skills(text)

    assert "REST APIs" in skills
    assert "Docker" in skills
    assert "CI/CD" in skills
    assert "Git" in skills


def test_extract_skills_recognizes_dockerized_services_wording() -> None:
    skills = extract_skills("Maintain Dockerized services and support deployment pipelines.")

    assert "Docker" in skills


def test_extract_skills_recognizes_full_stack_dotnet_job_language() -> None:
    text = (
        "Perform full-stack development with Angular, ASP.NET Core, C#, JavaScript, TypeScript, "
        "CSS, SASS, and HTML. Build robust APIs using Service-Oriented Architecture, "
        "event-driven architecture, Entity Framework Core, OOP concepts, and design patterns."
    )

    skills = extract_skills(text)

    assert "Full-Stack Development" in skills
    assert "Angular" in skills
    assert "ASP.NET Core" in skills
    assert "C#" in skills
    assert "JavaScript" in skills
    assert "TypeScript" in skills
    assert "CSS" in skills
    assert "Sass" in skills
    assert "HTML" in skills
    assert "REST APIs" in skills
    assert "Service-Oriented Architecture" in skills
    assert "Event-Driven Architecture" in skills
    assert "Entity Framework Core" in skills
    assert "OOP" in skills
    assert "Design Patterns" in skills


def test_skill_ontology_exposes_categories_and_relationships() -> None:
    assert SKILL_CATEGORIES["REST APIs"] == "backend"
    assert SKILL_CATEGORIES["Docker"] == "devops"
    assert "REST APIs" in RELATED_SKILLS["FastAPI"]
    assert "containerized workloads" in SKILL_PATTERNS["Docker"]
    assert "dockerized services" in SKILL_PATTERNS["Docker"]


def test_count_skills_counts_each_skill_once_per_text() -> None:
    texts = [
        "Python Python Python and SQL are required.",
        "Python, Docker, and REST APIs are preferred.",
    ]

    skill_counts = count_skills(texts)

    assert skill_counts["Python"] == 2
    assert skill_counts["SQL"] == 1
    assert skill_counts["Docker"] == 1
    assert skill_counts["REST APIs"] == 1
