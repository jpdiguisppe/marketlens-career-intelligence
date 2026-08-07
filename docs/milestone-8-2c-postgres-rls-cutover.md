# Milestone 8.2C — PostgreSQL RLS Production Cutover

## Purpose

This runbook describes the controlled production rollout for MarketLens database-enforced tenant isolation. It separates schema/security administration from the application runtime and keeps the existing application-level ownership predicates as a second independent control.

This document intentionally contains no database URLs, passwords, tokens, or other credentials.

## Target state

After cutover:

- the backend `DATABASE_URL` authenticates as a restricted non-owner runtime role
- the runtime role is `NOSUPERUSER`, `NOCREATEDB`, `NOCREATEROLE`, `NOINHERIT`, and `NOBYPASSRLS`
- the runtime role cannot create schema objects or administer RLS
- `saved_jobs`, `saved_reports`, and `career_plan_runs` have forced RLS ownership policies
- `career_plan_steps` and `career_plan_audit_events` are visible/writable only through ownership of their parent Career Plan run
- each authenticated request binds the Clerk/dev user ID through transaction-local `app.current_user_id`
- every new SQLAlchemy transaction reapplies that identity automatically
- pooled PostgreSQL connections do not retain one request's user identity
- PostgreSQL schema/security changes use a separate migration/owner credential that is never the application runtime credential

## Pre-cutover requirements

Do not touch production until all of these are true:

1. PR #123 is reviewed, approved, merged, and deployed with the existing production database credential.
2. The deployed backend reports the exact merged revision and normal health/canary checks are green.
3. The dedicated ephemeral PostgreSQL RLS gate passes all direct two-user isolation tests.
4. Full backend, frontend, Docker, security, provider, and reliability gates are green.
5. A current database backup/snapshot is available through the database provider.
6. The current PostgreSQL administration credential is available only to the person performing the migration.
7. A strong unique password has been generated for the restricted runtime role and is stored only in the deployment secret manager.
8. The production database role is confirmed capable of creating/altering the restricted runtime role. If the provider does not grant that capability, stop and use the provider-supported role-management path instead of weakening the migration.

## Why the code must deploy before RLS is enabled

The pre-8.2C backend does not set `app.current_user_id`. Enabling RLS before the new backend code is live would cause private saved-data requests to lose database visibility.

The safe ordering is therefore:

1. deploy the RLS-aware code while the database is still unchanged
2. verify the application
3. place the backend in a short maintenance window
4. run the database security migration
5. replace the backend runtime database credential with the restricted role credential
6. restart/redeploy immediately
7. verify database and application isolation

Do not enable the production policies first and leave the old application running against them.

## Phase 1 — Deploy RLS-aware application code

After PR #123 is merged:

1. Let Railway deploy the exact merge revision using the current `DATABASE_URL`.
2. Confirm `/health` succeeds.
3. Confirm `/deployment/status` reports the exact merge revision.
4. Run the existing production canaries.
5. Sign in with a normal account and verify saved jobs, saved reports, and Career Plans still read/write normally.

At this point the application knows how to set transaction-local user context, but production RLS has not yet been enabled.

## Phase 2 — Prepare secrets without exposing them

Create three deployment values through Railway/provider secret controls or a secure local shell that does not persist command history:

- `DATABASE_MIGRATION_URL` — existing administrative/owner PostgreSQL connection, used only for migration
- `DATABASE_RUNTIME_ROLE` — intended restricted role name, normally `marketlens_runtime`
- `DATABASE_RUNTIME_PASSWORD` — newly generated strong unique password

Never commit these values, paste them into GitHub issues/PRs, include them in screenshots, or echo them in CI logs.

The migration runner prints only success/failure classes and counts; it does not print credentials.

## Phase 3 — Short maintenance window

Because the migration enables `FORCE ROW LEVEL SECURITY`, avoid serving private writes during the role transition.

1. Temporarily stop or otherwise prevent backend user traffic.
2. Keep the PostgreSQL service running.
3. Run the migration from a trusted environment with the three migration values available as environment variables:

```bash
cd backend
python scripts/apply_database_security_migrations.py
```

Expected successful output indicates that migrations were applied or were already current, followed by restricted-role/forced-RLS verification.

The migration is designed to fail closed when:

- required MarketLens tables do not exist
- PostgreSQL is not being used
- the administration credential cannot create/harden the runtime role
- a prior security migration was recorded for a different runtime role
- the runtime role has unsafe PostgreSQL flags
- the runtime role can create schema objects
- forced RLS is missing
- the runtime role owns a protected table

Do not bypass a failed verification check to finish the cutover.

## Phase 4 — Switch the application to the restricted runtime role

Construct a new backend `DATABASE_URL` for the same PostgreSQL host, port, database, and connection options, but with the new restricted runtime username/password.

Store the complete URL only as the Railway backend secret value. Do not place it in source control or logs.

Then restart/redeploy the backend.

The migration/owner URL must not become the ongoing application `DATABASE_URL`.

## Phase 5 — Exact post-cutover verification

### Database role posture

Using the migration/administrative connection, verify the application runtime role:

- can log in
- is not superuser
- cannot create databases
- cannot create roles
- does not inherit other roles
- does not have `BYPASSRLS`
- does not own protected tables
- cannot create objects in the public schema
- cannot read the migration metadata table

### RLS posture

Verify `relrowsecurity = true` and `relforcerowsecurity = true` for:

- `saved_jobs`
- `saved_reports`
- `career_plan_runs`
- `career_plan_steps`
- `career_plan_audit_events`

### Application behavior

With User A:

- create/list/read/delete a saved job
- create/list/read/delete a saved report
- create/read/execute or otherwise exercise a Career Plan flow

With a separate User B:

- confirm User A's IDs do not become visible when IDs are guessed or substituted
- confirm User B's own data still functions normally

Existing API ownership filters should continue returning `404` for cross-user object access. RLS is the independent database backstop underneath those filters.

### Safe production canaries

Run the normal production health, deployment-status, Career Plan, provider/reliability, and security-surface checks against the exact cutover revision.

## Rollback plan

A rollback is an emergency recovery action, not the intended steady state.

If the restricted runtime credential is incorrect but the migration succeeded:

1. keep user traffic paused
2. correct the restricted runtime `DATABASE_URL`
3. restart the backend
4. re-run verification

If an RLS policy defect prevents legitimate access:

1. keep user traffic paused
2. restore the prior application revision/credential only long enough to diagnose safely
3. use the migration/owner path to repair the policy in a new versioned migration
4. do not permanently return the application to the owner credential
5. do not disable RLS as a routine workaround

If disabling RLS is required as a last-resort incident action, record the exact reason and duration, restrict traffic, and restore forced RLS before returning to normal operation.

## Credential lifecycle after success

- keep the runtime password only in deployment secret storage
- keep the migration/owner credential out of application runtime variables
- rotate the runtime password after suspected exposure or according to the project's credential-rotation policy
- rerun the security migration verifier after any database-role change
- never grant `BYPASSRLS`, table ownership, schema `CREATE`, or role-admin privileges to the application runtime role

## Acceptance evidence before 8.2C closes

8.2C should not be marked complete until the repository records:

- passing direct PostgreSQL two-user tests
- passing full application/security gates
- exact PR merge revision
- exact production deployment revision
- successful production migration verification
- successful restricted-runtime application verification
- confirmation that production `DATABASE_URL` no longer uses the migration/table-owner role
- no unresolved critical/high security finding introduced by the cutover
