from app.job_search import _score_job, parse_job_search_intent


def test_legal_internship_intent_is_separated_from_location_and_level() -> None:
    intent = parse_job_search_intent(
        query="legal internship",
        location="Philadelphia",
    )

    assert intent.job_function == "legal"
    assert intent.industry == "legal_services"
    assert intent.level == "intern"
    assert intent.location == "Philadelphia"


def test_cross_industry_legal_examples_parse_independent_dimensions() -> None:
    sports = parse_job_search_intent("sports legal operations internship")
    healthcare = parse_job_search_intent("healthcare compliance analyst entry level")
    public_interest = parse_job_search_intent("public interest policy internship")
    finance = parse_job_search_intent("financial services regulatory analyst")

    assert (sports.job_function, sports.industry, sports.level) == (
        "legal_operations",
        "sports",
        "intern",
    )
    assert (healthcare.job_function, healthcare.industry, healthcare.level) == (
        "compliance",
        "healthcare",
        "entry",
    )
    assert (public_interest.job_function, public_interest.industry, public_interest.level) == (
        "policy",
        "public_interest",
        "intern",
    )
    assert (finance.job_function, finance.industry) == (
        "compliance",
        "financial_services",
    )


def test_legal_role_scoring_rejects_unrelated_internships() -> None:
    assert _score_job(
        "Legal Intern",
        "Support legal research, contracts, and policy projects.",
        "legal internship",
        level="intern",
        company="Example Legal Organization",
    ) > 0
    assert _score_job(
        "Software Engineering Intern",
        "Build backend services for the legal team.",
        "legal internship",
        level="intern",
        company="Example Technology Company",
    ) == 0
