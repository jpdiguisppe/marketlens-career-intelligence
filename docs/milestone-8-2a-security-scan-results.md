# Milestone 8.2A — Security Audit and Immediate Hardening Results

## Validated functional candidate

`afdeb545c1a4fbfd84ff33a3cc49a088d6234976`

Documentation-only descendants must rerun the same gates before merge.

## Decision

```text
NO CONFIRMED ACTIVE DATA BREACH OR CRITICAL EXPLOIT FOUND
8.2A AUDIT BASELINE AND IMMEDIATE DEPENDENCY/AUTH HARDENING: GO
OVERALL MILESTONE 8.2 SECURITY SIGN-OFF: NO-GO UNTIL RLS AND REMAINING HARDENING COMPLETE
```

The initial audit found vulnerable framework, upload-parser, test, and frontend build dependencies. This branch patches the directly remediable findings, separates runtime and development dependencies, adds a production authentication startup boundary, and establishes permanent security gates. PostgreSQL-native RLS, least-privilege database roles, browser headers, parser resource controls, distributed abuse protection, container hardening, and final production validation remain separate workstreams.

## Validated results

| Check | Result |
| --- | ---: |
| Backend tests | 535 / 535 passed |
| Frontend production build | Passed |
| Backend Docker image | Passed |
| Frontend Docker image | Passed |
| Python runtime dependency audit | 0 unreviewed findings |
| Python development dependency audit | 0 unreviewed findings |
| npm production dependency audit | 0 findings |
| npm full dependency audit | 0 findings |
| Bandit medium/high findings | 0 |
| Bandit recorded low findings | 4 reviewed |
| CodeQL Python | Passed |
| CodeQL JavaScript/TypeScript | Passed |
| Secret and log safety | Passed |
| Provider resilience | Passed |
| Provider telemetry | Passed |
| Operational reliability | Passed |
| Career Plan agent evaluation | Passed |
| Semantic extraction | Passed |
| Personalized coaching | Passed |
| Evidence provenance | Passed |

## Dependency remediation

### Backend runtime

The following internet-facing dependencies were upgraded:

- `fastapi`: `0.115.6` → `0.139.2`
- `starlette`: `0.41.3` → `1.3.1`
- `python-multipart`: `0.0.20` → `0.0.32`

The previous Starlette and multipart advisories no longer appear in the candidate audit.

### Backend development dependencies

`pytest` was removed from the production requirements and moved to `backend/requirements-dev.txt` at version `9.1.1`. The backend production image therefore no longer intentionally ships test tooling.

Every workflow that runs pytest now installs `requirements-dev.txt`; evaluation-only workflows continue using runtime dependencies.

### Frontend dependency tree

Production dependencies are now limited to Clerk and React packages. Build tooling was moved to `devDependencies` and refreshed through an Actions-generated lockfile:

- `@clerk/react`: `6.12.8`
- `vite`: `7.3.6`
- `@vitejs/plugin-react`: `5.2.0`
- resolved `esbuild`: `0.28.1`
- `typescript`: `5.6.3`

The generated tree passed `npm ci`, the production build, `npm audit --omit=dev`, and the full npm audit.

## Reviewed cryptography exceptions

`clerk-backend-api==6.0.1` currently constrains its transitive `cryptography` dependency below the fully fixed versions. Three exact advisories are temporarily excluded from the blocking result:

- `PYSEC-2026-3552`
- `PYSEC-2026-3553`
- `PYSEC-2026-3554`

MarketLens does not call the affected PKCS#7 decryption or certificate-chain verification APIs. These are not blanket package exceptions: every other advisory remains blocking. The rationale, affected code paths, expiration, and required removal conditions are recorded in [`security-dependency-exceptions.md`](security-dependency-exceptions.md).

The exception expires on 2026-09-30 or at Milestone 8.2B completion, whichever comes first. The preferred resolution is an updated Clerk dependency chain or a reviewed replacement authentication verification path.

## Production authentication boundary

Development authentication now fails during module startup when either condition is true:

- `MARKETLENS_ENVIRONMENT` is `prod` or `production`; or
- any recognized Railway runtime marker is present.

Permanent tests verify:

- local development authentication remains available for tests;
- explicit production rejects development authentication;
- each Railway runtime marker rejects development authentication;
- Clerk/non-development mode remains valid on Railway; and
- the startup error never contains the configured development bearer token.

## Static source analysis

Bandit records four low findings while blocking every medium/high finding:

1. two environment-variable names mistaken for hardcoded passwords;
2. one bounded deployment-canary polling exception handler; and
3. one bounded occupation-audit polling exception handler.

The credential-name findings contain no secret values. The two polling findings are limited to validation tooling and remain visible for future cleanup. The medium/high Bandit report is empty.

CodeQL `security-extended` analysis completed successfully for Python and JavaScript/TypeScript.

## Safe production surface baseline

The bounded live probe used only GET and OPTIONS requests against the currently deployed pre-remediation revision.

### Authentication boundary

| Route | Unauthenticated result |
| --- | ---: |
| `/me` | 401 |
| `/saved-jobs` | 401 |
| `/saved-reports` | 401 |
| `/career-plans` | 401 |

### CORS

- the configured production frontend origin was explicitly allowed;
- `https://attacker.invalid` was rejected;
- no wildcard origin was observed.

### Remaining public exposure and headers

- `/docs` and `/openapi.json` remain public;
- the frontend and backend do not yet send the complete planned CSP, frame, MIME-sniffing, referrer, permissions, and HSTS header set.

These are tracked for 8.2D and must be retested after deployment.

## Database isolation status

Application-level ownership checks remain present for saved jobs, saved reports, and Career Plans, and no reviewed cross-user IDOR was found. PostgreSQL-native RLS is still absent.

Therefore this branch does **not** claim database-enforced tenant isolation. A compromised runtime database credential or future missing ownership predicate would not yet be independently stopped by PostgreSQL.

Milestone 8.2C must add:

- versioned migrations;
- separate owner/migration and restricted runtime roles;
- request-local authenticated user context;
- enabled and forced RLS on user-owned root tables;
- ownership-aware child-table policies;
- revoked unnecessary privileges; and
- direct two-user tests using the real restricted runtime role.

## Remaining work before overall security GO

1. Complete 8.2C PostgreSQL RLS and least privilege.
2. Add parser/decompression limits for PDF and DOCX uploads.
3. Replace or supplement process-local rate limiting and document trusted proxy behavior.
4. Add browser/API security headers and decide whether production docs remain public.
5. Run containers as non-root and add image/SBOM scanning.
6. Update `SECURITY.md`, incident-response guidance, data-handling documentation, and residual-risk records.
7. Deploy an exact candidate revision and rerun authenticated, unauthenticated, RLS, header, leakage, and production-canary checks.

Until the final 8.2 sign-off, MarketLens remains a portfolio/demo service and should not receive secrets, government identifiers, medical records, confidential employer data, or other highly sensitive information.
