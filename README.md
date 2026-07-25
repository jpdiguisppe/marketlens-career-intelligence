# MarketLens Career Intelligence

MarketLens is a deployed full-stack career-intelligence platform that searches configured public job sources, compares resume evidence against real job descriptions, ranks role fit, and turns noisy postings into clearer skill gaps, capability gaps, and learning priorities.

## Project Highlights

- **Deployed full-stack app:** React + TypeScript frontend, FastAPI backend, SQLAlchemy persistence, and Railway deployment.
- **Cross-sector job search:** Occupation-aware matching supports careers across technology, business, education, science, engineering, healthcare, public service, creative work, trades, agriculture, hospitality, transportation, and service work.
- **Strict search semantics:** Occupation, experience level, industry, and location are evaluated separately; explicit city searches exclude remote-only roles.
- **Role-aware Smart Fit:** Users can compare a resume against one or more jobs and review evidence, requirement coverage, capability gaps, ranking explanations, and coaching actions.
- **Online + manual workflows:** MarketLens searches public Greenhouse, Lever, named SmartRecruiters employer boards, Remote OK, and Remotive sources; outside postings can still be pasted into Smart Fit manually.
- **Private career workspace:** Clerk-authenticated users can save searched jobs and reduced Smart Fit report summaries with server-side ownership checks.
- **Quality coverage:** 290 backend tests, a 273-candidate formal job-search benchmark, integrated occupation/level/location matrices, frontend and Docker builds, and reviewed live-provider smoke tests.

## Tech Stack

| Area | Tools |
| --- | --- |
| Frontend | React, TypeScript, Vite, CSS |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy |
| Database | SQLite locally; PostgreSQL-ready through `DATABASE_URL` |
| Authentication | Clerk frontend sessions with backend token verification |
| Job sources | Greenhouse, Lever, named SmartRecruiters employer boards, Remote OK, Remotive |
| Testing / Quality | pytest, deterministic search evaluation, GitHub Actions, Docker builds, Dependabot |
| Deployment | Railway frontend and backend |

## Live Demo

- **Frontend app:** [MarketLens live demo](https://marketlens-career-intelligence-production-8a34.up.railway.app)
- **Backend API docs:** [FastAPI Swagger UI](https://marketlens-career-intelligence-production.up.railway.app/docs)
- **Backend health check:** [API health endpoint](https://marketlens-career-intelligence-production.up.railway.app/health)
- **Portfolio demo walkthrough:** [How to demo MarketLens](docs/portfolio-demo-walkthrough.md)
- **Milestone 6 completion:** [Private workspace completion record](docs/milestone-6-completion.md)
- **Milestone 7 completion:** [Job-source coverage completion record](docs/milestone-7-completion.md)
- **Milestone 7.1:** [Cross-sector search correctness contract](docs/search-correctness-hardening.md)
- **Validation record:** [Search-hardening validation log](docs/search-hardening-validation-log.md)

The deployed version is a secured portfolio application. Visitors can search configured public sources and run Smart Fit without saving. Signed-in users can privately save searched jobs and reduced Smart Fit report summaries. Shared posting creation, CSV import, and deletion remain admin-only actions protected by an `X-Admin-API-Key` header.

Do not upload sensitive personal information, secrets, API keys, database URLs, or confidential employer/customer data.

## Screenshots

### Online job search

MarketLens searches configured public sources and normalizes postings into selectable cards.

![Online job search results](docs/screenshots/online-job-search.png)

### Ranked Smart Fit comparison

Users can select multiple jobs and compare them against the same resume. The ranking explains score gaps, resume evidence, and runner-up differences.

![Ranked Smart Fit comparison](docs/screenshots/job-fit-ranking.png)

### Role-aware gap report

Detailed reports separate direct role evidence from general resume signals and surface capability gaps that exact keyword matching would miss.

![Role-aware gap report](docs/screenshots/role-aware-gap-report.png)

### Coaching actions and requirement breakdown

The report prioritizes next actions and keeps hard requirements separate from broader coaching guidance.

![Coaching actions and requirement breakdown](docs/screenshots/coaching-actions-breakdown.png)

## Problem

Career advice is often vague, and job descriptions are noisy. Students and career-switchers are told to “learn cloud,” “build projects,” or “get better at AI,” but it is hard to know which skills actually appear in the roles they want or which jobs fit their current evidence best.

MarketLens turns postings into evidence. Instead of guessing what to learn next, users can compare a resume against real job descriptions, rank opportunities, and see which missing capabilities matter most.

## Current Product Workflow

```text
Open MarketLens
Optionally sign in for private saving
Upload or paste a resume
Search configured public job sources
Choose an experience level and optional location
Review exactly which providers were searched
Inspect ranked and filtered job results
Select one or more jobs
Run role-aware Smart Fit
Explicitly save promising jobs or reduced report summaries
Revisit or delete private records from dedicated tabs
```

Manual pasted-job comparison remains available for postings outside the configured online sources:

```text
Upload or paste a resume
Paste one or more job descriptions
Separate multiple jobs with ---
Analyze and rank each job independently
Optionally save a reduced report summary when signed in
```

The interface is organized into **Smart Fit**, **Saved Jobs**, **Saved Reports**, and **Market Data**. Smart Fit remains mounted while switching tabs so in-progress search and analysis state is preserved.

## Search Correctness Contract

MarketLens evaluates four concerns separately.

### 1. Occupation relevance

Specific occupations require title-level evidence for the requested work. A shared word such as `engineer`, `analyst`, `assistant`, `technician`, `editor`, or `manager` is not enough by itself.

Exact and near-exact titles receive ranking bonuses. Unknown occupations use phrase-first signatures, curated aliases, occupation heads, and meaningful modifiers instead of defaulting to broad role-family acceptance.

Examples of protected distinctions include:

- electrical engineer vs. analytics engineer
- elementary teacher vs. middle-school teacher
- electrician vs. electrical engineer
- medical assistant vs. registered nurse
- policy analyst vs. data analyst
- journalism editor/reporter vs. cinematic video editor
- social worker vs. social-media manager

### 2. Experience level

Supported levels are `any`, `intern`, `entry`, `mid`, and `senior`.

- Internship matching recognizes internships, co-ops, apprenticeships, fellowships, student programs, and guarded seasonal roles.
- Entry matching recognizes explicit junior/new-grad/`I`/rotational evidence and written requirements of up to three years.
- A specific occupation search may also include a plain title with no contradictory experience or seniority evidence. These unlabeled compatible roles rank below explicitly labeled entry jobs.
- Broad family searches such as `computer science` still require actual entry evidence.
- Mid and senior matching uses numbered titles, seniority language, and written experience requirements.
- Occupational uses of `Staff`, such as Staff Reporter or Staff Accountant, are not automatically treated as senior.

### 3. Location

An explicit city search is strict.

- `Philadelphia` includes recognized metro locations such as King of Prussia, Malvern, West Chester, Camden, Cherry Hill, Mount Laurel, and Wilmington.
- It excludes Pittsburgh, New York, California, and remote-only postings.
- `PA` or `Pennsylvania` deliberately broadens the local region.
- `Remote` deliberately requests remote work.
- Blank location keeps a broad U.S./U.S.-remote search.

Recognized metro expansions also exist for New York City, Washington DC, San Francisco, Boston, Chicago, Seattle, and Los Angeles.

### 4. Source coverage

MarketLens uses public APIs instead of scraping closed job boards.

Configured source types:

- **Greenhouse Job Board API** — company-specific public ATS boards
- **Lever Postings API** — company-specific public ATS boards
- **SmartRecruiters Posting API** — a bounded, intent-selected set of named public employer boards
- **Remote OK public JSON feed** — remote-first jobs
- **Remotive public API** — remote-first jobs with search/category support

Named SmartRecruiters boards broaden representation across education, science, engineering, healthcare, government, media, trades, agriculture, delivery/service work, business, and technology. Verified examples include KIPP, AECOM, CRB, Bosch, Eurofins, City of Philadelphia, US Physical Therapy, NBCUniversal, Syngenta Group, and Domino's.

SmartRecruiters is not treated as a universal job board. MarketLens queries a bounded set of intent-selected employers, reports the exact providers searched, and evaluates a bounded number of fully detailed postings.

MarketLens does **not** claim to search all of LinkedIn, Indeed, Handshake, Workday search pages, school portals, or every company career site. Those services remain clearly labeled external continuation options; their results are not scraped or imported.

Zero results are acceptable when the currently searched public employers do not have a valid posting. Irrelevant jobs are not used to fill the page.

## Current Demo Capabilities

All visitors can:

- view the clearly labeled sample Market Data tab
- upload `.txt`, `.md`, `.pdf`, or `.docx` resumes for request-time extraction
- paste resume text manually
- search configured public Greenhouse, Lever, SmartRecruiters, Remote OK, and Remotive sources
- search with separate occupation, industry, experience-level, and location intent
- inspect provider-by-provider fetched/matched coverage, routing notes, warnings, suggestions, and external continuation links
- compare one to ten searched or manually pasted jobs through Smart Fit
- view ranked results, requirement coverage, matches, gaps, limitations, and coaching actions
- use deterministic analysis when model-assisted extraction is unavailable

Signed-in users can additionally:

- save searched jobs privately
- prevent duplicate saves of the same external posting
- reopen and delete saved jobs
- explicitly save reduced Smart Fit report summaries
- revisit and delete private saved reports
- switch between tabs without losing active Smart Fit state

MarketLens does not automatically save analysis inputs. Raw resume text and full job descriptions are not persisted inside saved-report records. Saved reports contain reduced derived summaries, skill names, gaps, coaching guidance, and job metadata.

## Backend API

The FastAPI backend currently supports:

- `GET /health` — health check
- `GET /me` — verified authenticated user
- `GET /postings` and `GET /postings/{posting_id}` — shared sample postings
- `GET /jobs/search` — normalized public-source search with occupation, industry, level, location, coverage, and fallback metadata
- `POST /skills/extract` — recognized skill extraction
- `GET /skills/top`, `GET /skills/by-company`, and `GET /skills/by-role` — sample dataset aggregates
- `POST /analysis/resume` — compare a resume against shared sample postings
- `POST /analysis/custom` — simpler skill-gap analysis for pasted descriptions
- `POST /analysis/resume-file/extract` — request-time resume extraction
- `POST /analysis/smart` — evidence-aware Smart Fit for one job
- `POST /analysis/smart/batch` — analyze and rank one to ten jobs
- `GET /analysis/model-status` — optional model configuration without secret exposure
- authenticated saved-job create/list/read/delete endpoints
- authenticated saved-report create/list/read/delete endpoints
- admin-protected shared posting creation, CSV import, and deletion

## Frontend Features

- Clerk sign-in, sign-up, sign-out, and user controls
- resume upload and manual resume text entry
- online job search with separate occupation, industry, level, and location intent
- provider-by-provider source transparency
- searched-job cards with source, company, location, safe application link, and extracted skills
- multi-job selection and Smart Fit comparison
- manual one-job or multi-job entry using `---`
- ranked Smart Fit reports with evidence, capability gaps, limitations, and coaching actions
- explicit save controls for jobs and reduced reports
- private Saved Jobs and Saved Reports workspaces
- tabbed responsive layout with preserved in-progress Smart Fit state
- deterministic fallback and optional model-assisted status messaging

## Security and Privacy

MarketLens is a portfolio application, not a service for highly sensitive data.

Current controls include:

- Clerk-managed authentication instead of custom password storage
- backend verification of Clerk session tokens
- authorized frontend-origin and CORS restrictions
- server-side user ownership filters for every private read/delete operation
- cross-user private-record requests returning `404`
- analysis remaining non-persistent unless the user explicitly saves a result
- raw resume text and full job descriptions excluded from saved-report persistence
- backend-only model-provider keys and model-status transparency
- redaction of obvious contact details before configured model-provider calls
- admin API key protection for shared posting write/delete endpoints
- request-size, CSV, provider-request, and public-analysis limits
- allowlisted ATS identifiers and safe HTTPS application-link validation
- no automatic redirects to unexpected provider hosts
- SQLAlchemy ORM usage instead of string-built SQL queries
- Dependabot and GitHub Actions checks

See [`SECURITY.md`](SECURITY.md) for the security policy and known limitations.

## Quality and CI

The final search-hardening branch passed:

- **290 backend tests**
- **20 intent cases**
- **273 candidate cases**
- **17 location cases**
- **20 ranking cases**
- **9 routing cases**
- **55 critical cases**
- **27 integrated occupation + entry + location cases** across nine sector groups
- **9 integrated local/remote/wrong-occupation ranking cases**
- **14 mid/senior occupation + location cases** across seven sector groups
- frontend TypeScript/Vite production build
- backend Docker image build
- frontend Docker image build
- strict Philadelphia live-provider smoke across ten representative occupations
- broadened U.S.-wide live-provider smoke across the same occupations

The formal benchmark passes at 100% for intent accuracy, candidate accuracy, recall, precision, negative rejection, location accuracy, ranking accuracy, routing accuracy, and critical-case pass rate. The benchmark also enforces category breadth so a convenient narrow test set cannot silently replace the cross-sector matrix.

See [`docs/search-hardening-validation-log.md`](docs/search-hardening-validation-log.md) for the exact live results and the defects discovered during validation.

## Running Locally

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

The frontend reads its API base URL from `VITE_API_BASE_URL`. Clerk-enabled builds also require `VITE_CLERK_PUBLISHABLE_KEY`.

### Optional job-source configuration

```text
JOB_SEARCH_GREENHOUSE_BOARDS=datadog,airbnb,figma
JOB_SEARCH_LEVER_SITES=github,postman,benchling
JOB_SEARCH_SMARTRECRUITERS_ENABLED=true
JOB_SEARCH_REMOTEOK_ENABLED=true
JOB_SEARCH_REMOTIVE_ENABLED=true
```

Only enabled, registered provider identifiers are accepted.

## Running Quality Checks

Backend suite:

```bash
cd backend
python -m pytest
```

Formal search evaluation:

```bash
cd backend
python scripts/run_job_search_evaluation.py
```

Frontend production build:

```bash
cd frontend
npm ci
npm run build
```

Docker images:

```bash
docker build -t marketlens-backend ./backend
docker build --build-arg VITE_API_BASE_URL=http://localhost:8000 -t marketlens-frontend ./frontend
```

## Resume / Interview Summary

MarketLens is a deployed full-stack career-intelligence application that searches public job APIs, compares resume evidence against multiple postings, ranks role fit, identifies capability gaps, and explains recommendations. The project includes a React frontend, FastAPI backend, secure authentication, private persistence, cross-sector occupation matching, source routing, deterministic evaluation, Docker packaging, CI, and Railway deployment.

Resume bullet:

```text
Built and deployed MarketLens, a full-stack React/FastAPI career-intelligence app that searches public job APIs, compares resumes against multiple postings, ranks role fit, identifies role-specific capability gaps, and validates cross-sector search relevance with deterministic and live-provider test suites.
```

## Roadmap

### Milestone 1 — Manual Job Comparison: complete

- resume upload and paste
- multi-job description splitting
- Smart Fit ranking and detailed reports

### Milestone 2 — Online Job Search: complete

- normalized public job-source search
- level and location filtering
- selected-job Smart Fit comparison
- source coverage metadata and fallback links

### Milestone 3 — Role-Aware Smart Fit: complete

- role-aware evidence and scoring
- capability-gap detection beyond exact keywords
- requirement coverage and coaching actions
- deterministic and optional model-assisted paths

### Milestone 4 — Portfolio Packaging: complete

- Railway deployment
- Docker and GitHub Actions CI
- screenshots, walkthroughs, and repository presentation

### Milestone 5 — Authentication and Private Data: complete

- Clerk authentication
- verified backend sessions
- user-owned private records
- ownership-isolation tests

### Milestone 6 — Saved Jobs, Reports, and Dashboard: complete

- private saved jobs
- explicitly saved reduced reports
- dedicated private tabs and deletion controls
- production authentication and persistence smoke tests

### Milestone 7 — Better Job Source Coverage: complete

- multidimensional job-search intent
- typed and allowlisted source registry
- intent-aware source routing
- stronger early-career and legal credential behavior
- honest provider reporting and external continuation workflow

### Milestone 7.1 — Cross-Sector Search Correctness: complete

- phrase-first occupation matching beyond predefined role families
- strict city/metro behavior with deliberate remote inclusion
- exact/near-exact ranking and conflicting-occupation rejection
- representative validation across nine sector groups
- bounded named SmartRecruiters source expansion
- formal, integrated, full-suite, Docker, and live-provider validation

See [`docs/search-correctness-hardening.md`](docs/search-correctness-hardening.md).

### Milestone 8 — Optional AI-Assisted Analysis: partially started

Already implemented:

- backend-only provider configuration
- model-status transparency
- optional model-assisted extraction
- obvious contact-detail redaction
- deterministic fallback

Potential later work:

- stronger semantic requirement parsing and evidence matching
- more personalized coaching explanations
- cost, latency, and evaluation controls for regular model usage
- optional agent-style workflows
