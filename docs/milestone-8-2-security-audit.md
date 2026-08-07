# Milestone 8.2 — Security Threat Model and Audit Baseline

## Status

The initial threat model and defensive audit baseline are complete. Immediate dependency and production-authentication remediations are implemented on PR #121. PostgreSQL RLS, least-privilege database roles, browser/API headers, parser and abuse controls, container hardening, and final production sign-off remain open.

This document records confirmed controls, trust boundaries, attacker goals, and prioritized hardening work. It does not claim that MarketLens is unhackable or that a destructive penetration test was performed.

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
- development authentication now refuses to start in an explicit production or Railway runtime

### Application-level user authorization

- saved-job reads and deletes query by both object ID and authenticated user ID
- saved-report reads and deletes query by both object ID and authenticated user ID
- Career Plan reads, execution, explanation, cancellation, decisions, and deletion load the run through an ID-plus-user-ID ownership query
- another user's missing or unauthorized object is returned as `404`
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
- Python runtime and development dependencies are audited separately
- npm production and full dependency trees are audited
- Bandit records low findings and blocks medium/high findings
- CodeQL security-extended analysis covers Python and JavaScript/TypeScript
- exact reviewed dependency exceptions are documented and time bounded

## Findings and risk classification

### SEC-01 — No database-native row-level security

**Priority:** High defense-in-depth gap — open

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

### SEC-02 — Development authentication production prohibition

**Priority:** High configuration risk — remediated on PR #121

Development authentication remains available for tests and local work, but startup now fails when it is enabled in an explicit production or Railway runtime. Permanent tests cover explicit production, each Railway marker, local development, Clerk mode, and secret-safe failure text.

Production deployment evidence remains required after merge.

### SEC-03 — Rate limiting is process-local and proxy trust is not explicit

**Priority:** Medium to high availability/cost risk — open

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

**Priority:** Medium availability risk — open

Upload byte size is limited, and files are not persisted, but a small compressed DOCX or pathological PDF may expand or parse disproportionately. Page count, decompressed member size, XML relationships, parser time, and worker isolation are not explicitly bounded.

Required hardening:

- validate ZIP member counts and uncompressed sizes before DOCX parsing
- cap PDF page/object processing
- enforce parser timeouts or isolate extraction work
- add decompression-bomb and malformed-document regressions

### SEC-05 — Browser security headers are not explicitly configured

**Priority:** Medium defense-in-depth gap — open

The Nginx configuration contains SPA routing only. An application-controlled CSP, frame restriction, MIME-sniffing protection, referrer policy, permissions policy, and sensitive-response caching policy are not present in the repository.

Required hardening:

- add and test an application-compatible Content Security Policy
- add `X-Content-Type-Options: nosniff`
- block framing through CSP `frame-ancestors` and/or `X-Frame-Options`
- add a restrictive referrer and permissions policy
- verify HSTS at the Railway edge and avoid duplicate/conflicting values

### SEC-06 — Backend container does not declare a non-root runtime user

**Priority:** Medium container-hardening gap — open

The backend image runs the Uvicorn process as the image default user. A container breakout is not implied, but running as non-root reduces the impact of an application compromise.

Required hardening:

- create an unprivileged application user
- own only required application paths
- use a read-only root filesystem and writable temporary/data paths where the platform supports them
- scan final images rather than only source manifests

### SEC-07 — Automated vulnerability and SAST coverage

**Priority:** Medium supply-chain visibility gap — substantially remediated on PR #121

PR #121 adds reviewed Python runtime/development dependency audits, npm production/full audits, Bandit policy, CodeQL analysis, machine-readable evidence, and documented exceptions. The patched candidate has no unreviewed dependency finding and no medium/high Bandit finding.

Remaining work:

- scan built backend and frontend images
- publish SBOMs
- establish final branch-protection expectations
- review and pin third-party Actions/base images where practical

### SEC-08 — Static admin key has broad destructive authority

**Priority:** Medium credential/authorization risk — open

The admin key protects shared-posting create, CSV import, and delete operations and uses constant-time comparison. It is still a single static credential with broad authority and no principal-level attribution.

Required hardening:

- verify it is absent from the frontend and logs
- rotate it after the audit
- restrict destructive administration to a separate deployment/private path or authenticated admin identity
- add audit events and route-specific limits
- consider removing unused shared-posting administration from the public deployment

### SEC-09 — Production documentation and configuration evidence are stale or incomplete

**Priority:** Low to medium governance risk — open

`SECURITY.md` still says real authentication, ownership, and structured security logging are missing, although they now exist. Exact production database role privileges, RLS state, TLS mode, backup access, Clerk configuration, admin-key rotation, security headers, and incident response are not recorded in the repository.

Required hardening:

- update the security policy after technical changes
- document data retention, deletion, breach response, credential rotation, backup/restore, and responsible disclosure
- keep the live demo restricted to non-sensitive résumé-style information until the final security sign-off

### SEC-10 — Published dependency advisories

**Priority:** High initial finding — directly remediable findings fixed on PR #121

PR #121 upgrades FastAPI/Starlette and `python-multipart`, removes pytest from the runtime image, upgrades pytest in development dependencies, upgrades Vite/esbuild through a validated lockfile, and moves build tooling to development dependencies.

Three Clerk-transitive `cryptography` advisories remain under exact, time-bounded exceptions because the Clerk SDK currently constrains the dependency below fixed versions and MarketLens does not use the affected APIs. See [`security-dependency-exceptions.md`](security-dependency-exceptions.md).

## No confirmed critical exploit from review

The source and bounded production review did not identify a confirmed authentication bypass in the intended production configuration, a confirmed cross-user IDOR in the reviewed private endpoints, raw SQL injection, arbitrary server-side URL fetching, command execution, or direct secret exposure.

This does not prove the absence of vulnerabilities. Real PostgreSQL role/RLS tests, container scans, exact production configuration verification, authenticated two-user canaries, browser-header validation, and final deployment evidence remain required.

## Current validation evidence

The functional remediation candidate passed:

- 535 backend tests
- frontend production build
- backend and frontend Docker builds
- runtime and development Python dependency gates
- npm production and full dependency gates
- Bandit medium/high gate
- CodeQL Python and JavaScript/TypeScript
- secret/log safety
- provider resilience and telemetry
- operational reliability
- Career Plan agent evaluation
- semantic extraction, personalized coaching, and evidence provenance
- bounded unauthenticated production-route and CORS checks

See [`milestone-8-2a-security-scan-results.md`](milestone-8-2a-security-scan-results.md) for the measured result and remaining work.
