# Security Policy

MarketLens is a portfolio/demo career-intelligence application. Until Milestone 8.2 receives final production security sign-off, the live deployment should not be treated as a service for highly sensitive personal, employer, medical, financial, legal, or government-identification data.

## Supported use

Use the live demo with public job postings and non-sensitive resume-style content.

Do not upload or submit:

- Social Security numbers, government identifiers, or authentication secrets
- passwords, API keys, bearer tokens, private keys, or database URLs
- private medical, financial, or legal records
- confidential employer, customer, or regulated data
- information whose disclosure would create material harm

## Authentication and authorization

Production authentication uses Clerk bearer-token verification. Production configuration requires authorized parties, and MarketLens fails closed if development authentication is enabled in a production or Railway environment.

Private saved jobs, saved reports, and Career Plans retain application-level ownership checks. Cross-user object access is designed to return `404` rather than reveal another user's object existence.

Milestone 8.2C also includes PostgreSQL row-level-security migrations, a restricted non-owner runtime role, transaction-local authenticated-user context, forced ownership policies, and direct two-user PostgreSQL isolation tests. The code and tests are merged, but the live Railway database must still complete the documented owner-level migration and restricted-runtime credential cutover before production RLS is considered active.

## Database isolation

The intended PostgreSQL production posture is:

- schema/security migrations run only with a separate owner or migration credential
- the application runtime role is non-owner, `NOBYPASSRLS`, and unable to create schema objects
- RLS is enabled and forced on user-owned root tables
- Career Plan child tables inherit isolation through parent-run ownership policies
- authenticated user identity is applied with transaction-local PostgreSQL context and reapplied on each new SQLAlchemy transaction
- pooled connections do not retain another request's user identity

Application-level ownership filters remain in place as an independent layer even after RLS is active.

## API and upload protections

Current controls include:

- bounded request bodies before JSON or multipart parsing
- route-specific public, private, expensive-operation, admin, and service-wide rate limits
- forwarded client IPs trusted only through explicitly configured trusted proxy CIDRs
- CSV upload size and row-count limits
- PDF page, decoded-stream, extracted-text, and parser bounds
- DOCX archive-entry, expanded-size, individual-entry, compression-ratio, paragraph, and table-cell bounds
- rejection of encrypted/invalid resume documents and dangerous OOXML entity declarations
- allowlisted HTTPS external job links and fixed/allowlisted external provider identifiers
- generic safe HTTP errors and centralized secret/document log redaction

The current application rate limiter is process-local. It reduces single-instance abuse but is not a globally coordinated quota across multiple replicas; distributed rate limiting remains a documented residual availability/cost risk.

## Browser and container protections

Production disables FastAPI `/docs`, `/redoc`, and `/openapi.json`.

Frontend and backend responses are checked for defense-in-depth headers including CSP, HSTS, MIME-sniffing protection, frame isolation, referrer policy, permissions policy, and no-store behavior where appropriate.

Backend and frontend production containers run as dedicated non-root users. The permanent container runtime smoke test builds and starts both images and verifies non-root execution and hardened HTTP behavior.

## Dependency, source, secret, and supply-chain scanning

Permanent CI includes:

- `pip-audit` for Python runtime and development dependencies
- npm production and full-tree audits
- Bandit for Python source security findings
- CodeQL for Python and JavaScript/TypeScript
- full-history repository secret scanning and safe-log tests
- direct PostgreSQL RLS isolation tests against an ephemeral PostgreSQL service
- backend/frontend container runtime security smoke tests
- Trivy vulnerability scanning of both production images with critical/high findings blocking the build
- CycloneDX SBOM artifacts for both production images

The Trivy GitHub Action is pinned to an exact reviewed release commit. GitHub Actions, Python/npm dependencies, and Docker base images are monitored by Dependabot. Docker base-image tags are not currently digest-pinned; image vulnerability scanning and weekly update review are the compensating controls, and digest pinning remains an optional future hardening step.

Reviewed dependency exceptions are documented in `docs/security-dependency-exceptions.md`. Exceptions are narrow, time-bounded, and do not suppress newly discovered advisories.

## Admin access

Admin write/delete routes use a server-side `X-Admin-API-Key` and have a dedicated abuse limit. The admin credential must be stored only in deployment secret storage and must never be committed or logged.

The static admin-key model remains a residual risk compared with short-lived scoped administrative identity. Rotation, scope reduction, or replacement should be considered before MarketLens becomes a broader multi-user production service.

## Current production limitations

Milestone 8.2 is not complete until all final production checks pass. In particular:

- the live Railway PostgreSQL database still requires the restricted-runtime/RLS cutover and verification
- final two-independent-user production isolation testing has not yet been recorded
- rate limiting is process-local rather than distributed
- reviewed Clerk-transitive `cryptography` advisories remain under the explicit exception policy until the dependency chain can be upgraded
- no external-user beta validation is claimed
- privacy policy/terms and operational incident-response processes would need additional work before collecting sensitive real-user data at scale

## Reporting a vulnerability

Report vulnerabilities privately to the project owner. Do not post credentials, database URLs, private user data, or actionable exploit details in a public issue, pull request, discussion, or screenshot.

Include only the minimum information necessary to reproduce the problem safely. Do not perform destructive testing, denial-of-service testing, credential attacks, or extraction of other users' data.
