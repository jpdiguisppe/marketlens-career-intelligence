from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import psycopg2
from psycopg2 import sql

MIGRATION_URL_ENV = "DATABASE_MIGRATION_URL"
RUNTIME_ROLE_ENV = "DATABASE_RUNTIME_ROLE"
RUNTIME_PASSWORD_ENV = "DATABASE_RUNTIME_PASSWORD"
DEFAULT_RUNTIME_ROLE = "marketlens_runtime"
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
REQUIRED_TABLES = (
    "job_postings",
    "saved_jobs",
    "saved_reports",
    "career_plan_runs",
    "career_plan_steps",
    "career_plan_audit_events",
)
RLS_TABLES = (
    "saved_jobs",
    "saved_reports",
    "career_plan_runs",
    "career_plan_steps",
    "career_plan_audit_events",
)
ROOT_RLS_POLICIES = {
    "saved_jobs": "marketlens_saved_jobs_owner",
    "saved_reports": "marketlens_saved_reports_owner",
    "career_plan_runs": "marketlens_career_plan_runs_owner",
}
CHILD_RLS_POLICIES = {
    "career_plan_steps": "marketlens_career_plan_steps_owner",
    "career_plan_audit_events": "marketlens_career_plan_audit_events_owner",
}
EXPECTED_RLS_POLICIES = ROOT_RLS_POLICIES | CHILD_RLS_POLICIES


def _normalize_psycopg2_dsn(value: str) -> str:
    normalized = value.strip()
    sqlalchemy_prefix = "postgresql+psycopg2://"
    if normalized.startswith(sqlalchemy_prefix):
        return "postgresql://" + normalized[len(sqlalchemy_prefix) :]
    return normalized


def _require_setting(name: str, explicit_value: str | None = None) -> str:
    value = explicit_value if explicit_value is not None else os.getenv(name)
    normalized = (value or "").strip()
    if not normalized:
        raise RuntimeError(f"Required database security setting is missing: {name}.")
    return normalized


def _validate_runtime_role(role_name: str) -> str:
    normalized = role_name.strip()
    if not normalized or len(normalized.encode("utf-8")) > 63 or "\x00" in normalized:
        raise RuntimeError("Database runtime role name is invalid.")
    return normalized


def _ensure_required_tables(cursor: object) -> None:
    missing: list[str] = []
    for table_name in REQUIRED_TABLES:
        cursor.execute("SELECT to_regclass(%s)", (f"public.{table_name}",))
        if cursor.fetchone()[0] is None:
            missing.append(table_name)
    if missing:
        raise RuntimeError(
            "Database security migration requires the existing MarketLens schema; "
            f"missing tables: {', '.join(sorted(missing))}."
        )


def _ensure_migration_table(cursor: object) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS marketlens_schema_migrations (
            version TEXT PRIMARY KEY,
            runtime_role TEXT NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _runtime_role_memberships(cursor: object, role_name: str) -> list[str]:
    cursor.execute(
        """
        SELECT parent_role.rolname
        FROM pg_auth_members AS membership
        JOIN pg_roles AS member_role ON member_role.oid = membership.member
        JOIN pg_roles AS parent_role ON parent_role.oid = membership.roleid
        WHERE member_role.rolname = %s
        ORDER BY parent_role.rolname
        """,
        (role_name,),
    )
    return [row[0] for row in cursor.fetchall()]


def _ensure_runtime_role(cursor: object, role_name: str, password: str) -> None:
    cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role_name,))
    role_exists = cursor.fetchone() is not None

    role_identifier = sql.Identifier(role_name)
    password_literal = sql.Literal(password)
    hardened_options = sql.SQL(
        "LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS PASSWORD {}"
    ).format(password_literal)

    if role_exists:
        cursor.execute(
            sql.SQL("ALTER ROLE {} WITH ").format(role_identifier) + hardened_options
        )
    else:
        cursor.execute(
            sql.SQL("CREATE ROLE {} WITH ").format(role_identifier) + hardened_options
        )

    memberships = _runtime_role_memberships(cursor, role_name)
    if memberships:
        raise RuntimeError(
            "Database runtime role has role memberships that could permit SET ROLE escalation."
        )

    cursor.execute("SELECT current_database()")
    database_name = cursor.fetchone()[0]
    database_identifier = sql.Identifier(database_name)

    cursor.execute(
        sql.SQL("REVOKE CREATE, TEMPORARY ON DATABASE {} FROM PUBLIC").format(
            database_identifier
        )
    )
    cursor.execute(
        sql.SQL("REVOKE ALL PRIVILEGES ON DATABASE {} FROM {}").format(
            database_identifier,
            role_identifier,
        )
    )
    cursor.execute(
        sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
            database_identifier,
            role_identifier,
        )
    )


def _assert_role_consistency(cursor: object, role_name: str) -> None:
    cursor.execute("SELECT DISTINCT runtime_role FROM marketlens_schema_migrations")
    recorded_roles = {row[0] for row in cursor.fetchall()}
    if recorded_roles and recorded_roles != {role_name}:
        raise RuntimeError(
            "Existing database security migrations were applied for a different runtime role."
        )


def _apply_versioned_migrations(cursor: object, role_name: str) -> list[str]:
    applied_versions: list[str] = []
    migration_paths = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migration_paths:
        raise RuntimeError("No database security migrations were found.")

    for migration_path in migration_paths:
        version = migration_path.stem
        cursor.execute(
            "SELECT 1 FROM marketlens_schema_migrations WHERE version = %s",
            (version,),
        )
        if cursor.fetchone() is not None:
            continue

        template = migration_path.read_text(encoding="utf-8")
        rendered = sql.SQL(template).format(runtime_role=sql.Identifier(role_name))
        cursor.execute(rendered)
        cursor.execute(
            """
            INSERT INTO marketlens_schema_migrations (version, runtime_role)
            VALUES (%s, %s)
            """,
            (version, role_name),
        )
        applied_versions.append(version)

    return applied_versions


def _normalized_policy_expression(value: str | None) -> str:
    if not value:
        return ""
    normalized = re.sub(r"\s+", "", value.lower())
    normalized = normalized.replace("::text", "")
    normalized = normalized.replace("::name", "")
    return normalized


def _verify_root_policy_expression(expression: str, table_name: str) -> bool:
    normalized = _normalized_policy_expression(expression)
    return all(
        token in normalized
        for token in (
            "user_id",
            "nullif(",
            "current_setting('app.current_user_id',true)",
            "''",
            "=",
        )
    ) and "true" not in normalized.replace("current_setting('app.current_user_id',true)", "")


def _verify_child_policy_expression(expression: str, table_name: str) -> bool:
    normalized = _normalized_policy_expression(expression)
    return all(
        token in normalized
        for token in (
            "exists(",
            "career_plan_runs",
            f"career_plan_runs.id={table_name}.run_id",
            "career_plan_runs.user_id",
            "nullif(",
            "current_setting('app.current_user_id',true)",
            "''",
        )
    ) and "true" not in normalized.replace("current_setting('app.current_user_id',true)", "")


def _verify_policy_definitions(cursor: object, role_name: str) -> None:
    for table_name, expected_policy_name in EXPECTED_RLS_POLICIES.items():
        cursor.execute(
            """
            SELECT policyname, permissive, roles, cmd, qual, with_check
            FROM pg_policies
            WHERE schemaname = 'public' AND tablename = %s
            ORDER BY policyname
            """,
            (table_name,),
        )
        policies = cursor.fetchall()
        if len(policies) != 1:
            raise RuntimeError(
                f"RLS policy verification expected exactly one policy for {table_name}."
            )

        policy_name, permissive, roles, command, using_expression, check_expression = policies[0]
        if policy_name != expected_policy_name:
            raise RuntimeError(f"Unexpected RLS policy name for {table_name}.")
        if permissive != "PERMISSIVE" or command != "ALL":
            raise RuntimeError(f"Unexpected RLS policy mode for {table_name}.")
        if set(roles or []) != {role_name}:
            raise RuntimeError(f"Unexpected RLS policy role scope for {table_name}.")
        if not using_expression or not check_expression:
            raise RuntimeError(f"RLS policy predicates are incomplete for {table_name}.")

        verifier = (
            _verify_root_policy_expression
            if table_name in ROOT_RLS_POLICIES
            else _verify_child_policy_expression
        )
        if not verifier(using_expression, table_name) or not verifier(check_expression, table_name):
            raise RuntimeError(f"RLS policy predicate verification failed for {table_name}.")


def _verify_security_posture(cursor: object, role_name: str) -> None:
    cursor.execute(
        """
        SELECT rolsuper, rolcreatedb, rolcreaterole, rolinherit, rolbypassrls, rolcanlogin
        FROM pg_roles
        WHERE rolname = %s
        """,
        (role_name,),
    )
    role_row = cursor.fetchone()
    if role_row is None:
        raise RuntimeError("Database runtime role verification failed.")

    rolsuper, rolcreatedb, rolcreaterole, rolinherit, rolbypassrls, rolcanlogin = role_row
    if any((rolsuper, rolcreatedb, rolcreaterole, rolinherit, rolbypassrls)) or not rolcanlogin:
        raise RuntimeError("Database runtime role has unsafe PostgreSQL attributes.")

    if _runtime_role_memberships(cursor, role_name):
        raise RuntimeError("Database runtime role retains unsafe role memberships.")

    cursor.execute(
        "SELECT has_schema_privilege(%s, 'public', 'CREATE')",
        (role_name,),
    )
    if cursor.fetchone()[0]:
        raise RuntimeError("Database runtime role still has schema CREATE privilege.")

    cursor.execute(
        "SELECT has_table_privilege(%s, 'marketlens_schema_migrations', 'SELECT')",
        (role_name,),
    )
    if cursor.fetchone()[0]:
        raise RuntimeError("Database runtime role can read migration metadata.")

    for table_name in RLS_TABLES:
        cursor.execute(
            """
            SELECT c.relrowsecurity, c.relforcerowsecurity, owner_role.rolname
            FROM pg_class AS c
            JOIN pg_namespace AS n ON n.oid = c.relnamespace
            JOIN pg_roles AS owner_role ON owner_role.oid = c.relowner
            WHERE n.nspname = 'public' AND c.relname = %s
            """,
            (table_name,),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError(f"RLS verification table is missing: {table_name}.")
        rls_enabled, rls_forced, owner_name = row
        if not rls_enabled or not rls_forced:
            raise RuntimeError(f"Forced RLS verification failed for {table_name}.")
        if owner_name == role_name:
            raise RuntimeError(f"Runtime role must not own RLS table {table_name}.")

    _verify_policy_definitions(cursor, role_name)


def apply_database_security_migrations(
    migration_url: str,
    runtime_role: str,
    runtime_password: str,
) -> list[str]:
    dsn = _normalize_psycopg2_dsn(_require_setting(MIGRATION_URL_ENV, migration_url))
    role_name = _validate_runtime_role(_require_setting(RUNTIME_ROLE_ENV, runtime_role))
    password = _require_setting(RUNTIME_PASSWORD_ENV, runtime_password)

    if not dsn.startswith(("postgresql://", "postgres://")):
        raise RuntimeError("Database security migrations require PostgreSQL.")

    connection = psycopg2.connect(dsn)
    try:
        with connection:
            with connection.cursor() as cursor:
                _ensure_required_tables(cursor)
                _ensure_migration_table(cursor)
                _assert_role_consistency(cursor, role_name)
                _ensure_runtime_role(cursor, role_name, password)
                applied = _apply_versioned_migrations(cursor, role_name)
                _verify_security_posture(cursor, role_name)
        return applied
    finally:
        connection.close()


def main() -> int:
    try:
        migration_url = _require_setting(MIGRATION_URL_ENV)
        runtime_role = os.getenv(RUNTIME_ROLE_ENV, DEFAULT_RUNTIME_ROLE)
        runtime_password = _require_setting(RUNTIME_PASSWORD_ENV)
        applied = apply_database_security_migrations(
            migration_url,
            runtime_role,
            runtime_password,
        )
    except Exception as exc:
        print(
            f"Database security migration failed safely ({type(exc).__name__}).",
            file=sys.stderr,
        )
        return 1

    if applied:
        print(f"Applied {len(applied)} database security migration(s).")
    else:
        print("Database security migrations are already current.")
    print("Restricted runtime role and forced RLS verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
