# MarketLens Career Intelligence

MarketLens is a deployed full-stack career-intelligence platform that compares resume evidence against real job descriptions, ranks role fit, and turns noisy postings into clearer skill gaps, capability gaps, and learning priorities.

## Project Highlights

- **Deployed full-stack app:** React + TypeScript frontend, FastAPI backend, SQLAlchemy persistence, and Railway deployment.
- **Resume-to-job comparison:** Users can upload or paste a resume, search configured public job sources, select jobs, and compare fit.
- **Role-aware Smart Fit:** The app ranks jobs using resume-backed evidence, role-family context, capability gaps, and coaching actions.
- **Online + manual workflows:** Users can search public Greenhouse, Lever, Remote OK, and Remotive sources or paste outside postings manually.
- **Private career workspace:** Clerk-authenticated users can save jobs and reduced Smart Fit report summaries with server-side ownership checks.
- **Portfolio-ready packaging:** The repo now includes screenshots, a guided demo walkthrough, README highlights, and a resume/interview summary.
- **Quality coverage:** Backend tests cover API behavior, job search filtering, Smart Fit analysis, role-aware behavior, and evaluation cases.

## Tech Stack

| Area | Tools |
| --- | --- |
| Frontend | React, TypeScript, Vite, CSS |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy |
| Database | SQLite locally, PostgreSQL-ready deployment through `DATABASE_URL` |
| Job sources | Greenhouse Job Board API, Lever Postings API, Remote OK, Remotive |
| Testing / Quality | pytest, frontend production build, GitHub Actions, Dependabot |
| Deployment | Railway frontend, Railway backend, Railway/PostgreSQL-ready backend configuration |

## Resume / Interview Summary

MarketLens is a deployed full-stack career-intelligence app that compares resume evidence against real job postings, ranks job fit, and explains role-specific gaps. I built the React frontend, FastAPI backend, job-search normalization layer, Smart Fit analysis workflow, role-aware scoring logic, security controls, tests, deployment pipeline, and portfolio-ready documentation.

Resume bullet version:

```text
Built and deployed MarketLens, a full-stack React/FastAPI career-intelligence app that searches public job APIs, compares resumes against multiple postings, ranks role fit, identifies role-specific capability gaps, and explains recommendations with tested backend analysis logic.
```

## Live Demo

- **Frontend app:** [MarketLens live demo](https://marketlens-career-intelligence-production-8a34.up.railway.app)
- **Backend API docs:** [FastAPI Swagger UI](https://marketlens-career-intelligence-production.up.railway.app/docs)
- **Backend health check:** [API health endpoint](https://marketlens-career-intelligence-production.up.railway.app/health)
- **Portfolio demo walkthrough:** [How to demo MarketLens](docs/portfolio-demo-walkthrough.md)
- **Milestone 6 completion:** [Private workspace completion record](docs/milestone-6-completion.md)
- **Milestone 7 plan:** [Job-source coverage roadmap](docs/milestone-7-source-coverage-plan.md)

The deployed version is a secured portfolio application. Visitors can search configured public sources and run Smart Fit without saving. Signed-in users can privately save searched jobs and reduced Smart Fit report summaries. Creating shared demo postings, importing CSV files, and deleting shared postings remain admin-only actions protected by an `X-Admin-API-Key` header.

Do not upload sensitive personal information, secrets, API keys, database URLs, or confidential employer/customer data.

## Screenshots

### Online job search

MarketLens searches configured public job sources and normalizes postings into selectable cards.

![Online job search results](docs/screenshots/online-job-search.png)

### Ranked Smart Fit comparison

Users can select multiple jobs and compare them against the same resume. The ranking explains score gaps, resume evidence, and runner-up gaps.

![Ranked Smart Fit comparison](docs/screenshots/job-fit-ranking.png)

### Role-aware gap report

Detailed reports separate direct role evidence from general resume signals and surface capability gaps that exact keyword matching would miss.

![Role-aware gap report](docs/screenshots/role-aware-gap-report.png)

### Coaching actions and requirement breakdown

The report prioritizes next actions and keeps hard requirements separate from broader coaching guidance.

![Coaching actions and requirement breakdown](docs/screenshots/coaching-actions-breakdown.png)

## Problem

Career advice is often vague, and job descriptions are noisy. Students and career-switchers are told to “learn cloud,” “build projects,” or “get better at AI,” but it is hard to know which skills are actually showing up in the roles they want or which roles fit their current resume best.

MarketLens turns messy job postings into evidence. Instead of guessing what to learn next, users can compare their resume against real job descriptions, rank roles by fit, and see which missing skills matter most.

## Current Product Workflow

```text
Open MarketLens
Sign in when private saving is needed
Upload or paste a resume
Search configured public job sources
Filter by level and optionally location
Review source coverage and search notes
Select one or more returned jobs
Compare selected jobs with role-aware Smart Fit
Save promising searched jobs
Explicitly save reduced Smart Fit report summaries
Revisit or delete private records from dedicated tabs
```

Manual pasted-job comparison remains available for jobs outside the configured online sources:

```text
Upload or paste resume
Paste one or more job descriptions
Separate multiple pasted jobs with ---
Analyze and rank each job independently
Explicitly save a reduced report summary when signed in
```

The interface is organized into **Smart Fit**, **Saved Jobs**, **Saved Reports**, and **Market Data**. Smart Fit remains mounted while switching tabs so in-progress search and analysis state is preserved.

Demo and smoke-test docs:

- [`docs/portfolio-demo-walkthrough.md`](docs/portfolio-demo-walkthrough.md)
- [`docs/portfolio-screenshot-guide.md`](docs/portfolio-screenshot-guide.md)
- [`docs/milestone-1-manual-comparison-smoke-test.md`](docs/milestone-1-manual-comparison-smoke-test.md)
- [`docs/milestone-2-online-job-search-smoke-test.md`](docs/milestone-2-online-job-search-smoke-test.md)
- [`docs/milestone-6-completion.md`](docs/milestone-6-completion.md)
## Current Demo Capabilities

All visitors can:

- view the clearly labeled sample Market Data tab
- upload `.txt`, `.md`, `.pdf`, or `.docx` resumes for request-time text extraction
- paste resume text manually
- search configured public Greenhouse, Lever, Remote OK, and Remotive sources
- search across multiple role families and filter by experience level and location
- inspect source coverage notes, warnings, and fallback links
- compare one to ten searched or manually pasted jobs through Smart Fit
- view ranked results, requirement coverage, matches, gaps, limitations, and coaching actions
- run deterministic analysis when model-assisted extraction is unavailable

Signed-in users can additionally:

- save searched jobs privately
- prevent duplicate saves of the same external posting
- reopen and delete saved jobs
- explicitly save reduced Smart Fit report summaries
- revisit and delete private saved reports
- move between Smart Fit, Saved Jobs, Saved Reports, and Market Data without losing active Smart Fit state

MarketLens does not automatically save analysis inputs. Raw resume text and full job descriptions are not persisted inside saved-report records. Saved reports do contain derived fit summaries, skill names, gaps, coaching guidance, and job metadata.

Admin-only shared-data actions require the `X-Admin-API-Key` header:

- `POST /postings`
- `POST /import/csv`
- `DELETE /postings/{posting_id}`
## Backend Features

The FastAPI backend currently supports:

- `GET /health` — health check
- `GET /me` — return the verified authenticated user
- `GET /postings` and `GET /postings/{posting_id}` — read shared sample postings
- `GET /jobs/search` — normalize configured public job sources with role, industry evidence, level, location, coverage, and fallback metadata
- `POST /skills/extract` — extract recognized skills from text
- `GET /skills/top`, `GET /skills/by-company`, and `GET /skills/by-role` — aggregate the shared sample dataset
- `POST /analysis/resume` — compare resume skills against shared sample postings
- `POST /analysis/custom` — run the simpler skill-gap engine against pasted descriptions
- `POST /analysis/resume-file/extract` — extract request-time resume text from supported files
- `POST /analysis/smart` — run evidence-aware Smart Fit against one job
- `POST /analysis/smart/batch` — analyze and rank one to ten jobs
- `GET /analysis/model-status` — report optional model configuration without exposing secrets
- authenticated saved-job create/list/delete endpoints with user ownership filtering
- authenticated saved-report create/list/read/delete endpoints with user ownership filtering
- admin-protected shared posting creation, CSV import, and deletion
## Online Job Search Sources

MarketLens uses public job APIs instead of scraping closed job boards.

Configured source types:

- **Greenhouse Job Board API** — company-specific ATS boards
- **Lever Postings API** — company-specific ATS boards
- **Remote OK public JSON feed** — remote-first job feed
- **Remotive public API** — remote-first job feed with search/category support

MarketLens does **not** claim to search all of LinkedIn, Indeed, Handshake, Workday, company career pages, or school career portals. When no results are found, the API returns source-coverage metadata, human-readable search notes, and fallback search links so the user can continue outside the configured API-friendly sources and paste those jobs back into Smart Fit.

### Role-family search behavior

Search is no longer software-only. The backend detects role-family intent from the query and uses family-specific title matching.

Currently supported families include:

```text
software, finance, data, cybersecurity, product, marketing, operations, healthcare, design
```

Examples:

```text
finance internship
accounting internship
financial analyst internship
data analyst internship
cybersecurity internship
marketing intern
software engineer intern
backend developer
```

For finance/accounting, the matcher recognizes signals such as:

```text
finance, financial analyst, accounting, accountant, audit, tax, FP&A, treasury,
investment banking, valuation, credit analyst, portfolio analyst, summer analyst
```

It also protects against level-only false positives. For example, `finance internship` should match `Finance Intern` or `Accounting Intern`, but not `Sales Intern` or `Software Engineer Intern` merely because those titles contain `Intern`.

### Experience level behavior

- `level=any` keeps the search general-purpose and can return senior, mid-level, entry-level, or internship roles.
- `level=intern` only returns internship/co-op-looking roles.
- `level=entry`, `level=mid`, and `level=senior` filter by experience signal.
- Query text can infer level intent, such as `SWE Intern`, `entry level finance`, or `senior product manager`.

### Location behavior

- `Philadelphia` means Philadelphia/Philly plus U.S.-remote fallback; it does not include Pittsburgh.
- `PA` or `Pennsylvania` can include Philadelphia, Pittsburgh, PA-wide, and U.S.-remote roles.
- `Remote` means U.S.-remote or worldwide-remote roles unless the source clearly labels a non-U.S. country-specific remote role.
- Blank location means broad U.S./U.S.-remote matching.

### Source coverage limitations

Public remote-job APIs are stronger for remote/general roles than for campus internships. Finance/accounting internships are especially likely to appear on Handshake, Workday-backed company career pages, LinkedIn, Indeed, school portals, and company internship pages. MarketLens handles that honestly by surfacing no-result explanations and fallback links rather than pretending those sources were searched.

Manual pasted-job analysis remains available for any posting copied from outside the configured sources.

Source coverage is configurable through backend environment variables:

```text
JOB_SEARCH_GREENHOUSE_BOARDS=datadog,airbnb,figma
JOB_SEARCH_LEVER_SITES=github,postman,benchling
JOB_SEARCH_REMOTEOK_ENABLED=true
JOB_SEARCH_REMOTIVE_ENABLED=true
```

## Frontend Features

The React frontend currently supports:

- Clerk sign-in, sign-up, sign-out, and user controls
- resume upload and manual resume text entry
- online job search with level and optional location filters
- searched-job cards with source, company, location, link, and extracted skills
- selection and Smart Fit comparison for searched jobs
- manual one-job or multi-job description entry using `---`
- ranked Smart Fit reports with role-aware evidence, capability gaps, and coaching actions
- explicit save controls for searched jobs and reduced Smart Fit report summaries
- private Saved Jobs and Saved Reports workspaces with deletion
- a tabbed layout for Smart Fit, Saved Jobs, Saved Reports, and Market Data
- preserved Smart Fit state while switching tabs
- clearly labeled sample market analytics and the secondary sample-dataset comparison tool
- visible model-assisted availability and deterministic fallback messaging
- responsive layouts plus loading, empty, warning, and error states
## Security and Privacy Notes

MarketLens is a portfolio application, not a service for highly sensitive personal data.

Current security and privacy controls include:

- Clerk-managed authentication instead of custom password storage
- backend verification of Clerk session tokens
- authorized frontend-origin restrictions and CORS configuration
- server-side ownership filters on every private saved-job and saved-report read/delete operation
- cross-user private-record requests returning `404`
- analysis remaining non-persistent unless the user explicitly saves a result
- raw resume text and full job descriptions excluded from saved-report persistence
- backend-only model provider keys and model-status transparency
- redaction of obvious contact details before configured model-provider calls
- admin API key protection for shared posting write/delete endpoints
- request size limits, CSV limits, and public analysis rate limiting
- SQLAlchemy ORM usage instead of raw string-built SQL queries
- Dependabot and GitHub Actions checks

Derived saved-report data can include fit summaries, skill names, gaps, coaching recommendations, and job metadata. Users should still avoid uploading Social Security numbers, medical or financial details, API keys, passwords, confidential employer information, or other unnecessary sensitive data.

See [`SECURITY.md`](SECURITY.md) for the security policy and known limitations.
## Quality and CI

Current checks include:

- backend API tests for job posting creation, CSV import, admin API key protection, input validation, resume extraction, model status, and Smart Fit batch comparison
- backend unit tests for skill extraction, job search normalization/filtering, role-family search, and Smart Fit analysis behavior
- backend role-aware Smart Fit tests across software, data, cybersecurity, finance, product, healthcare, operations, and admin-style roles
- backend evaluation cases for Smart Fit analysis
- frontend production build validation
- Docker image build validation for the backend and frontend
- GitHub Actions continuous integration on pushes and pull requests to `main`
- weekly Dependabot dependency checks

## Running Quality Checks Locally

Run backend tests:

```bash
cd backend
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest
```

Run the frontend production build:

```bash
cd frontend
npm install
npm run build
```

Run both apps locally:

```bash
# terminal 1
cd backend
source .venv/bin/activate
python -m uvicorn app.main:app --reload

# terminal 2
cd frontend
npm run dev
```

## Roadmap

### Milestone 1 — Manual Job Comparison Workflow: complete

- resume upload and paste
- manual job-description comparison
- multi-job splitting and Smart Fit ranking
- detailed per-job reports

### Milestone 2 — Online Job Search + Smart Fit Comparison: complete

- normalized Greenhouse, Lever, Remote OK, and Remotive search
- level and location filtering
- selected-job Smart Fit comparison
- source coverage metadata, warnings, and fallback links

### Milestone 3 — Role-Aware Smart Fit Intelligence: complete

- role-aware scoring across job families
- capability-gap detection beyond exact keywords
- requirement coverage, ranking explanations, and coaching actions
- deterministic and optional model-assisted extraction paths

### Milestone 4 — Portfolio/Demo Packaging: complete

- Railway deployment
- Docker and GitHub Actions CI
- demo walkthroughs, screenshots, and repository presentation

### Milestone 5 — Authentication + Private Data Foundation: complete

- Clerk authentication UI
- verified backend sessions
- user-owned private database records
- authorization and ownership-isolation tests
- analyze-without-saving as the default

### Milestone 6 — Saved Jobs, Saved Reports, and Private Dashboard: complete

- private saved searched jobs with duplicate prevention and deletion
- explicitly saved reduced Smart Fit report summaries
- private report history with read and delete controls
- tabbed Smart Fit, Saved Jobs, Saved Reports, and Market Data interface
- Smart Fit state preservation while switching tabs
- production smoke test covering authentication, saving, refresh persistence, deletion, privacy visibility, and tab state

Deferred optional additions:

- saved searches, alerts, collections, or folders
- saving a manually pasted job as a standalone Saved Job record; its Smart Fit report can already be saved

See [`docs/milestone-6-completion.md`](docs/milestone-6-completion.md).

### Milestone 7 — Better Job Source Coverage: in progress

The next major limitation is recall: precise filtering cannot return roles that are absent from the configured sources.

Planned work:

- model search intent as separate job-function, industry, experience-level, and location dimensions
- build a reusable industry taxonomy
- create a configurable organization/source registry with coverage metadata
- expand legitimate public Greenhouse and Lever boards plus suitable public APIs
- improve internship and entry-level coverage
- improve sports, entertainment, healthcare, finance, education, nonprofit, media, and other non-software coverage
- improve user-facing source coverage explanations
- provide responsible user-assisted workflows for Workday, Handshake, LinkedIn, Indeed, and other closed sources without scraping them
- add recall and precision regression tests across industries

See [`docs/milestone-7-source-coverage-plan.md`](docs/milestone-7-source-coverage-plan.md) and [issue #21](https://github.com/jpdiguisppe/marketlens-career-intelligence/issues/21).

### Milestone 8 — Optional AI-Assisted Analysis: partially started

Already implemented:

- backend-only provider configuration
- model-status transparency
- optional model-assisted extraction
- obvious contact-detail redaction
- deterministic fallback when model assistance is unavailable

Potential later work:

- stronger semantic requirement parsing and evidence matching
- more personalized coaching explanations
- cost, latency, and evaluation controls for regular model usage
- optional agent-style workflows
