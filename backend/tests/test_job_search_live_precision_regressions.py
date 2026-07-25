from app.job_search import _score_job


def test_elementary_school_query_rejects_middle_school_titles() -> None:
    assert _score_job(
        title="Elementary School Social Studies Teacher",
        description="Teach elementary students.",
        query="elementary school teacher",
        level="any",
    ) > 0
    assert _score_job(
        title="2026-27 Middle School Math Teacher",
        description="Teach middle school students.",
        query="elementary school teacher",
        level="any",
    ) == 0


def test_elementary_school_query_accepts_grade_level_title_evidence() -> None:
    assert _score_job(
        title="3rd Grade Teacher",
        description="Teach elementary students in a public school education program.",
        query="elementary school teacher",
        level="any",
    ) > 0


def test_broad_teacher_query_remains_broad() -> None:
    assert _score_job(
        title="Middle School Math Teacher",
        description="Teach middle school students.",
        query="teacher",
        level="any",
    ) > 0


def test_journalism_query_rejects_cinematic_video_editor() -> None:
    assert _score_job(
        title="Mid/Senior AI Cinematic Video Editor",
        description="Create cinematic AI videos for entertainment campaigns.",
        query="journalism",
        level="any",
    ) == 0


def test_journalism_query_preserves_newsroom_editor_and_reporter_titles() -> None:
    assert _score_job(
        title="Assignment Desk Editor",
        description="Coordinate breaking news coverage in the newsroom.",
        query="journalism",
        level="any",
    ) > 0
    assert _score_job(
        title="Data Reporter, Polling and Campaigns",
        description="Report data-driven political news.",
        query="journalism",
        level="any",
    ) > 0


def test_video_editor_query_still_accepts_video_editing_work() -> None:
    assert _score_job(
        title="AI Cinematic Video Editor",
        description="Create and edit cinematic video content.",
        query="video editor",
        level="any",
    ) > 0
