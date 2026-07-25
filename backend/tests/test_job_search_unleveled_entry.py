from app.job_search import _score_job


def test_plain_specific_occupation_without_experience_is_entry_compatible() -> None:
    assert _score_job(
        title="Elementary School Social Studies Teacher",
        description="Teach elementary students in a public school education program.",
        query="elementary school teacher",
        level="entry",
    ) > 0
    assert _score_job(
        title="Electrical Engineer",
        description="Design electrical systems for commercial buildings.",
        query="electrical engineer",
        level="entry",
    ) > 0
    assert _score_job(
        title="Policy Analyst",
        description="Research legislation and prepare policy recommendations.",
        query="policy analyst",
        level="entry",
    ) > 0


def test_broad_family_entry_search_still_requires_entry_evidence() -> None:
    assert _score_job(
        title="Analytics Engineer",
        description="Build data pipelines with SQL and Python.",
        query="computer science",
        level="entry",
    ) == 0


def test_unleveled_entry_rule_still_rejects_contrary_level_evidence() -> None:
    assert _score_job(
        title="Senior Electrical Engineer",
        description="Design electrical systems.",
        query="electrical engineer",
        level="entry",
    ) == 0
    assert _score_job(
        title="Electrical Engineer II",
        description="Design electrical systems.",
        query="electrical engineer",
        level="entry",
    ) == 0
    assert _score_job(
        title="Electrical Engineer",
        description="Requires several years of experience designing power systems.",
        query="electrical engineer",
        level="entry",
    ) == 0
    assert _score_job(
        title="Product Manager",
        description="Own product strategy and roadmap.",
        query="product manager",
        level="entry",
    ) == 0


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
