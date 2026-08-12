# Milestone 8.2C — PostgreSQL RLS Production Cutover

## Purpose

This runbook describes the controlled production rollout for MarketLens database-enforced tenant isolation. It separates schema/security administration from the application runtime and keeps the existing application-level ownership predicates as a second independent control.

This document intentionally contains no database URLs, passwords, tokens, or other credentials.

## Current production status

**COMPLETE — production restricted-runtime/RLS cutover and post-cutover isolation verification succeeded.**

The live restricted-runtime cutover and final verification were completed against functional production candidate:

```text
39570fb853be4f9cd670ea6d4670d334abcdd758
```

Recorded production evidence:

- `backend/scripts/apply_database_security_migrations.py` completed successfully and reported restricted-role/forced-RLS verification success
- the runtime role was verified as login-capable, non-superuser, unable to create databases or roles, `NOINHERIT`, and `NOBYPASSRLS`
- the runtime role does not own protected tables, cannot create objects in the public schema, and cannot read migration metadata
- RLS is enabled and forced on `saved_jobs`, `saved_reports`, `career_plan_runs`, `career_plan_steps`, and `career_plan_audit_events`
- Railway backend `DATABASE_URL` was switched to the restricted runtime role and the backend redeployed successfully
- `/health` and `/deployment/status` returned healthy responses on the exact functional production candidate
- a direct restricted-runtime check showed default-deny behavior with no authenticated request identity
- an authenticated synthetic Career Plan flow returned `201` on create, `200` on execute, reached `awaiting_approval` with seven persisted steps, and returned `200` on cleanup
- two distinct live users passed post-cutover isolation checks: User B received `404` for User A saved-job read/delete, saved-report read/delete, and Career Plan read/execute/delete attempts
- User B's own saved-job, saved-report, and Career Plan create/read/delete operations worked normally
- User A's records remained intact after User B's attempted access and the final synthetic verification records were cleaned up successfully
- the ongoing backend variable set was reviewed with values masked and contained the intended runtime database connection but no migration/owner database connection variable
- backend production logs around the verification window were reviewed and exposed request metadata only, with no observed bearer/JWT tokens, database credentials, stack traces, or submitted test payload/document bodies
- Railway-managed backup/PITR is unavailable on the current plan; a pre-cutover production PostgreSQL backup was created on owner-controlled local Mac storage as the rollback safeguard

Milestone 8.2C issue #122 and umbrella issue #120 are closed as completed. The final GO record is in `docs/milestone-8-2f-security-signoff.md` and issue #120.

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

The production state above now matches this target posture.

## Pre-cutover requirements

Do not touch production until all of these are true:

1. PR #123 is reviewed, approved, merged, and deployed with the existing production database credential.
2. The deployed backend reports the exact merged revision and normal health/canary checks are green.
3. The dedicated ephemeral PostgreSQL RLS gate passes all direct two-user isolation tests.
4. Full backend, frontend, Docker, security, provider, and reliability gates are green.
5. A current rollback backup is available through the database provider or an owner-controlled database dump stored outside the application runtime.
6. The current PostgreSQL administration credential is available only to the person performing the migration.
7. A strong unique password has been generated for the restricted runtime role and is stored only in the deployment secret manager.
8. The production database role is confirmed capable of creating/altering the restricted runtime role. If the provider does not grant that capability, stop and use the provider-supported role-management path instead of weakening the migration.

For the completed MarketLens cutover, Railway-managed backup/PITR was unavailable on the current plan, so the rollback backup was created locally on owner-controlled Mac storage before the migration.

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

All required 8.2C evidence has now been recorded:

- [x] passing direct PostgreSQL two-user tests
- [x] passing full application/security gates
- [x] exact PR merge revision
- [x] exact production deployment revision
- [x] successful production migration verification
- [x] successful restricted-runtime application verification
- [x] confirmation that production `DATABASE_URL` no longer uses the migration/table-owner role
- [x] post-cutover live two-user isolation for saved jobs, saved reports, and Career Plans
- [x] no unresolved critical/high security finding introduced by the cutover outside the explicit reviewed exception policy

Milestone 8.2C is complete.
