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