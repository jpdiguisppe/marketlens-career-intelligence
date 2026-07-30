# MarketLens Career Intelligence

MarketLens is a deployed full-stack career-intelligence platform that searches configured public job sources, compares résumé evidence against real job descriptions, ranks role fit, and turns opportunities, strengths, and evidence gaps into a reviewable career plan.

The product has two connected workspaces:

1. **Job Intelligence** — public-source job search and evidence-aware Smart Fit comparison.
2. **Career Plans** — a private, resumable, bounded AI-agent workflow that searches, selects, analyzes, synthesizes, explains, and proposes next actions while preserving human control.

## Project highlights

- **Deployed full-stack product:** React + TypeScript, FastAPI, SQLAlchemy, Clerk authentication, Docker, PostgreSQL, and Railway.
- **Bounded Career Planning Agent:** a durable seven-step workflow that orchestrates the existing search and Smart Fit systems rather than reproducing their logic inside prompts.
- **Deterministic authority:** job selection, scores, evidence, hard requirements, provenance, opportunity categories, and the action set remain deterministic.
- **Optional AI organization:** one strict-schema model call may organize existing IDs and priorities but cannot create facts, alter scores, approve a plan, or take external action.
- **Private resumable workflows:** users can create, cancel, retry, edit, approve, reject, reopen, and delete owned plans.
- **Production-oriented evaluation:** ten-sector task fixtures, prompt-injection tests, ownership attacks, provider failures, cancellation recovery, privacy checks, explicit budgets, Docker builds, and exact-revision production canaries.

## Tech stack

| Area | Tools |
| --- | --- |
| Frontend | React, TypeScript, Vite, CSS |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy |
| Database | SQLite locally; PostgreSQL through `DATABASE_URL` in production |
| Authentication | Clerk frontend sessions with backend token verification |
| Job sources | Greenhouse, Lever, named SmartRecruiters employer boards, Remote OK, Remotive |
| AI integration | Backend-only Responses API configuration, strict schemas, deterministic fallback |
| Testing | pytest, deterministic evaluators, adversarial fixtures, GitHub Actions, Docker builds |
| Deployment | Railway frontend and backend services |

## Live demo

- **Frontend:** [MarketLens live demo](https://marketlens-career-intelligence-production-8a34.up.railway.app)
- **Backend API docs:** [FastAPI Swagger UI](https://marketlens-career-intelligence-production.up.railway.app/docs)
- **Backend health:** [API health endpoint](https://marketlens-career-intelligence-production.up.railway.app/health)
- **Deployment identity:** [Safe backend revision endpoint](https://marketlens-career-intelligence-production.up.railway.app/deployment/status)
- **Portfolio walkthrough:** [How to demo MarketLens](docs/portfolio-demo-walkthrough.md)
- **Agent evaluation:** [Milestone 8.1 evaluation record](docs/milestone-8-1-agent-evaluation.md)
- **Production sign-off:** [Milestone 8.1 completion record](docs/milestone-8-1-completion.md)

MarketLens is a portfolio product. Do not upload secrets, API keys, confidential employer/customer data, or highly sensitive personal information.

## Screenshots

### Online job search

MarketLens searches configured public sources and reports exactly which providers were attempted.

![Online job search results](docs/screenshots/online-job-search.png)

### Ranked Smart Fit comparison

Users can compare multiple jobs against one résumé and inspect why one opportunity ranked above another.

![Ranked Smart Fit comparison](docs/screenshots/job-fit-ranking.png)

### Role-aware gap report

Reports distinguish direct résumé proof from broader signals and surface role-specific capability gaps.

![Role-aware gap report](docs/screenshots/role-aware-gap-report.png)

### Coaching actions and requirements

Deterministic recommendations keep hard requirements separate from broader career-development guidance.

![Coaching actions and requirement breakdown](docs/screenshots/coaching-actions-breakdown.png)

### Seven-step Career Planning Agent

The authenticated production workspace displays every persisted step and clearly separates deterministic planning from optional bounded AI organization.

![Career Plan seven-step AI workflow](docs/screenshots/milestone-8-1/career-plan-ai-workflow.svg)

### Deterministic candidate-selection audit

Users can inspect provider coverage, considered jobs, selected jobs, excluded jobs, and deterministic reason codes before approval.

![Career Plan candidate-selection audit](docs/screenshots/milestone-8-1/candidate-selection-audit.svg)

### Safe cancellation and retry

A production run was cancelled after search and successfully completed as attempt two without duplicated actions or lost audit history.

![Career Plan cancellation and retry recovery](docs/screenshots/milestone-8-1/cancellation-retry-recovery.svg)

### Edited approval persistence

User edits remain separate from the immutable generated proposal and persist after approval, refresh, and reopening.

![Approved Career Plan edited action](docs/screenshots/milestone-8-1/approved-edited-action.svg)

These privacy-safe production validation visuals reproduce the exact captured states and measured values from the July 30, 2026 authenticated session while excluding raw résumé text and account details. Responsive behavior was separately validated at a 400 × 770 viewport after the mobile authentication-overlay fix in PR #98.

## Current product workflow

### Job Intelligence

```text
Open MarketLens
Optionally sign in for private saving
Upload or paste a résumé
Search configured public job sources
Choose occupation, experience level, and optional location
Inspect provider coverage and bounded results
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

## What makes the agent bounded

MarketLens is not an unrestricted career chatbot and does not autonomously act on the user’s behalf.

The agent:

- calls the existing search and Smart Fit implementations through typed boundaries
- analyzes at most five jobs per run
- creates at most twenty proposed actions
- uses at most one Career Plan model call
- persists workflow state, attempts, safe summaries, and audit events
- treats job content and résumé content as untrusted data
- returns a complete deterministic plan when AI is disabled or fails
- requires an explicit user decision before a plan becomes approved or rejected

The model cannot:

- change Smart Fit scores or confidence
- change evidence statuses or provenance
- override hard-requirement findings
- add jobs or deterministic actions
- invent experience, credentials, projects, or résumé claims
- apply to jobs, message recruiters, edit profiles, or purchase services
- bypass authentication or human approval
- predict interviews, offers, salary, or hiring probability

## Search correctness contract

MarketLens evaluates occupation, experience level, industry, and location as separate concerns.

Specific occupations require title-level evidence. A shared word such as `engineer`, `analyst`, `assistant`, `technician`, `editor`, or `manager` is not sufficient by itself. Protected distinctions include electrical engineer vs. analytics engineer, electrician vs. electrical engineer, medical assistant vs. registered nurse, policy analyst vs. data analyst, and journalism editor vs. video editor.

Supported experience levels are `any`, `intern`, `entry`, `mid`, and `senior`. Explicit city searches are strict, with bounded metro-area aliases rather than unrestricted location matching.

MarketLens uses public APIs rather than scraping closed platforms:

- Greenhouse Job Board API
- Lever Postings API
- bounded named SmartRecruiters employer boards
- Remote OK public feed
- Remotive public API

It does not claim to search all of LinkedIn, Indeed, Handshake, Workday, school portals, or every company career site.

## Current capabilities

All visitors can:

- upload `.txt`, `.md`, `.pdf`, or `.docx` résumés for request-time extraction
- paste résumé text manually
- search configured public sources
- inspect provider-by-provider coverage, warnings, and continuation links
- compare one to ten searched or manually pasted jobs through Smart Fit
- review requirements, evidence, rankings, gaps, limitations, and coaching actions
- use deterministic analysis when model-assisted stages are unavailable

Signed-in users can additionally:

- save, reopen, and delete jobs privately
- save and delete reduced Smart Fit summaries
- create private Career Plan runs
- inspect all seven workflow steps and safe audit history
- cancel and retry active or failed runs
- review selected and excluded candidates with deterministic reason codes
- inspect opportunity categories, repeated strengths, repeated gaps, and proposed actions
- request bounded explanations from saved plan data
- edit, approve, reject, reopen, and delete owned plans

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

## Security and privacy

Current controls include:

- Clerk-managed authentication instead of custom password storage
- backend verification of Clerk session tokens
- server-side ownership filters for every private resource
- cross-user private-record access returning `404`
- no automatic persistence of analysis inputs
- raw résumé text and full job descriptions excluded from Career Plan and saved-report records
- backend-only model-provider keys
- request-scoped redaction and sensitive-log context
- strict model response schemas and reference validation
- public request, file, CSV, search, and provider bounds
- safe HTTPS application-link validation
- SQLAlchemy ORM usage
- secret scanning and log-redaction CI
- explicit deterministic fallback for provider failure

See [`SECURITY.md`](SECURITY.md) for the security policy and limitations.

## Evaluation and production validation

Milestone 8.1 passed:

- ten representative career sectors
- ten committed task-level cases
- three repeated deterministic executions per case
- thirty stable agent executions with zero failed cases
- prompt-injection inputs across descriptions, titles, company metadata, URLs, and authenticated résumé text
- model timeout, transport, HTTP, invalid JSON, schema, reference, duplicate, and policy-changing output cases
- cancellation and failed-run retry recovery without duplicated actions
- automated and production ownership-isolation checks
- provider telemetry, cost, token, payload, and latency policies
- **447 backend tests**
- frontend TypeScript/Vite production build
- backend and frontend Docker builds
- Career Plan Agent Evaluation
- Smart Fit Evaluation
- Operational Reliability
- Provider Resilience
- Provider Telemetry
- Secret and Log Safety

The exact-revision Railway canaries passed on validated runtime revision `31acd2b7a587cf4fdc9c2cebe0dbf4b7dce567f1`. Authenticated production browser validation covered deterministic and AI-assisted plans, all seven steps, explanations, edit/approve/reopen persistence, reject/delete, cancellation/retry, prompt-injection resistance, second-account isolation, and 400-pixel responsive behavior.

See [`docs/milestone-8-1-completion.md`](docs/milestone-8-1-completion.md) for measured latency, cost, fallback, residual-risk, and GO evidence.

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

The frontend reads `VITE_API_BASE_URL` and `VITE_CLERK_PUBLISHABLE_KEY`. Railway runtime configuration also exposes a sanitized deployment revision through `config.js`.

### Quality checks

```bash
cd backend
python -m pytest
python scripts/run_job_search_evaluation.py
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

Production public canary:

```bash
cd backend
EXPECTED_REVISION=<40-character-sha> \
CANARY_WAIT_SECONDS=900 \
python scripts/run_production_career_plan_canary.py --mode public
```

Full automated authenticated mode additionally requires short-lived canary bearer tokens stored outside the repository. The final Milestone 8.1 authenticated sign-off was completed through a recorded production browser session.

## Portfolio and interview summary

MarketLens is a deployed, stateful career-intelligence product. It combines public job-source integrations, evidence-aware analysis, private workflow persistence, and a bounded AI agent that orchestrates search and Smart Fit tools while preserving deterministic authority and human approval.

Suggested résumé bullet:

```text
Built and deployed MarketLens, a React/FastAPI career-intelligence platform with a bounded AI planning agent that orchestrates public job search and evidence-based résumé analysis, persists resumable user-owned workflows, falls back deterministically on model failure, and is validated through adversarial, privacy, recovery, Docker, and exact-revision production canary gates.
```

## Milestone status

Completed:

- Milestones 1–7.1: search, Smart Fit, deployment, authentication, private saving, source coverage, and cross-sector correctness
- Milestone 8: optional model-assisted extraction and personalized coaching foundations
- **Milestone 8.1A–8.1F: bounded Career Planning Agent architecture, orchestration, optional AI organization, authenticated UI, permanent evaluation, and production sign-off**

## Explicit post-launch roadmap

The following are not implemented by Milestone 8.1:

- autonomous or mass job applications
- recruiter messaging or email automation
- external profile editing
- course or service purchasing
- unrestricted multi-agent delegation
- closed-platform scraping
- full Career Evidence Graph
- GitHub evidence verification
- résumé claim verification
- complete application tracker and outcome-learning loop
- long-term labor-market trend forecasting
- guaranteed interview, offer, salary, or career outcomes
