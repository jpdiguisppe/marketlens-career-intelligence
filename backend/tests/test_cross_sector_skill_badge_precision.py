from app.skill_extractor import extract_skills


def test_accounting_company_ai_language_does_not_create_machine_learning_badge() -> None:
    skills = extract_skills(
        "Our company uses AI to improve access to financial services. "
        "The accountant prepares journal entries, reconciliations, and monthly close support."
    )

    assert "Machine Learning" not in skills


def test_electrician_field_testing_and_class_c_license_are_not_technical_badges() -> None:
    skills = extract_skills(
        "Perform field testing of electrical equipment, troubleshoot wiring, "
        "and maintain a valid Class C driver's license."
    )

    assert "Testing" not in skills
    assert "C" not in skills


def test_teacher_standardized_testing_is_not_software_testing() -> None:
    skills = extract_skills(
        "Coordinate standardized testing, classroom assessments, and family communication."
    )

    assert "Testing" not in skills


def test_explicit_programming_c_context_still_resolves() -> None:
    skills = extract_skills(
        "Computer Languages: Java, Python, C, and SQL for embedded software development."
    )

    assert "C" in skills
    assert "Python" in skills
    assert "SQL" in skills


def test_explicit_software_testing_context_still_resolves() -> None:
    skills = extract_skills(
        "Perform software testing for REST APIs, write automated tests, "
        "and maintain regression test coverage."
    )

    assert "Testing" in skills
    assert "REST APIs" in skills


def test_explicit_machine_learning_model_work_still_resolves() -> None:
    skills = extract_skills(
        "Develop and deploy machine learning models in Python, including training and inference."
    )

    assert "Machine Learning" in skills
    assert "Python" in skills


def test_ai_ml_compound_skill_language_still_resolves() -> None:
    skills = extract_skills(
        "Experience building AI/ML models and production inference services is required."
    )

    assert "Machine Learning" in skills
