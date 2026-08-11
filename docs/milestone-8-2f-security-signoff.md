# Milestone 8.2F — Final security sign-off

## Current decision

**POST-CUTOVER PRE-SIGN-OFF — PRODUCTION RLS IS LIVE; FINAL GO REMAINS BLOCKED ON THE REMAINING MANUAL TWO-USER AND EVIDENCE CHECKS.**

This document is the final release checklist for Milestone 8.2. It deliberately separates repository-proven controls from production controls that require owner-level Railway/PostgreSQL access.

## Repository-complete controls

The following work is complete and green:

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

Successful exact-revision evidence has been recorded for production candidate `39570fb853be4f9cd670ea6d4670d334abcdd758`:

- [x] both Railway services deployed successfully for the candidate SHA
- [x] backend `/deployment/status` reports the exact candidate SHA
- [x] unauthenticated private routes return 401/403
- [x] production `/docs`, `/redoc`, and `/openapi.json` are unavailable
- [x] hostile CORS origins are rejected
- [x] the deployed frontend origin is explicitly allowed
- [x] frontend and backend required security headers are present
- [x] backend API responses use no-store protection
- [x] normal production health and public Career Plan canary checks pass
- [x] production security-surface verification passed on the exact candidate

Occupation/provider/reliability gates were green on the security candidate before the owner-controlled database cutover and remain part of the final evidence review.

## Owner-required production database cutover

The live cutover was performed on 2026-08-10. Current recorded state:

- [ ] current production database backup/snapshot confirmation recorded in final evidence
- [x] migration/owner credential was available privately for the migration
- [x] unique restricted runtime-role password was created and handled through private secret controls
- [x] `backend/scripts/apply_database_security_migrations.py` succeeded using the owner/migration connection
- [x] runtime role was verified non-owner, `NOBYPASSRLS`, unable to administer schema/RLS, and unable to read migration metadata
- [x] RLS is enabled and forced on all five protected tables
- [x] Railway backend `DATABASE_URL` was switched to the restricted runtime role
- [ ] owner/migration credential absence from ongoing application runtime variables recorded in final evidence
- [x] backend redeploy succeeded using the restricted credential
- [x] restricted-runtime default-deny behavior was verified with no request identity
- [x] an authenticated synthetic Career Plan create/execute/delete flow succeeded through the restricted runtime role

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
- [x] observed migration output contained no credentials
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
