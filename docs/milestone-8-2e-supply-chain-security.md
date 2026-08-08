# Milestone 8.2E — Supply-chain security

## Goal

Make dependency and container risk continuously visible, reviewable, and blocking where appropriate before MarketLens receives final Milestone 8.2 security sign-off.

## Permanent gates

### Python and JavaScript dependencies

The Security Audit Baseline blocks unreviewed findings from:

- `pip-audit` against runtime requirements
- `pip-audit` against development requirements
- npm production dependency audit
- npm full dependency-tree audit
- Bandit medium/high Python source findings

Reviewed Python exceptions are limited to exact advisory IDs and documented in `docs/security-dependency-exceptions.md`.

### Source and secret analysis

MarketLens also retains:

- CodeQL for Python and JavaScript/TypeScript
- full-history secret scanning
- safe-log and safe-HTTP regression tests
- direct PostgreSQL RLS isolation tests

### Production container images

`Container Supply Chain Security` builds the actual backend and frontend production Dockerfiles and scans each image with Trivy.

For each image, CI produces:

- a JSON critical/high vulnerability report
- a CycloneDX SBOM
- scanner version, source revision, and image-ID metadata
- a blocking critical/high vulnerability gate

The evidence artifacts are retained for 90 days.

The Trivy action is pinned to exact commit `ed142fd0673e97e23eac54620cfb913e5ce36c25`, corresponding to the reviewed v0.36.0 release. Trivy itself is explicitly requested at v0.70.0 in the first scan invocation.

## GitHub Action dependency policy

Third-party security actions should be pinned to a full commit SHA whenever practical. First-party `actions/*` dependencies that remain on major-version tags are monitored by the repository's weekly GitHub Actions Dependabot configuration.

Security-sensitive newly introduced third-party actions should not be added by an unreviewed floating `main`, `master`, or major-only tag.

## Docker base-image policy

Current Dockerfiles use bounded upstream tags rather than immutable image digests. This is consciously managed through:

- weekly Dependabot Docker monitoring for both `/backend` and `/frontend`
- permanent vulnerability scanning of the fully built images
- production container runtime smoke testing
- explicit review before major base-image changes

Digest pinning would further reduce tag-mutation risk and remains a future defense-in-depth option. The current policy does not claim digest-level reproducibility.

## Finding policy

- Critical/high findings are blocking by default.
- Scanner evidence is uploaded even when the enforcement step fails so findings can be reviewed.
- An exception must identify the exact finding, affected component/path, exploitability analysis, compensating controls, owner, and review/expiry date.
- An exception in one scanner does not automatically suppress the same package in another scanner.
- No critical/high finding may be silently ignored to make a workflow green.

## Relationship to final sign-off

Passing 8.2E proves the repository has repeatable dependency/source/container supply-chain gates. It does not prove the live PostgreSQL RLS cutover. Final Milestone 8.2 sign-off remains blocked until the production database uses the restricted runtime role and two independent users pass the live isolation checks.
