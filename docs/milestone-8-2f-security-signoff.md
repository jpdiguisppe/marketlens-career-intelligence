# Milestone 8.2F — Final security sign-off

## Current decision

**PRE-SIGN-OFF — NO-GO FOR SENSITIVE DATA UNTIL THE PRODUCTION RLS CUTOVER AND LIVE TWO-USER ISOLATION TEST ARE COMPLETE.**

This document is the final release checklist for Milestone 8.2. It deliberately separates repository-proven controls from production controls that require owner-level Railway/PostgreSQL access.

## Repository-complete controls

The following work is expected to be complete and green before the production database cutover:

- threat model and security audit baseline
- production development-auth fail-closed guard
- Clerk authorized-party validation
- private-resource application ownership checks
- cross-user API authorization regression tests
- PostgreSQL forced-RLS migration and restricted-role provisioning logic
- transaction-local authenticated-user database context
- direct two-user PostgreSQL isolation and RLS-bypass tests on ephemeral PostgreSQL
- request-body and route-specific abuse limits
- trusted-proxy handling
- PDF/DOCX parser and decompression bounds
- production security headers and production docs shutdown
- non-root backend and frontend containers
- dependency audits, Bandit, CodeQL, and full-history secret/log scanning
- production image vulnerability scanning
- backend/frontend CycloneDX image SBOM evidence
- exact-revision production security-surface workflow
- current `SECURITY.md` and explicit residual-risk documentation

## Production checks that can run without private user credentials

Before final GO, record successful exact-revision evidence for:

- [ ] both Railway services deployed successfully for the final candidate SHA
- [ ] backend `/deployment/status` reports the exact final candidate SHA
- [ ] unauthenticated private routes return 401/403
- [ ] production `/docs`, `/redoc`, and `/openapi.json` are unavailable
- [ ] hostile CORS origins are rejected
- [ ] the deployed frontend origin is explicitly allowed
- [ ] frontend and backend required security headers are present
- [ ] backend API responses use no-store protection
- [ ] normal production health and Career Plan canaries pass
- [ ] occupation/provider/reliability production gates remain green

## Owner-required production database cutover

These steps require Railway/PostgreSQL owner access and must not be automated from ordinary CI:

- [ ] current production database backup/snapshot confirmed
- [ ] migration/owner credential available privately
- [ ] unique restricted runtime-role password created and stored only in Railway/provider secret storage
- [ ] short maintenance window established
- [ ] `backend/scripts/apply_database_security_migrations.py` succeeds using the owner/migration connection
- [ ] runtime role is verified non-owner, `NOBYPASSRLS`, unable to administer schema/RLS, and unable to read migration metadata
- [ ] RLS is enabled and forced on all five protected tables
- [ ] Railway backend `DATABASE_URL` is switched to the restricted runtime role
- [ ] owner/migration credential is absent from ongoing application runtime variables
- [ ] backend redeploy succeeds using the restricted credential

The detailed procedure and rollback plan are in `docs/milestone-8-2c-postgres-rls-cutover.md`.

## Two-independent-user live verification

After the restricted runtime credential is live:

User A should create/exercise:

- a saved job
- a saved report
- a Career Plan flow

Using a distinct User B account:

- [ ] User A's saved-job ID cannot be read, changed, or deleted by User B
- [ ] User A's saved-report ID cannot be read, changed, or deleted by User B
- [ ] User A's Career Plan/run data cannot be accessed by User B
- [ ] cross-user API access remains non-enumerating (`404` where designed)
- [ ] User B can still create/read/update/delete User B's own supported private data normally
- [ ] User A's data remains functional after the test

No test should attempt to extract unrelated real-user records. Use only test records created for this verification.

## Secret/private-data leakage verification

Before GO:

- [ ] production responses do not expose secrets, tokens, database URLs, or stack traces
- [ ] reviewed logs do not contain submitted resume/job-document bodies or authentication secrets
- [ ] migration output contains no credentials
- [ ] CI artifacts contain only intended security evidence and no production credentials/private user data

## Residual risks that may remain after GO

A final GO does not mean MarketLens is unhackable. At minimum, record and accept or remediate:

- process-local rate limiting rather than a distributed global quota
- a static admin API key rather than short-lived scoped administrator identity
- reviewed, time-bounded Clerk-transitive `cryptography` dependency exceptions if still unresolved
- Docker base images managed by tags/Dependabot rather than immutable digest pinning
- operational/privacy/legal work needed before collecting highly sensitive user data at scale
- no claim of external-user beta validation unless such testing actually occurs

## Final decision rule

### GO

Issue `GO — MILESTONE 8.2 SECURITY HARDENING COMPLETE` only when:

1. all repository and security gates are green on the final candidate,
2. both Railway services are verified on the exact revision,
3. the production database cutover is verified with the restricted role and forced RLS,
4. two independent live users pass the isolation checks,
5. no unresolved critical/high finding remains without an explicit accepted exception,
6. residual risks are recorded honestly.

### NO-GO

Remain NO-GO for sensitive production data if any required production RLS, isolation, critical/high security, secret-leakage, or exact-revision verification is missing or failing.
