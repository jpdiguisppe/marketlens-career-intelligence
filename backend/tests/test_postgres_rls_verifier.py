from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text

from app.database import Base
from app.models import JobPostingDB, SavedJobDB, SavedReportDB  # noqa: F401
from app.career_plans.models import CareerPlanAuditEventDB, CareerPlanRunDB, CareerPlanStepDB  # noqa: F401
from scripts.apply_database_security_migrations import apply_database_security_migrations

POSTGRES_TEST_URL_ENV = "MARKETLENS_POSTGRES_TEST_URL"
RUNTIME_ROLE = "marketlens_runtime_verifier_test"
RUNTIME_PASSWORD = "marketlens-runtime-verifier-password"
PARENT_ROLE = "marketlens_runtime_parent_test"

pytestmark = pytest.mark.skipif(
    not os.getenv(POSTGRES_TEST_URL_ENV),
    reason="PostgreSQL RLS verifier tests require MARKETLENS_POSTGRES_TEST_URL.",
)


@pytest.fixture(scope="module")
def migrated_admin_engine():
    admin_url = os.environ[POSTGRES_TEST_URL_ENV]
    engine = create_engine(admin_url)

    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS marketlens_schema_migrations"))
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    applied = apply_database_security_migrations(
        admin_url,
        RUNTIME_ROLE,
        RUNTIME_PASSWORD,
    )
    assert applied == ["0001_force_user_data_rls"]

    try:
        yield admin_url, engine
    finally:
        with engine.begin() as connection:
            connection.execute(text(f"REVOKE {PARENT_ROLE} FROM {RUNTIME_ROLE}"))
            connection.execute(text(f"DROP ROLE IF EXISTS {PARENT_ROLE}"))
            connection.execute(text("DROP TABLE IF EXISTS marketlens_schema_migrations"))
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_verifier_rejects_runtime_role_membership(
    migrated_admin_engine: tuple[str, object],
) -> None:
    admin_url, engine = migrated_admin_engine

    with engine.begin() as connection:
        connection.execute(text(f"DROP ROLE IF EXISTS {PARENT_ROLE}"))
        connection.execute(text(f"CREATE ROLE {PARENT_ROLE} NOLOGIN"))
        connection.execute(text(f"GRANT {PARENT_ROLE} TO {RUNTIME_ROLE}"))

    with pytest.raises(RuntimeError, match="role memberships"):
        apply_database_security_migrations(
            admin_url,
            RUNTIME_ROLE,
            RUNTIME_PASSWORD,
        )

    with engine.begin() as connection:
        connection.execute(text(f"REVOKE {PARENT_ROLE} FROM {RUNTIME_ROLE}"))
        connection.execute(text(f"DROP ROLE {PARENT_ROLE}"))

    assert apply_database_security_migrations(
        admin_url,
        RUNTIME_ROLE,
        RUNTIME_PASSWORD,
    ) == []


def test_verifier_rejects_permissive_policy_drift(
    migrated_admin_engine: tuple[str, object],
) -> None:
    admin_url, engine = migrated_admin_engine

    with engine.begin() as connection:
        connection.execute(text("DROP POLICY marketlens_saved_jobs_owner ON saved_jobs"))
        connection.execute(
            text(
                f"""
                CREATE POLICY marketlens_saved_jobs_owner
                ON saved_jobs
                FOR ALL
                TO {RUNTIME_ROLE}
                USING (true)
                WITH CHECK (true)
                """
            )
        )

    with pytest.raises(RuntimeError, match="predicate verification failed"):
        apply_database_security_migrations(
            admin_url,
            RUNTIME_ROLE,
            RUNTIME_PASSWORD,
        )

    with engine.begin() as connection:
        connection.execute(text("DROP POLICY marketlens_saved_jobs_owner ON saved_jobs"))
        connection.execute(
            text(
                f"""
                CREATE POLICY marketlens_saved_jobs_owner
                ON saved_jobs
                FOR ALL
                TO {RUNTIME_ROLE}
                USING (
                    user_id = NULLIF(current_setting('app.current_user_id', true), '')
                )
                WITH CHECK (
                    user_id = NULLIF(current_setting('app.current_user_id', true), '')
                )
                """
            )
        )

    assert apply_database_security_migrations(
        admin_url,
        RUNTIME_ROLE,
        RUNTIME_PASSWORD,
    ) == []
