# Milestone 8.2 — Security Threat Model and Audit Baseline

## Status

Initial defensive audit baseline. This document records confirmed controls, unverified production assumptions, and prioritized hardening work. It does not claim that MarketLens is unhackable or that a destructive penetration test was performed.

## Scope and safety boundary

This review covers:

- FastAPI authentication, authorization, administration, validation, error handling, and rate limiting
- SQLAlchemy/PostgreSQL data access and user isolation
- Career Plan, saved-job, and saved-report ownership
- public job-provider and model-provider outbound requests
- résumé and CSV uploads
- React rendering, external links, and Nginx behavior
- secrets, logs, dependencies, CI, containers, and deployment configuration

Allowed validation is static analysis, dependency and container scanning, unit/integration tests, and bounded non-destructive production checks. Denial-of-service testing, credential attacks, destructive writes, data extraction, and exploitation of third-party systems are out of scope.

## Protected assets

1. Clerk session tokens and authenticated user identities
2. saved jobs and their descriptions
3. saved Smart Fit reports
4. Career Plan goals, proposals, decisions, safe summaries, and audit history
5. database credentials, Clerk secret key, admin API key, and model-provider key
6. production integrity and service availability
7. third-party provider quotas and model-provider spending
8. repository and deployment supply chain

Raw résumé text is intended to be processed only for the request and is not stored in shared application tables. The system should continue treating résumé and job text as untrusted, potentially sensitive input.

## Trust boundaries

- browser to Railway frontend
- browser to Railway FastAPI backend
- FastAPI backend to Clerk token verification
- FastAPI backend to PostgreSQL
- FastAPI backend to configured public job providers
- FastAPI backend to the optional model provider
- GitHub Actions to repository, package registries, container registries, and Railway deployment
- administrator to static admin-key-protected shared-posting routes

## Attacker profiles

- unauthenticated internet client probing public endpoints
- authenticated user attempting to read, modify, or delete another user's records
- automated client attempting resource exhaustion or provider-cost amplification
- attacker who obtains a leaked bearer token, admin key, provider key, or database credential
- malicious résumé, job description, URL, PDF, DOCX, or provider payload
- compromised or vulnerable dependency, base image, GitHub Action, or package registry artifact
- application bug that omits an ownership filter

## Confirmed controls

### Authentication

- private routes use a bearer-token dependency
- production authentication uses Clerk and requires configured authorized parties
- missing or invalid authentication fails closed
- development-token comparison and admin-key comparison use constant-time checks

### Application-level user authorization

- saved-job reads and deletes query by both object ID and authenticated user ID
- saved-report reads and deletes query by both object ID and authenticated user ID
- Career Plan reads, execution, explanation, cancellation, decisions, and deletion load the run through an ID-plus-user-ID ownership query
- another user's missing/unauthorized object is returned as `404`
- cross-user saved-job, saved-report, and Career Plan behavior has automated coverage

### Injection and unsafe execution

- application database access uses SQLAlchemy ORM
- no application-path raw string-built SQL, `eval`, unsafe YAML load, pickle deserialization, or shell execution was found in the reviewed source
- user input does not select arbitrary job-provider URLs; provider base URLs are fixed and board identifiers are resolved through an allowlisted registry
- external application links are display-only and must use public HTTPS without embedded credentials or literal private/local addresses

### Input and output safety

- Pydantic models apply field and collection bounds
- résumé, CSV, job-search, batch-analysis, provider-request, model-call, and Career Plan limits exist
- validation errors do not echo rejected values
- unhandled errors return a generic response
- logs redact configured credentials, bearer tokens, credential-bearing URLs, common secret formats, and request-scoped documents
- Career Plan audit payloads reject résumé, description, token, secret, API-key, and database-URL fields

### Repository and pipeline safety

- full reachable Git history is scanned for secrets
- safe logging and safe HTTP behavior have permanent tests
- Dependabot is configured for Python, npm, and GitHub Actions
- backend tests, frontend build, and both Docker builds are permanent gates

## Findings and risk classification

### SEC-01 — No database-native row-level security

**Priority:** High defense-in-depth gap

User-owned tables contain `user_id`, and the application consistently filters by it, but no PostgreSQL RLS policy, request-scoped database user context, or direct database-level isolation test is present. Application authorization currently provides the primary isolation boundary.

Impact scenarios include:

- a future endpoint forgets the ownership predicate
- a maintenance script or background task queries a user-owned table incorrectly
- a SQL-injection or ORM misuse bug is introduced later
- a compromised runtime database credential can read every row allowed to that database role

Required hardening:

- introduce versioned migrations
- create separate schema-owner/migration and restricted runtime roles
- enable and force RLS on user-owned root tables
- set the authenticated Clerk user ID transaction-locally
- add `USING` and `WITH CHECK` policies
- protect Career Plan child tables through ownership-aware policies
- test the policies directly using two users and the real restricted runtime role

### SEC-02 — Development authentication needs an explicit production startup prohibition

**Priority:** High configuration risk

Development authentication is intentionally available for tests and local work. If `AUTH_DEV_MODE=true` and a shared development token were accidentally configured in production, Clerk would be bypassed for private routes.

Required hardening:

- refuse startup when development authentication is enabled in a Railway/production environment
- add permanent startup/configuration tests
- verify the exact Clerk authorized-party allowlist and rotate/remove any unused development token from production settings

### SEC-03 — Rate limiting is process-local and proxy trust is not explicit

**Priority:** Medium to high availability/cost risk

The existing limiter is bounded and useful, but it is in memory, resets on deployment, does not coordinate across replicas, and derives the client address from forwarded headers without an explicit trusted-proxy boundary. Several public read or analysis routes are not uniformly covered.

Potential impact:

- bypass or uneven enforcement across replicas
- expensive résumé/parser/model/provider traffic
- third-party quota or model-cost amplification
- memory pressure from many client buckets, despite the current maximum bucket count

Required hardening:

- verify Railway's trusted proxy chain and accept forwarded client addresses only from that boundary
- use a distributed limiter or Railway/edge controls for production
- key authenticated limits by user as well as IP
- apply route-specific limits and concurrency bounds to expensive public/private operations

### SEC-04 — PDF and DOCX parser resource exhaustion

**Priority:** Medium availability risk

Upload byte size is limited, and files are not persisted, but a small compressed DOCX or pathological PDF may expand or parse disproportionately. Page count, decompressed member size, XML relationships, parser time, and worker isolation are not explicitly bounded.

Required hardening:

- validate ZIP member counts and uncompressed sizes before DOCX parsing
- cap PDF page/object processing
- enforce parser timeouts or isolate extraction work
- add decompression-bomb and malformed-document regressions

### SEC-05 — Browser security headers are not explicitly configured

**Priority:** Medium defense-in-depth gap

The Nginx configuration contains SPA routing only. An application-controlled CSP, frame restriction, MIME-sniffing protection, referrer policy, permissions policy, and sensitive-response caching policy are not present in the repository.

Required hardening:

- add and test an application-compatible Content Security Policy
- add `X-Content-Type-Options: nosniff`
- block framing through CSP `frame-ancestors` and/or `X-Frame-Options`
- add a restrictive referrer and permissions policy
- verify HSTS at the Railway edge and avoid duplicate/conflicting values

### SEC-06 — Backend container does not declare a non-root runtime user

**Priority:** Medium container-hardening gap

The backend image runs the Uvicorn process as the image default user. A container breakout is not implied, but running as non-root reduces the impact of an application compromise.

Required hardening:

- create an unprivileged application user
- own only required application paths
- use a read-only root filesystem and writable temporary/data paths where the platform supports them
- scan final images rather than only source manifests

### SEC-07 — Automated vulnerability/SAST/container scanning is incomplete

**Priority:** Medium supply-chain visibility gap

Dependabot and custom secret scanning exist, but CI does not currently run a blocking Python dependency audit, npm production-dependency audit, Python/JavaScript SAST, or image vulnerability scan.

Required hardening:

- add pinned `pip-audit` and npm production audits
- add CodeQL or a reviewed equivalent for Python and JavaScript/TypeScript
- scan built backend and frontend images
- publish machine-readable artifacts and an SBOM
- establish a documented exception process rather than silently ignoring advisories

### SEC-08 — Static admin key has broad destructive authority

**Priority:** Medium credential/authorization risk

The admin key protects shared-posting create, CSV import, and delete operations and uses constant-time comparison. It is still a single static credential with broad authority and no principal-level attribution.

Required hardening:

- verify it is absent from the frontend and logs
- rotate it after the audit
- restrict destructive administration to a separate deployment/private path or authenticated admin identity
- add audit events and route-specific limits
- consider removing unused shared-posting administration from the public deployment

### SEC-09 — Production documentation and configuration evidence are stale or incomplete

**Priority:** Low to medium governance risk

`SECURITY.md` still says real authentication, ownership, and structured security logging are missing, although they now exist. Exact production database role privileges, RLS state, TLS mode, backup access, Clerk configuration, admin-key rotation, security headers, and incident response are not recorded in the repository.

Required hardening:

- update the security policy after technical changes
- document data retention, deletion, breach response, credential rotation, backup/restore, and responsible disclosure
- keep the live demo restricted to non-sensitive résumé-style information until the final security sign-off

## No confirmed critical exploit from static review

The initial source review did not identify a confirmed authentication bypass in the intended production configuration, a confirmed cross-user IDOR in the reviewed private endpoints, raw SQL injection, arbitrary server-side URL fetching, command execution, or direct secret exposure.

This does not prove the absence of vulnerabilities. Automated scans, real PostgreSQL role/RLS tests, exact production configuration verification, browser-header inspection, and safe production authorization canaries remain required.

## Planned validation evidence

- Python dependency audit report
- npm production and full dependency audit reports
- Python static security report
- CodeQL Python and JavaScript/TypeScript results
- backend and frontend image vulnerability reports
- two-user API authorization matrix
- direct PostgreSQL RLS isolation matrix
- production auth-mode and Clerk-party assertions
- upload parser abuse regressions
- production header and route-exposure report
- final severity table, accepted limitations, and GO/NO-GO decision
