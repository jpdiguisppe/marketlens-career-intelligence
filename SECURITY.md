# Security Policy

MarketLens is a portfolio/demo career-intelligence application with completed Milestone 8.2 production security sign-off. The live deployment has database-enforced tenant isolation, production auth hardening, security/supply-chain gates, and documented residual risks, but it is still not presented as a service for highly sensitive or regulated data at scale.

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

PostgreSQL row-level security is active in production. The live Railway backend uses a restricted non-owner runtime role rather than the migration/table-owner credential, and authenticated private requests bind transaction-local user identity through `app.current_user_id`.

The final live two-user verification used synthetic records only and confirmed that User B received non-enumerating `404` responses when attempting to read/delete User A saved jobs and saved reports or read/execute/delete User A Career Plans, while both users' own supported private operations continued to work normally.

## Database isolation

The current PostgreSQL production posture is:

- schema/security migrations use a separate owner or migration credential
- the application runtime role is non-owner, `NOBYPASSRLS`, and unable to create databases, roles, or public-schema objects
- the runtime role does not own protected tables and cannot read migration metadata
- RLS is enabled and forced on `saved_jobs`, `saved_reports`, `career_plan_runs`, `career_plan_steps`, and `career_plan_audit_events`
- Career Plan child-table policies enforce ownership through the parent run
- authenticated user identity is applied with transaction-local PostgreSQL context and reapplied on each new SQLAlchemy transaction
- pooled connections are designed not to retain another request's user identity
- requests without an authenticated database user context fail closed against protected data

Application-level ownership filters remain in place as an independent layer above database-enforced RLS.

The production cutover and final live verification were completed against functional candidate revision `39570fb853be4f9cd670ea6d4670d334abcdd758`. The restricted runtime path was verified through authenticated create/execute/delete behavior, and the owner-controlled final sign-off also confirmed that the migration/owner connection is absent from the ongoing backend runtime variable set.

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

## Current production limitations and accepted residual risks

Milestone 8.2 is complete, but the final GO does not mean MarketLens is unhackable or ready for arbitrary sensitive-data workloads. Accepted residual risks include:

- rate limiting is process-local rather than distributed
- reviewed Clerk-transitive `cryptography` advisories remain under the explicit time-bounded exception policy until the dependency chain can be upgraded
- the administrator model still relies on a static server-side admin key rather than short-lived scoped admin identity
- Docker base images are managed through tags/Dependabot rather than immutable digest pins
- Railway-managed backup/PITR is unavailable on the current plan; the completed cutover used an owner-controlled local pre-cutover PostgreSQL backup as the rollback safeguard
- no external-user beta validation is claimed
- privacy policy/terms and operational incident-response processes would need additional work before collecting sensitive real-user data at scale

The final Milestone 8.2 security record is documented in `docs/milestone-8-2f-security-signoff.md` and GitHub issue #120.

## Reporting a vulnerability

Report vulnerabilities privately to the project owner. Do not post credentials, database URLs, private user data, or actionable exploit details in a public issue, pull request, discussion, or screenshot.

Include only the minimum information necessary to reproduce the problem safely. Do not perform destructive testing, denial-of-service testing, credential attacks, or extraction of other users' data.
