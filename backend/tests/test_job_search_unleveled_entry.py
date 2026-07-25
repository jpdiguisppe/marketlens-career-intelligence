from app.job_search import _matches_level, _score_job


def test_plain_occupation_without_experience_requirement_is_entry_compatible() -> None:
    assert _matches_level(
        "Elementary School Social Studies Teacher",
        "Teach elementary students in a public school education program.",
        "entry",
    )
    assert _matches_level(
        "Electrical Engineer",
        "Design electrical systems for commercial buildings.",
        "entry",
    )
    assert _matches_level(
        "Policy Analyst",
        "Research legislation and prepare policy recommendations.",
        "entry",
    )


def test_unleveled_entry_rule_still_rejects_contrary_level_evidence() -> None:
    assert not _matches_level(
        "Senior Electrical Engineer",
        "Design electrical systems.",
        "entry",
    )
    assert not _matches_level(
        "Electrical Engineer II",
        "Design electrical systems.",
        "entry",
    )
    assert not _matches_level(
        "Electrical Engineer",
        "Requires several years of experience designing power systems.",
        "entry",
    )
    assert not _matches_level(
        "Product Manager",
        "Own product strategy and roadmap.",
        "entry",
    )


def test_unleveled_entry_jobs_rank_below_explicit_entry_titles() -> None:
    plain_score = _score_job(
        title="Electrical Engineer",
        description="Design electrical systems for commercial buildings.",
        query="electrical engineer",
        level="entry",
    )
    explicit_score = _score_job(
        title="Electrical Engineer I",
        description="Entry-level electrical design position.",
        query="electrical engineer",
        level="entry",
    )

    assert plain_score > 0
    assert explicit_score > plain_score
