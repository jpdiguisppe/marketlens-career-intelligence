# Milestone 8.2F — Final security sign-off

## Current decision

**GO — MILESTONE 8.2 SECURITY HARDENING COMPLETE.**

Milestone 8.2 completed final production security sign-off on 2026-08-11 after the repository security work, owner-controlled PostgreSQL restricted-runtime/RLS cutover, live two-independent-user isolation verification, and final owner evidence review were completed.

The functional production candidate used for final security evidence is:

```text
39570fb853be4f9cd670ea6d4670d334abcdd758
```

GitHub issue #122 records the completed PostgreSQL cutover evidence, and umbrella issue #120 records the final GO decision.

## Repository-complete controls

The following work is complete:

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

## Exact-revision public production checks

Successful evidence was recorded for candidate `39570fb853be4f9cd670ea6d4670d334abcdd758`:

- [x] both Railway services deployed successfully for the candidate SHA
- [x] backend `/deployment/status` reported the exact candidate SHA
- [x] unauthenticated private routes returned 401/403
- [x] production `/docs`, `/redoc`, and `/openapi.json` were unavailable
- [x] hostile CORS origins were rejected
- [x] the deployed frontend origin was explicitly allowed
- [x] frontend and backend required security headers were present
- [x] backend API responses used no-store protection where required
- [x] normal production health and public Career Plan canary checks passed
- [x] Production Security Surface verification passed on the exact candidate
- [x] occupation/provider/reliability gates were green on the candidate during the final security workstream

## Owner-required production database cutover

The live owner-controlled cutover completed successfully:

- [x] a pre-cutover production PostgreSQL backup was created on owner-controlled local Mac storage because Railway-managed backup/PITR is unavailable on the current plan
- [x] migration/owner credential was available privately for the migration
- [x] unique restricted runtime-role password was created and handled through private secret controls
- [x] `backend/scripts/apply_database_security_migrations.py` succeeded using the owner/migration connection
- [x] runtime role was verified non-owner, `NOBYPASSRLS`, unable to administer schema/RLS, and unable to read migration metadata
- [x] RLS was enabled and forced on all five protected tables
- [x] Railway backend `DATABASE_URL` was switched to the restricted runtime role
- [x] owner/migration connection was confirmed absent from ongoing application runtime variables
- [x] backend redeploy succeeded using the restricted credential
- [x] restricted-runtime default-deny behavior was verified with no request identity
- [x] an authenticated synthetic Career Plan create/execute/delete flow succeeded through the restricted runtime role

The detailed procedure and rollback plan remain in `docs/milestone-8-2c-postgres-rls-cutover.md`.

## Two-independent-user live verification

The final live verification used two distinct authenticated users and synthetic test records only.

User A successfully created and read:

- a saved job
- a saved report
- a Career Plan

Using User B:

- [x] User A's saved-job ID could not be read or deleted by User B; cross-user requests returned `404`
- [x] User A's saved-report ID could not be read or deleted by User B; cross-user requests returned `404`
- [x] User A's Career Plan could not be read, executed, or deleted by User B; cross-user requests returned `404`
- [x] cross-user API access remained non-enumerating where designed
- [x] User B could create/read/delete User B's own saved job, saved report, and Career Plan normally
- [x] User A's saved job, saved report, and Career Plan remained readable after User B's attempted access
- [x] the final synthetic User A/User B verification records were cleaned up successfully

No test attempted to extract unrelated real-user records.

## Secret/private-data leakage verification

Final review recorded:

- [x] production responses did not expose secrets, tokens, database URLs, or stack traces during the bounded verification
- [x] reviewed backend deployment logs around the verification window contained request metadata only and did not expose bearer/JWT tokens, database URLs/passwords, stack traces, or submitted test payload/document bodies
- [x] observed migration output contained no credentials
- [x] repository secret/log-safety and supply-chain evidence gates remained in place; no production credentials/private user data were intentionally placed in CI artifacts
- [x] backend service variables were reviewed with values masked; the ongoing runtime contained the intended `DATABASE_URL` and no migration/owner database connection variable

## Accepted residual risks

A final GO does not mean MarketLens is unhackable. The following residual risks remain documented and accepted for the current portfolio/demo scope:

- process-local rate limiting rather than a distributed global quota
- a static admin API key rather than short-lived scoped administrator identity
- reviewed, time-bounded Clerk-transitive `cryptography` dependency exceptions while the dependency chain remains constrained
- Docker base images managed by tags/Dependabot rather than immutable digest pinning
- Railway-managed backup/PITR unavailable on the current plan; the local owner-controlled backup procedure is the current rollback safeguard
- operational/privacy/legal work needed before intentionally collecting highly sensitive user data at scale
- no claim of external-user beta validation

## Final decision rule

The GO rule required:

1. repository and security gates green on the final candidate,
2. both Railway services verified on the exact revision,
3. production database cutover verified with the restricted role and forced RLS,
4. two independent live users passing isolation checks,
5. no unresolved critical/high finding without an explicit accepted exception,
6. residual risks recorded honestly.

All six conditions were satisfied for the Milestone 8.2 sign-off evidence above.

## Final record

**GO — MILESTONE 8.2 SECURITY HARDENING COMPLETE**

- 8.2C issue #122: closed as completed
- Milestone 8.2 umbrella issue #120: closed as completed
- functional production security candidate: `39570fb853be4f9cd670ea6d4670d334abcdd758`
