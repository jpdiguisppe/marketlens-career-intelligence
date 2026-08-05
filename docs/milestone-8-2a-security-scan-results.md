# Milestone 8.2A — Initial Security Scan Results

## Candidate revision

`d4da9d3865046d49bf61bb905c148e6133eac485`

This record summarizes the first defensive scan of the completed Milestone 8 codebase. The audit PR remains unmerged while findings are classified and remediated.

## Executive result

```text
NO CONFIRMED ACTIVE DATA BREACH OR CRITICAL EXPLOIT FOUND
SECURITY SIGN-OFF: NO-GO UNTIL HIGH-PRIORITY DEPENDENCY AND DATABASE-ISOLATION WORK IS COMPLETE
```

The public deployment correctly rejected unauthenticated access to all four private route groups tested and correctly rejected a hostile CORS origin. Static application analysis did not identify a high-severity Python source finding. The audit did identify outdated framework/upload dependencies with published advisories, missing PostgreSQL RLS, missing browser/API security headers, and several defense-in-depth gaps that should be fixed before MarketLens is described as hardened for sensitive user data.

## Scanner execution

| Scanner | Result | Interpretation |
| --- | --- | --- |
| `pip-audit` 2.10.0 | Findings | Production and development Python dependencies include packages with published advisories |
| Bandit 1.9.4 | Four low findings | No medium or high Python source finding; reported items are reviewed below |
| npm production audit | Findings | Vite/esbuild development/build tooling has published advisories |
| npm full audit | Findings | Same Vite/esbuild set; no additional dependency category |
| CodeQL `security-extended` — Python | Completed successfully | Analysis initialized and uploaded successfully; no workflow-blocking analysis failure |
| CodeQL `security-extended` — JavaScript/TypeScript | Completed successfully | Analysis initialized and uploaded successfully; no workflow-blocking analysis failure |
| Existing secret/log safety | Passed | Full-history secret scan and safe-log/error tests remained green |
| Existing CI and permanent evaluations | Passed | Product tests/builds remained green; the audit-only changes did not alter runtime behavior |

## Python dependency findings

### `python-multipart==0.0.20`

**Classification:** High-priority production remediation

The scanner reported six advisories with fixes spread through versions 0.0.22 to 0.0.31. The most relevant MarketLens exposure is denial of service during multipart and form parsing. MarketLens accepts public résumé files and administrative CSV uploads, so this parser is on a reachable request path.

One advisory concerns path traversal only when non-default upload-directory/keep-filename options are used; MarketLens reads bounded uploads into memory and does not use that configuration, so that specific path-traversal scenario does not appear directly applicable. The multipart parsing denial-of-service advisories remain relevant.

**Required action:** upgrade to the current reviewed release, rerun all upload tests, and add malformed multipart/decompression resource regressions.

### `starlette==0.41.3`

**Classification:** High-priority framework remediation

The scanner reported advisories involving unvalidated host/path URL reconstruction, multipart spool/resource behavior, HTTP Range processing, and Windows-specific static-file/handler cases.

Not every advisory maps directly to MarketLens:

- the Windows UNC/static-file cases do not match the Linux Railway backend deployment and its current backend routing
- the Range/FileResponse case may not be reachable through a MarketLens endpoint that serves arbitrary files
- multipart resource handling and URL reconstruction are framework-level concerns on an internet-facing API and should not be left on an old release

Starlette is installed through FastAPI compatibility, so it should not be independently forced to an incompatible major version. The repair should upgrade FastAPI and Starlette together, then run the complete API, upload, auth, provider, and production-canary suites.

### `cryptography==48.0.1`

**Classification:** Medium-priority transitive remediation

Three advisories were reported involving PKCS#7 decryption and certificate-chain/name-constraint processing. MarketLens does not directly call those APIs in application code. The package is transitive, most likely through authentication/JWT dependencies. Direct exploitability has not been established, but the dependency should be upgraded through its owning dependency chain rather than ignored.

### `pytest==8.3.4`

**Classification:** Development/CI-only remediation

The reported local temporary-directory denial-of-service issue affects test execution on shared Unix systems. Pytest is not installed as an application runtime dependency by design intent, but it is currently listed in the shared requirements file used by the backend image, so the production image may contain unnecessary test tooling.

**Required action:** upgrade pytest and split runtime dependencies from development/test dependencies so test-only packages do not ship in the backend image.

## Frontend/build dependency findings

### `vite` and `esbuild`

**Classification:** Medium build/development remediation; lower direct production exploitability

The npm audit reported one high and one moderate dependency entry covering Vite path/Windows development-server behaviors and esbuild development-server request exposure. Railway serves the compiled frontend through Nginx, not the Vite development server, so the vulnerable server behavior is not the deployed production serving path.

The packages still participate in the build supply chain and should be upgraded. Vite and TypeScript build tooling should also be moved from `dependencies` to `devDependencies` so production-dependency reports accurately represent what is shipped.

## Bandit findings

Bandit reported four low-severity findings and no medium or high finding:

1. environment-variable name `AUTH_DEV_BEARER_TOKEN` was mistaken for a hardcoded password
2. environment-variable name `CLERK_SECRET_KEY` was mistaken for a hardcoded password
3. a bounded deployment-canary polling loop contains `except Exception: pass`
4. the production occupation-audit polling loop contains the same intentional pattern

The first two are false positives: the source contains environment-variable names, not secret values. The two canary findings are low-risk but should be made more explicit by catching expected network/parse exceptions or recording the last safe error rather than silently passing.

## Safe production surface results

The non-destructive live check made only bounded GET and OPTIONS requests.

### Authentication boundary

| Route | Unauthenticated result |
| --- | ---: |
| `/me` | 401 |
| `/saved-jobs` | 401 |
| `/saved-reports` | 401 |
| `/career-plans` | 401 |

All tested private route groups rejected unauthenticated access.

### CORS

- configured production frontend origin: explicitly allowed
- hostile origin `https://attacker.invalid`: rejected with HTTP 400
- hostile response did not include `Access-Control-Allow-Origin`
- wildcard origin was not observed

### Public route exposure

- frontend root: 200
- backend health: 200
- deployment status: 200
- Swagger UI `/docs`: 200
- OpenAPI schema `/openapi.json`: 200

Public API documentation is not itself an authentication bypass, but it improves endpoint enumeration. The final hardening decision should either disable it in production or explicitly accept and document the exposure.

### Security headers

Neither the frontend root response nor backend health response included:

- `Strict-Transport-Security`
- `Content-Security-Policy`
- `X-Content-Type-Options`
- `X-Frame-Options`
- `Referrer-Policy`
- `Permissions-Policy`

Both responses exposed `Server: railway-hikari`. This server header is low severity. The missing security headers are a medium defense-in-depth gap, especially the frontend CSP/frame/MIME protections.

## Database and user-data isolation result

Application-level ownership is consistently implemented in the reviewed saved-job, saved-report, and Career Plan endpoints. No confirmed cross-user IDOR was found in those routes, and existing two-user tests support that conclusion.

PostgreSQL-native RLS is not implemented in the repository. The database connection does not set a request-local authenticated user, migrations do not create RLS policies, and a restricted non-owner runtime role is not defined. Therefore:

- a normal API request is protected by application filters today
- a future forgotten ownership predicate would not be stopped by the database
- a compromised runtime database credential may be able to read all user-owned rows
- the current codebase cannot claim database-enforced tenant isolation

RLS must be enabled and forced using a runtime role that is neither the table owner nor a `BYPASSRLS` role. Direct two-user database tests are required; API tests alone are insufficient for this control.

## Immediate remediation order

1. Upgrade FastAPI/Starlette, `python-multipart`, cryptography dependency chain, pytest, Vite, and esbuild; split runtime and development dependencies.
2. Add a production startup guard that rejects development authentication.
3. Introduce migrations, a restricted runtime database role, request-local user context, and forced PostgreSQL RLS.
4. Add CSP and the remaining browser/API security headers; decide whether production docs remain public.
5. Harden parser resource limits, rate limiting, trusted-proxy handling, and the backend non-root container.
6. Add reviewed container scanning and SBOM generation before final sign-off.

## Current user guidance

Until Milestone 8.2 is signed off, MarketLens should continue being treated as a portfolio/demo application. Users should not upload secrets, government identifiers, medical records, confidential employer data, or other highly sensitive personal information.
