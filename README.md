# MarketLens Career Intelligence

MarketLens is a deployed full-stack career-intelligence platform that searches configured public job sources, compares résumé evidence against real job descriptions, ranks role fit, and turns opportunities, strengths, and evidence gaps into a reviewable career plan.

The product has two connected workspaces:

1. **Job Intelligence** — SOC-aligned public-source job search and evidence-aware Smart Fit comparison.
2. **Career Plans** — a private, resumable, bounded AI-agent workflow that searches, selects, analyzes, synthesizes, explains, and proposes next actions while preserving deterministic authority and human control.

## Project highlights

- **Deployed full-stack product:** React, TypeScript, FastAPI, Pydantic, SQLAlchemy, Clerk authentication, PostgreSQL, Docker, and Railway.
- **Universal cross-sector occupation search:** all 23 SOC major occupational groups are represented through 214 occupation concepts, 454 accepted titles, and 33 explicitly ambiguous acronyms.
- **Measured search quality:** 268/268 held-out occupation queries, 92/92 held-out title checks, and a 40/40 exact-revision production audit passed; all 47 manually reviewed returned live titles were relevant.
- **Bounded Career Planning Agent:** a durable seven-step workflow orchestrates job search and Smart Fit rather than reproducing those systems inside prompts.
- **Deterministic authority:** job selection, scores, evidence, hard requirements, provenance, opportunity categories, and proposed actions remain deterministic.
- **Optional AI organization:** one strict-schema model call may organize existing IDs and priorities but cannot invent facts, change scores, approve a plan, or take external action.
- **Private resumable workflows:** authenticated users can create, cancel, retry, edit, approve, reject, reopen, and delete owned plans.
- **Production security hardening:** Clerk authorization, application ownership checks, PostgreSQL forced row-level security, a restricted non-owner runtime database role, request and parser bounds, security headers, non-root containers, dependency/SAST/secret scanning, production image scanning, and SBOM evidence.
- **Final production security sign-off:** Milestone 8.2 completed with live two-user tenant-isolation verification, owner-controlled database rollback evidence, runtime credential review, production log review, and an explicit residual-risk record.

## Tech stack

| Area | Tools |
| --- | --- |
| Frontend | React, TypeScript, Vite, CSS |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy |
| Database | SQLite locally; PostgreSQL in production |
| Authentication | Clerk frontend sessions with backend bearer-token verification |
| Job sources | Greenhouse, Lever, named SmartRecruiters employer boards, Remote OK, Remotive |
| AI integration | Backend-only Responses API configuration, strict schemas, deterministic fallback |
| Testing | pytest, deterministic evaluators, adversarial fixtures, GitHub Actions, Docker |
| Deployment | Railway frontend and backend services |

## Live demo and evidence

- **Frontend:** [MarketLens live demo](https://marketlens-career-intelligence-production-8a34.up.railway.app)
- **Backend health:** [API health endpoint](https://marketlens-career-intelligence-production.up.railway.app/health)
- **Deployment identity:** [Safe backend revision endpoint](https://marketlens-career-intelligence-production.up.railway.app/deployment/status)
- **Portfolio walkthrough:** [How to demo MarketLens](docs/portfolio-demo-walkthrough.md)
- **Career Plan evaluation:** [Milestone 8.1 agent evaluation](docs/milestone-8-1-agent-evaluation.md)
- **Career Plan sign-off:** [Milestone 8.1 completion record](docs/milestone-8-1-completion.md)
- **Universal-search evaluation:** [Milestone 8.1I held-out occupation evaluation](docs/milestone-8-1i-held-out-occupation-evaluation.md)
- **Milestone 8 search sign-off:** [Universal search production sign-off](docs/milestone-8-universal-search-signoff.md)
- **Security audit:** [Milestone 8.2 security audit baseline](docs/milestone-8-2-security-audit.md)
- **RLS production cutover runbook:** [Milestone 8.2C PostgreSQL RLS cutover](docs/milestone-8-2c-postgres-rls-cutover.md)
- **Final security sign-off:** [Milestone 8.2F security sign-off](docs/milestone-8-2f-security-signoff.md)

Production FastAPI `/docs`, `/redoc`, and `/openapi.json` are intentionally disabled as part of the production security surface.

MarketLens is a portfolio product. Do not upload secrets, API keys, confidential employer/customer data, or highly sensitive personal information.

## Product screenshots

### Workspace 1 — Job Intelligence

MarketLens searches configured public sources and reports which providers were attempted.

![Job Intelligence public-source search results](docs/screenshots/online-job-search.png)

Users can compare multiple jobs against one résumé and inspect why one opportunity ranked above another.

![Job Intelligence ranked Smart Fit comparison](docs/screenshots/job-fit-ranking.png)

Reports distinguish direct résumé proof from broader signals and surface role-specific capability gaps.

![Job Intelligence role-aware gap report](docs/screenshots/role-aware-gap-report.png)

Deterministic recommendations keep hard requirements separate from broader career-development guidance.

![Job Intelligence coaching actions and requirement breakdown](docs/screenshots/coaching-actions-breakdown.png)

### Workspace 2 — Career Plans

The authenticated production workspace displays every persisted step and separates deterministic planning from optional bounded AI organization.

![Career Plans seven-step AI workflow](docs/screenshots/milestone-8-1/career-plan-ai-workflow.svg)

Users can inspect provider coverage, considered jobs, selected jobs, excluded jobs, and deterministic reason codes before approval.

![Career Plans deterministic candidate-selection audit](docs/screenshots/milestone-8-1/candidate-selection-audit.svg)

A production run was cancelled after search and successfully completed as attempt two without duplicated actions or lost audit history.

![Career Plans cancellation and retry recovery](docs/screenshots/milestone-8-1/cancellation-retry-recovery.svg)

User edits remain separate from the immutable generated proposal and persist after approval, refresh, and reopening.

![Career Plans approved edited action](docs/screenshots/milestone-8-1/approved-edited-action.svg)

## Current product workflow

### Job Intelligence

```text
Open MarketLens
Optionally sign in for private saving
Upload or paste a résumé
Search configured public job sources
Choose occupation, experience level, and optional location
Inspect interpretation, provider coverage, warnings, and bounded results
Select one or more jobs
Run role-aware Smart Fit
Review ranking, evidence, requirements, gaps, and coaching
Explicitly save jobs or reduced reports when signed in
```

Manual comparison remains available for postings outside configured public sources:

```text
Upload or paste a résumé
Paste one or more job descriptions
Separate multiple postings with ---
Run Smart Fit and compare results
Explicitly save a reduced report when signed in
```

### Career Planning Agent

```text
Sign in
Open Career Plans
Define a target occupation and practical constraints
Provide a résumé for request-time analysis
Create and execute a bounded planning run
Watch seven persisted workflow steps
Inspect source coverage and candidate selection/exclusion reasons
Review opportunity categories, recurring strengths, recurring gaps, and actions
Inspect deterministic reasoning and optional AI contribution
Ask bounded “Why?” questions
Edit, approve, reject, save, reopen, retry, cancel, or delete the plan
```

The seven workflow steps are:

1. validate input
2. search jobs
3. select candidates
4. analyze Smart Fit
5. synthesize a deterministic plan
6. optionally organize the plan with one bounded model call
7. finalize the proposal for human review

## Universal search correctness contract

MarketLens evaluates occupation, experience level, industry, and location as separate concerns.

The occupation layer recognizes canonical titles, accepted alternate titles, spelling and punctuation variants, reordered phrases, and safe abbreviations across every SOC major group. Bare ambiguous acronyms such as `SAE`, `PM`, `PA`, and `SE` are not silently expanded; MarketLens asks the user to choose a meaning before any provider search.

Specific occupations require title-level evidence. A shared word such as `engineer`, `analyst`, `assistant`, `technician`, `editor`, or `manager` is not sufficient by itself. Production guards protect distinctions including accountant vs. accountant partner programs, financial analyst vs. generic finance fellowships, RN vs. LPN/LVN, medical assistant vs. medical fellowships, electrician vs. electrical engineer, and policy analyst vs. data analyst.

Unknown nonsense phrases stop without provider requests. Recognized occupations with no current configured-source result receive an explicit explanation and canonical continuation links rather than loosely related filler jobs.

MarketLens uses public APIs rather than scraping closed platforms:

- Greenhouse Job Board API
- Lever Postings API
- bounded named SmartRecruiters employer boards
- Remote OK public feed
- Remotive public API

It does not claim to search all of LinkedIn, Indeed, Handshake, Workday, school portals, or every company career site.

## What makes the agent bounded

MarketLens is not an unrestricted career chatbot and does not autonomously act on a user’s behalf.

The agent:

- calls the existing search and Smart Fit implementations through typed boundaries
- analyzes at most five jobs per run
- creates at most twenty proposed actions
- uses at most one Career Plan model call
- persists workflow state, attempts, safe summaries, and audit events
- treats job content and résumé content as untrusted data
- returns a complete deterministic plan when AI is disabled or fails
- requires an explicit user decision before a plan becomes approved or rejected

The model cannot change Smart Fit scores, override hard requirements, add jobs, invent résumé evidence, apply to jobs, message recruiters, edit external profiles, purchase services, bypass authentication, or predict hiring outcomes.

## Security and privacy

Current controls include:

- Clerk-managed authentication and backend session-token verification
- exact application-level ownership filters for private resources, with cross-user object access returning non-enumerating `404` responses where designed
- a PostgreSQL restricted runtime role that is separate from the migration/table-owner credential
- forced PostgreSQL row-level security on `saved_jobs`, `saved_reports`, `career_plan_runs`, `career_plan_steps`, and `career_plan_audit_events`
- transaction-local authenticated-user context through `app.current_user_id`
- runtime-role restrictions including no superuser, role/database creation, inheritance, RLS bypass, protected-table ownership, public-schema creation, or migration-metadata access
- no automatic persistence of raw analysis inputs
- raw résumé text and full job descriptions excluded from Career Plan and saved-report records
- request-scoped credential/document redaction and safe HTTP error behavior
- strict model response schemas and reference validation
- route-specific request/rate bounds and a 2 MB request-body ceiling
- DOCX archive/decompression/XML limits and PDF page/decompression/content limits
- production CSP, HSTS, clickjacking, MIME-sniffing, referrer, permissions, and no-store controls
- production API documentation disabled
- backend and frontend production containers running as non-root users
- Python/npm dependency audits, Bandit, CodeQL, full-history secret scanning, and safe-log regression tests
- Trivy scans of the actual production images, machine-enforced critical/high policy, and CycloneDX SBOM evidence
- explicit deterministic fallback for provider or model failure

See [`SECURITY.md`](SECURITY.md) for the current security policy and limitations.

## Milestone 8.2 production security sign-off

Milestone 8.2A–8.2F is complete.

- **8.2A — Threat model and audit baseline:** complete
- **8.2B — Production authentication and authorization hardening:** complete
- **8.2C — PostgreSQL RLS and least privilege:** complete, including the owner-controlled production restricted-runtime/RLS cutover
- **8.2D — API, upload, browser, and container hardening:** complete and production verified
- **8.2E — Security CI and supply-chain gates:** complete
- **8.2F — Final production security sign-off:** complete

The functional production security candidate used for the final evidence is:

```text
39570fb853be4f9cd670ea6d4670d334abcdd758
```

Final evidence includes:

- backend health and deployment identity returning the exact functional candidate revision
- frontend exact-revision production verification
- successful Production Security Surface checks for private-route authentication boundaries, disabled API documentation, CORS, security headers, CSP, and no-store behavior
- successful PostgreSQL security migration and restricted-runtime verification
- forced RLS enabled on all five protected tables
- Railway backend switched from the migration/table-owner credential to the restricted runtime database role
- direct restricted-runtime default-deny behavior with no request identity
- an authenticated synthetic production Career Plan flow successfully creating a run (`201`), executing it (`200`), reaching `awaiting_approval` with all seven workflow steps, and deleting the test run (`200`)
- live two-independent-user isolation across saved jobs, saved reports, and Career Plans, with cross-user access returning `404` where designed while same-user operations continued to work normally
- owner review confirming the ongoing backend runtime variable set does not contain the migration/owner database connection
- owner review of production logs around the verification window showing request metadata only and no observed bearer/JWT tokens, database credentials, stack traces, or submitted test bodies
- a pre-cutover production PostgreSQL backup created on owner-controlled local Mac storage because Railway-managed backup/PITR is unavailable on the current plan
- final residual risks recorded explicitly rather than hidden

Final decision:

```text
GO — MILESTONE 8.2 SECURITY HARDENING COMPLETE
```

GitHub issue #122 and umbrella issue #120 are closed as completed.

## Evaluation and production validation

### Career Planning Agent

The original Milestone 8.1 Career Planning Agent sign-off covered ten representative career sectors, repeated deterministic executions, prompt-injection inputs, model/provider failure modes, cancellation/retry recovery, production ownership isolation, provider telemetry, cost/token policies, Docker builds, and exact-revision Railway validation.

See [`docs/milestone-8-1-completion.md`](docs/milestone-8-1-completion.md) for the full agent evidence.

### Universal occupation search

| Measurement | Result |
| --- | ---: |
| Held-out occupation queries | 268 / 268 |
| Held-out title checks | 92 / 92 |
| SOC major groups | 23 / 23 |
| Held-out career spheres | 30 |
| Explicit ambiguous acronyms | 33 |
| Exact-revision production audit | 40 / 40 cases |
| Production career spheres | 14 |
| Manually reviewed production titles | 47 / 47 relevant |
| Returned-title precision | 100.0% |

### Security hardening validation

The final security workstream recorded 539 normal backend tests with PostgreSQL-specific cases separated from that run, plus a dedicated 7/7 PostgreSQL RLS/verifier gate. It also included frontend and Docker builds, dependency audits, Bandit, CodeQL, secret/log safety, production image scanning, SBOM generation, and exact-revision production security checks.

See:

- [`docs/milestone-8-1i-held-out-occupation-evaluation.md`](docs/milestone-8-1i-held-out-occupation-evaluation.md)
- [`docs/milestone-8-universal-search-signoff.md`](docs/milestone-8-universal-search-signoff.md)
- [`docs/milestone-8-2f-security-signoff.md`](docs/milestone-8-2f-security-signoff.md)

## Backend API

Important public endpoints include:

- `GET /health`
- `GET /deployment/status`
- `GET /jobs/search`
- `POST /skills/extract`
- `POST /analysis/resume-file/extract`
- `POST /analysis/smart`
- `POST /analysis/smart/batch`
- `GET /analysis/model-status`

Authenticated Career Plan endpoints include:

- `POST /career-plans`
- `GET /career-plans`
- `GET /career-plans/{run_id}`
- `POST /career-plans/{run_id}/execute`
- `POST /career-plans/{run_id}/cancel`
- `POST /career-plans/{run_id}/explain`
- `POST /career-plans/{run_id}/decision`
- `DELETE /career-plans/{run_id}`

Shared posting creation, CSV import, and deletion remain admin-only operations protected by `X-Admin-API-Key`.

## Running locally

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend reads `VITE_API_BASE_URL` and `VITE_CLERK_PUBLISHABLE_KEY`.

### Quality checks

```bash
cd backend
python -m pytest
python scripts/run_job_search_evaluation.py
python scripts/run_held_out_occupation_evaluation.py
python scripts/run_career_plan_agent_evaluation.py
```

```bash
cd frontend
npm ci
npm run build
```

```bash
docker build -t marketlens-backend ./backend
docker build --build-arg VITE_API_BASE_URL=http://localhost:8000 -t marketlens-frontend ./frontend
```

## Portfolio and interview summary

MarketLens is a deployed, stateful career-intelligence product. It combines SOC-aligned cross-sector occupation interpretation, public job-source integrations, evidence-aware analysis, private workflow persistence, a bounded AI agent, database-enforced tenant isolation, and production security/supply-chain gates while preserving deterministic authority and human approval.

Suggested résumé bullet:

```text
Built and deployed MarketLens, a React/FastAPI/PostgreSQL career-intelligence platform with SOC-aligned job search, evidence-based résumé analysis, a bounded AI planning agent, Clerk authentication, forced PostgreSQL row-level security, container/SBOM security gates, and exact-revision Railway production validation.
```

## Milestone status

Completed:

- Milestones 1–7.1: search, Smart Fit, deployment, authentication, private saving, source coverage, and cross-sector correctness
- Milestone 8: optional model-assisted extraction and personalized coaching foundations
- Milestones 8.1A–8.1F: bounded Career Planning Agent architecture, orchestration, optional AI organization, authenticated UI, permanent evaluation, and production sign-off
- Milestone 8.1G: universal occupation-search foundation and production hardening
- Milestone 8.1H: cross-sector skill-badge precision
- Milestone 8.1I: independent held-out occupation evaluation and exact-revision production audit
- Milestone 8.1J: measured universal-search production sign-off
- Milestones 8.2A and 8.2B: threat model, audit baseline, authentication, and authorization hardening
- Milestone 8.2C: PostgreSQL RLS/least privilege implementation and completed production restricted-runtime cutover
- Milestone 8.2D: API, upload, browser, and container hardening
- Milestone 8.2E: security CI, production image scanning, and SBOM/supply-chain gates
- Milestone 8.2F: final production security validation and GO decision
- **Milestone 8.2 security hardening workstream: complete**

## Explicit post-launch roadmap

The following are not implemented by the completed product scope:

- autonomous or mass job applications
- recruiter messaging or email automation
- external profile editing
- course or service purchasing
- unrestricted multi-agent delegation
- closed-platform scraping
- full O*NET-generated occupation-registry importer
- full Career Evidence Graph
- GitHub evidence verification
- résumé claim verification
- complete application tracker and outcome-learning loop
- long-term labor-market trend forecasting
- guaranteed interview, offer, salary, or career outcomes
