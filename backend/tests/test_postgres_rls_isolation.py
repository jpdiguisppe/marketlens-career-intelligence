from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote, urlsplit, urlunsplit

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.career_plans.models import CareerPlanAuditEventDB, CareerPlanRunDB, CareerPlanStepDB
from app.database import Base, bind_authenticated_user
from app.models import JobPostingDB, SavedJobDB, SavedReportDB  # noqa: F401
from scripts.apply_database_security_migrations import apply_database_security_migrations

POSTGRES_TEST_URL_ENV = "MARKETLENS_POSTGRES_TEST_URL"
RUNTIME_ROLE = "marketlens_runtime_test"
RUNTIME_PASSWORD = "marketlens-runtime-test-password"
USER_A = "rls-test-user-a"
USER_B = "rls-test-user-b"

pytestmark = pytest.mark.skipif(
    not os.getenv(POSTGRES_TEST_URL_ENV),
    reason="PostgreSQL RLS integration test requires MARKETLENS_POSTGRES_TEST_URL.",
)


@dataclass(frozen=True)
class PostgresSecurityFixture:
    admin_url: str
    runtime_url: str
    admin_engine: object
    runtime_engine: object


def _runtime_url(admin_url: str) -> str:
    parts = urlsplit(admin_url)
    host = parts.hostname or "localhost"
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    port = f":{parts.port}" if parts.port is not None else ""
    netloc = f"{quote(RUNTIME_ROLE, safe='')}:{quote(RUNTIME_PASSWORD, safe='')}@{host}{port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def _set_user(connection: object, user_id: str) -> None:
    connection.execute(
        text("SELECT set_config('app.current_user_id', :user_id, true)"),
        {"user_id": user_id},
    )


@pytest.fixture(scope="module")
def postgres_security() -> PostgresSecurityFixture:
    admin_url = os.environ[POSTGRES_TEST_URL_ENV]
    admin_engine = create_engine(admin_url)

    with admin_engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS marketlens_schema_migrations"))
    Base.metadata.drop_all(bind=admin_engine)
    Base.metadata.create_all(bind=admin_engine)

    first_apply = apply_database_security_migrations(
        admin_url,
        RUNTIME_ROLE,
        RUNTIME_PASSWORD,
    )
    assert first_apply == ["0001_force_user_data_rls"]

    second_apply = apply_database_security_migrations(
        admin_url,
        RUNTIME_ROLE,
        RUNTIME_PASSWORD,
    )
    assert second_apply == []

    runtime_url = _runtime_url(admin_url)
    runtime_engine = create_engine(runtime_url, pool_size=2, max_overflow=0)
    fixture = PostgresSecurityFixture(
        admin_url=admin_url,
        runtime_url=runtime_url,
        admin_engine=admin_engine,
        runtime_engine=runtime_engine,
    )
    try:
        yield fixture
    finally:
        runtime_engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS marketlens_schema_migrations"))
        Base.metadata.drop_all(bind=admin_engine)
        admin_engine.dispose()


def test_runtime_role_is_non_owner_and_cannot_administer_schema(
    postgres_security: PostgresSecurityFixture,
) -> None:
    engine = postgres_security.runtime_engine

    with engine.connect() as connection:
        role = connection.execute(
            text(
                """
                SELECT current_user, rolsuper, rolcreatedb, rolcreaterole,
                       rolinherit, rolbypassrls, rolcanlogin
                FROM pg_roles
                WHERE rolname = current_user
                """
            )
        ).one()
        assert role[0] == RUNTIME_ROLE
        assert role[1:] == (False, False, False, False, False, True)
        assert connection.execute(
            text("SELECT has_schema_privilege(current_user, 'public', 'CREATE')")
        ).scalar_one() is False

        protected_tables = connection.execute(
            text(
                """
                SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity,
                       pg_get_userbyid(c.relowner) AS owner_name
                FROM pg_class AS c
                JOIN pg_namespace AS n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relname IN (
                    'saved_jobs', 'saved_reports', 'career_plan_runs',
                    'career_plan_steps', 'career_plan_audit_events'
                  )
                ORDER BY c.relname
                """
            )
        ).all()
        assert len(protected_tables) == 5
        assert all(row[1] is True and row[2] is True for row in protected_tables)
        assert all(row[3] != RUNTIME_ROLE for row in protected_tables)

    with engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(DBAPIError):
            connection.execute(text("CREATE TABLE rls_escape_attempt (id integer)"))
        transaction.rollback()

    with engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(DBAPIError):
            connection.execute(text("ALTER TABLE saved_jobs DISABLE ROW LEVEL SECURITY"))
        transaction.rollback()


def test_saved_job_and_saved_report_rls_blocks_cross_user_crud(
    postgres_security: PostgresSecurityFixture,
) -> None:
    engine = postgres_security.runtime_engine

    with engine.begin() as connection:
        _set_user(connection, USER_A)
        saved_job_id = connection.execute(
            text(
                """
                INSERT INTO saved_jobs (
                    user_id, source, company, title, description, extracted_skills_json
                ) VALUES (
                    :user_id, 'test', 'Example Co', 'Engineer', 'Private description', '[]'
                ) RETURNING id
                """
            ),
            {"user_id": USER_A},
        ).scalar_one()
        saved_report_id = connection.execute(
            text(
                """
                INSERT INTO saved_reports (
                    user_id, source, title, summary_json
                ) VALUES (
                    :user_id, 'test', 'Private report', '{}'
                ) RETURNING id
                """
            ),
            {"user_id": USER_A},
        ).scalar_one()

    with engine.begin() as connection:
        _set_user(connection, USER_B)
        assert connection.execute(
            text("SELECT id FROM saved_jobs WHERE id = :id"),
            {"id": saved_job_id},
        ).all() == []
        assert connection.execute(
            text("SELECT id FROM saved_reports WHERE id = :id"),
            {"id": saved_report_id},
        ).all() == []
        assert connection.execute(
            text("UPDATE saved_jobs SET title = 'stolen' WHERE id = :id"),
            {"id": saved_job_id},
        ).rowcount == 0
        assert connection.execute(
            text("DELETE FROM saved_reports WHERE id = :id"),
            {"id": saved_report_id},
        ).rowcount == 0

    with engine.connect() as connection:
        transaction = connection.begin()
        _set_user(connection, USER_B)
        with pytest.raises(DBAPIError):
            connection.execute(
                text(
                    """
                    INSERT INTO saved_jobs (
                        user_id, source, company, title, description, extracted_skills_json
                    ) VALUES (
                        :other_user, 'test', 'Example Co', 'Impersonated', 'Blocked', '[]'
                    )
                    """
                ),
                {"other_user": USER_A},
            )
        transaction.rollback()

    with engine.begin() as connection:
        _set_user(connection, USER_A)
        assert connection.execute(
            text("SELECT title FROM saved_jobs WHERE id = :id"),
            {"id": saved_job_id},
        ).scalar_one() == "Engineer"
        assert connection.execute(
            text("SELECT title FROM saved_reports WHERE id = :id"),
            {"id": saved_report_id},
        ).scalar_one() == "Private report"


def test_career_plan_root_and_child_rls_follow_parent_ownership(
    postgres_security: PostgresSecurityFixture,
) -> None:
    engine = postgres_security.runtime_engine

    with Session(engine) as session:
        bind_authenticated_user(session, USER_A)
        run = CareerPlanRunDB(
            user_id=USER_A,
            status="draft",
            schema_version="8.1.1",
            run_version=1,
            attempt_count=0,
            goal_json="{}",
            search_summary_json="{}",
            proposal_json="{}",
            approval_json="{}",
            fallback_status="not_requested",
            resume_required_to_resume=False,
        )
        session.add(run)
        session.flush()
        session.add(
            CareerPlanStepDB(
                run_id=run.id,
                step_name="search",
                status="completed",
                attempt=1,
                safe_output_summary_json="{}",
                latency_ms=1.0,
            )
        )
        session.add(
            CareerPlanAuditEventDB(
                run_id=run.id,
                sequence_number=1,
                event_type="rls_test",
                safe_payload_json="{}",
            )
        )
        session.commit()

        # refresh starts a new transaction. The Session after_begin hook must
        # reapply USER_A or forced RLS would hide the row from its creator.
        session.refresh(run)
        run_id = run.id
        assert run.user_id == USER_A

    with engine.begin() as connection:
        _set_user(connection, USER_B)
        assert connection.execute(
            text("SELECT id FROM career_plan_runs WHERE id = :id"),
            {"id": run_id},
        ).all() == []
        assert connection.execute(
            text("SELECT id FROM career_plan_steps WHERE run_id = :id"),
            {"id": run_id},
        ).all() == []
        assert connection.execute(
            text("SELECT id FROM career_plan_audit_events WHERE run_id = :id"),
            {"id": run_id},
        ).all() == []

    with engine.connect() as connection:
        transaction = connection.begin()
        _set_user(connection, USER_B)
        with pytest.raises(DBAPIError):
            connection.execute(
                text(
                    """
                    INSERT INTO career_plan_steps (
                        run_id, step_name, status, attempt,
                        safe_output_summary_json, latency_ms
                    ) VALUES (
                        :run_id, 'attack', 'pending', 1, '{}', 0
                    )
                    """
                ),
                {"run_id": run_id},
            )
        transaction.rollback()

    with engine.begin() as connection:
        _set_user(connection, USER_A)
        assert connection.execute(
            text("SELECT count(*) FROM career_plan_steps WHERE run_id = :id"),
            {"id": run_id},
        ).scalar_one() == 1
        assert connection.execute(
            text("SELECT count(*) FROM career_plan_audit_events WHERE run_id = :id"),
            {"id": run_id},
        ).scalar_one() == 1


def test_transaction_local_identity_does_not_leak_through_pool(
    postgres_security: PostgresSecurityFixture,
) -> None:
    engine = postgres_security.runtime_engine

    with Session(engine) as session:
        bind_authenticated_user(session, USER_A)
        own_count = session.execute(text("SELECT count(*) FROM saved_jobs")).scalar_one()
        assert own_count >= 1
        session.commit()
        # A new transaction on the same Session must get USER_A again.
        assert session.execute(text("SELECT count(*) FROM saved_jobs")).scalar_one() == own_count

    # A new request/session with no authenticated context must inherit nothing
    # from the pooled PostgreSQL connection.
    with Session(engine) as session:
        assert session.execute(text("SELECT count(*) FROM saved_jobs")).scalar_one() == 0

    with Session(engine) as session:
        bind_authenticated_user(session, USER_B)
        assert session.execute(text("SELECT count(*) FROM saved_jobs")).scalar_one() == 0


def test_runtime_role_cannot_disable_rls_to_read_hidden_rows(
    postgres_security: PostgresSecurityFixture,
) -> None:
    engine = postgres_security.runtime_engine

    with engine.connect() as connection:
        transaction = connection.begin()
        _set_user(connection, USER_B)
        connection.execute(text("SET LOCAL row_security = off"))
        with pytest.raises(DBAPIError):
            connection.execute(text("SELECT id FROM saved_jobs"))
        transaction.rollback()
