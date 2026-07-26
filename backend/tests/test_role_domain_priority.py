from app.analysis import analyze_smart_fit


def test_marketing_coordinator_is_not_reduced_to_generic_operations_role() -> None:
    analysis = analyze_smart_fit(
        resume_text=(
            "PROJECTS\n"
            "Developed a backend API and relational database for a career application."
        ),
        job_description=(
            "Marketing Coordinator\n"
            "RESPONSIBILITIES\n"
            "Plan campaigns, create content, manage social media channels, "
            "and support brand initiatives."
        ),
    )

    assert "Marketing channels and campaign execution" in analysis.important_gaps
    assert analysis.analysis_engine == "deterministic"
