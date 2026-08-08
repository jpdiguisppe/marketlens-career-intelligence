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
- a JSON policy-classification report
- a CycloneDX SBOM
- scanner version, source revision, and image-ID metadata
- an enforcement step that rejects every critical/high finding unless it exactly matches a current reviewed exception

The evidence artifacts are retained for 90 days.

The Trivy action is pinned to exact commit `ed142fd0673e97e23eac54620cfb913e5ce36c25`, corresponding to the reviewed immutable v0.36.0 release. That action currently carries Trivy v0.70.0.

## Container remediation performed during 8.2E

The first image scan was intentionally allowed to record evidence before enforcement. It found that the previous Debian-based Python runtime and the old Nginx/Alpine runtime carried multiple high/critical base-image findings.

Rather than waive those findings:

- the backend moved to the official Python 3.12.13 Alpine 3.23 line
- the frontend build moved to Node 24 LTS on Alpine 3.23
- the frontend runtime moved to stable Nginx 1.30 on Alpine 3.24
- `pip` and `setuptools` are removed from the final backend runtime after dependency installation

After that remediation, both Alpine OS layers scanned with zero critical/high findings. The only backend high findings remaining are the Clerk-transitive `cryptography==48.0.1` advisories already reviewed in `docs/security-dependency-exceptions.md`.

The container policy does not ignore the package broadly. It allows only the exact backend package name, installed version, CVE identifiers, and review window through 2026-09-30. A different package, version, CVE, image, or expired review blocks the workflow.

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
- Scanner evidence is uploaded before enforcement so failed findings remain reviewable.
- An exception must identify the exact finding, affected component/path, exploitability analysis, compensating controls, owner, and review/expiry date.
- Container exceptions are machine-checked against exact package/version/CVE/image tuples and an explicit expiry date.
- An exception in one scanner does not automatically suppress unrelated findings in another scanner.
- No critical/high finding may be silently ignored to make a workflow green.

## Relationship to final sign-off

Passing 8.2E proves the repository has repeatable dependency/source/container supply-chain gates. It does not prove the live PostgreSQL RLS cutover. Final Milestone 8.2 sign-off remains blocked until the production database uses the restricted runtime role and two independent users pass the live isolation checks.
