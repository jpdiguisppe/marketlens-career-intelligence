# MarketLens Career Intelligence

MarketLens is a full-stack career intelligence platform that compares resume evidence against real job descriptions, ranks role fit, and turns noisy postings into clearer skill gaps and learning priorities.

## Live Demo

- **Frontend app:** [MarketLens live demo](https://marketlens-career-intelligence-production-8a34.up.railway.app)
- **Backend API docs:** [FastAPI Swagger UI](https://marketlens-career-intelligence-production.up.railway.app/docs)
- **Backend health check:** [API health endpoint](https://marketlens-career-intelligence-production.up.railway.app/health)

The deployed version is a secured portfolio/demo app. Public visitors can view the saved demo dataset, explore skill dashboards, upload or paste non-sensitive resume text, search configured public job boards, paste job descriptions, and run non-saved Smart Fit comparisons. Creating postings, importing CSV files, and deleting saved postings are admin-only actions protected by an `X-Admin-API-Key` header.

Do not upload sensitive personal information, secrets, API keys, database URLs, or confidential employer/customer data.

## Problem

Career advice is often vague, and job descriptions are noisy. Students, early-career candidates, and working professionals are told to “learn cloud,” “build projects,” or “get better at AI,” but it is hard to know which skills are actually showing up in the roles they want or which roles fit their current resume best.

MarketLens turns messy job postings into evidence. Instead of guessing what to learn next, users can search for roles, compare their resume against real job descriptions, rank jobs by fit, and see which missing skills matter most.

## Current Milestone: Online Job Search + Smart Fit Comparison

The active product workflow is:

```text
Upload or paste resume
Search configured public job boards or paste job descriptions manually
Filter searched roles by level: any, intern, entry, mid, senior
Select one or more job results
Compare selected jobs with Smart Fit
Rank jobs against the resume
Explain why the ranking happened
Inspect each job's detailed Smart Fit report
```

For manual comparison, put a line containing only `---` between each pasted posting. The frontend detects the job count before analysis and uses the backend batch endpoint to rank the jobs.

Smoke-test checklists:

- [`docs/milestone-1-manual-comparison-smoke-test.md`](docs/milestone-1-manual-comparison-smoke-test.md)
- [`docs/milestone-2-online-job-search-smoke-test.md`](docs/milestone-2-online-job-search-smoke-test.md)

## Current Demo Capabilities

Public visitors can:

- view the saved demo job posting dataset
- view top skills, company breakdowns, and role-category breakdowns
- upload `.txt`, `.md`, `.pdf`, or `.docx` resumes for text extraction
- paste resume text manually
- search configured public Greenhouse job boards
- filter searched jobs by `any`, `intern`, `entry`, `mid`, or `senior` level
- use typed searches such as `SWE`, `SWE Intern`, `entry level SWE`, or `senior SWE`
- select searched jobs and compare them with Smart Fit
- paste one or more job descriptions without saving them to the shared database
- separate multiple pasted jobs with `---`
- run Smart Fit analysis against one job
- run batch Smart Fit comparison against 2–10 jobs
- view ranked jobs, top matches, top gaps, and detailed reports per job
- check whether model-assisted extraction is configured

Admin-only actions require the `X-Admin-API-Key` header:

- `POST /job-postings`
- `POST /job-postings/import-csv`
- `DELETE /job-postings`

This keeps the public demo useful while preventing anonymous users from modifying or deleting shared demo data.

## Job Search Scope

Online job search currently uses configured public Greenhouse job boards. A no-results response means no matching jobs were found in those configured sources, not that no such jobs exist anywhere.

Current default configured boards:

```text
datadog, airbnb, figma, duolingo, roblox, scaleai, hubspot, cloudflare, verkada
```

The backend supports overriding that list with:

```text
JOB_SEARCH_GREENHOUSE_BOARDS=companytoken1,companytoken2,companytoken3
```

Level behavior:

```text
query=SWE&level=any      -> general software engineering search
query=SWE&level=intern   -> internship/co-op-looking results only
query=SWE Intern         -> inferred internship search
query=entry level SWE    -> inferred entry-level search
query=senior SWE         -> inferred senior search
```

Manual pasted-job comparison remains available for jobs outside the configured search sources.

## Backend Features

The FastAPI backend currently supports:

- `GET /health` — health check
- `GET /job-postings` — list saved demo postings
- `GET /job-postings/{posting_id}` — retrieve one saved posting
- `GET /jobs/search` — search configured external job boards with optional `query`, `location`, `level`, and `limit`
- `POST /skills/extract` — extract skills from pasted text
- `GET /skills/top` — view overall skill frequency
- `GET /skills/top-by-company` — compare skill frequency by company
- `GET /skills/top-by-role` — compare skill frequency by role category
- `POST /resume/analyze` — compare resume skills against saved postings
- `POST /analysis/custom` — compare resume skills against pasted job descriptions using the simpler skill-gap engine
- `POST /analysis/resume-file/extract` — extract text from `.txt`, `.md`, `.pdf`, or `.docx` resume uploads
- `POST /analysis/smart` — run evidence-aware Smart Fit analysis against one pasted job description
- `POST /analysis/smart/batch` — run Smart Fit analysis against 1–10 jobs and return ranked results
- `GET /analysis/model-status` — report whether model-assisted extraction is configured without exposing secrets
- `POST /job-postings` — admin-protected manual job posting creation
- `POST /job-postings/import-csv` — admin-protected CSV import
- `DELETE /job-postings` — admin-protected clearing of saved postings

## Frontend Features

The React frontend currently supports:

- resume upload and extraction for supported resume files
- manual resume text entry
- online job search with role query, level dropdown, and optional location
- selectable external job result cards
- comparing selected searched jobs through Smart Fit batch analysis
- manual job description entry
- `---`-based multiple-job splitting
- visible detected pasted-job count before analysis
- backend batch Smart Fit comparison
- ranked job results
- ranking explanation summary
- top matches and top gaps for each ranked job
- detail switching between ranked job reports
- disabled AI toggle when backend model-assisted extraction is not configured
- dashboard summary cards for saved demo data
- saved job posting table
- overall top skills list with simple bar visuals
- skills grouped by company
- skills grouped by role category
- empty and error states

## Security and Privacy Notes

MarketLens is currently a portfolio/demo application, not a production service for sensitive personal data.

Current security controls include:

- admin API key protection for write/delete endpoints
- CORS configuration for the deployed frontend origin
- request size limits on free-text fields and uploaded resume files
- CSV upload size and row-count limits
- basic public endpoint rate limiting for analysis endpoints
- SQLAlchemy ORM usage instead of raw string-built SQL queries
- resume uploads are processed for the current request and are not saved to the shared database
- external job search results are normalized before display and analysis
- model-assisted extraction is disabled unless configured through backend-only environment variables
- Dependabot checks for backend, frontend, and GitHub Actions dependencies

Do not upload real Social Security numbers, addresses, phone numbers, medical details, financial details, API keys, passwords, database URLs, or confidential employer/customer data.

See [`SECURITY.md`](SECURITY.md) for the security policy and known limitations.

## Quality and CI

Current checks include:

- backend API tests for job posting creation, CSV import, admin API key protection, input validation, resume extraction, model status, external job search, and Smart Fit batch comparison
- backend unit tests for skill extraction, job-search level filtering, and Smart Fit analysis behavior
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

Build Docker images:

```bash
docker build -t marketlens-backend ./backend
docker build --build-arg VITE_API_BASE_URL=http://localhost:8000 -t marketlens-frontend ./frontend
```

## Running the Backend Locally

From the project root:

```bash
cd backend
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/docs
```

For local admin-protected endpoints, set an admin key before starting the backend:

```bash
export ADMIN_API_KEY=local-dev-admin-key
```

Then pass this header in Swagger or API requests:

```text
X-Admin-API-Key: local-dev-admin-key
```

## Running the Frontend Locally

Open a second terminal tab from the project root:

```bash
cd frontend
npm install
npm run dev
```

Then open:

```text
http://localhost:5173
```

The frontend expects the backend to be running at:

```text
http://127.0.0.1:8000
```

You can override that by creating a local `.env` file inside `frontend/`:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Persistence

MarketLens uses SQLAlchemy for database-backed storage.

For local development, the backend defaults to SQLite:

```text
sqlite:///./marketlens.db
```

In Docker, the backend uses a named Docker volume and stores SQLite data at:

```text
/app/data/marketlens.db
```

For public deployment, MarketLens uses PostgreSQL by setting a `DATABASE_URL` environment variable.

## CSV Format

CSV imports should use this header row:

```csv
company,title,location,role_category,experience_level,description
```

Required columns:

- `company`
- `title`
- `description`

Optional columns:

- `location`
- `role_category`
- `experience_level`

A sample file is included at:

```text
data/sample_job_postings.csv
```

CSV import is admin-protected in the deployed demo and requires the `X-Admin-API-Key` header.

## Running with Docker

From the project root:

```bash
docker compose up --build
```

Then open:

```text
http://localhost:5173
```

The backend API will be available at:

```text
http://localhost:8000
```

FastAPI docs will be available at:

```text
http://localhost:8000/docs
```

Stop the containers with:

```bash
docker compose down
```

To also delete the Docker-managed SQLite database volume:

```bash
docker compose down -v
```

## Railway Deployment

MarketLens is deployed on Railway as an isolated monorepo with separate backend and frontend services plus a Railway Postgres database.

Deployment guide:

```text
docs/railway-deployment.md
```

Expected Railway services:

- `backend` from `/backend`
- `frontend` from `/frontend`
- `Postgres` database service

Important backend variables:

```text
DATABASE_URL=<Railway Postgres connection string>
ADMIN_API_KEY=<long random secret value>
CORS_ALLOWED_ORIGINS=<public frontend Railway URL>
```

Important frontend variable:

```text
VITE_API_BASE_URL=<public backend Railway URL>
```

Never commit or publicly share `DATABASE_URL`, Postgres connection strings, `ADMIN_API_KEY`, GitHub tokens, model-provider API keys, or other secrets.

## Project Structure

```text
.github/
  dependabot.yml
  workflows/
    ci.yml
backend/
  app/
    analysis/
    database.py
    job_search.py
    main.py
    models.py
    resume_files.py
    skill_extractor.py
  tests/
frontend/
  src/
    api.ts
    App.tsx
    main.tsx
    styles.css
    types.ts
data/
  sample_job_postings.csv
docs/
  images/
  auth-user-ownership-roadmap.md
  database-schema.md
  evaluation-set.md
  milestone-1-manual-comparison-smoke-test.md
  milestone-2-online-job-search-smoke-test.md
  project-plan.md
  railway-deployment.md
SECURITY.md
docker-compose.yml
README.md
```

## Roadmap

### Milestone 1: Manual Job Comparison Workflow

Status: complete.

- resume upload and extraction
- manual job description paste
- multi-job detection with `---`
- backend batch comparison
- ranked results
- ranking explanation
- detail switching between ranked jobs
- local tests and frontend build check
- live Railway verification

### Milestone 2: Online Job Search

Status: base functionality complete.

- backend provider interface for external job sources
- public Greenhouse job-board search
- normalized job results
- cleaned plain-text job descriptions
- level support: `any`, `intern`, `entry`, `mid`, `senior`
- typed query level inference such as `SWE Intern` and `senior SWE`
- frontend search fields for role, level, and location
- selectable searched job results
- comparison of selected searched jobs through the Smart Fit batch endpoint
- live Railway verification

### Milestone 3: Better Source Coverage and Search Quality

- expand configurable source coverage while avoiding scraping-restricted sites
- improve no-results guidance
- improve result ranking and de-duplication
- add clearer source/provider metadata in the UI
- consider additional legal APIs such as government or partner job feeds

### Milestone 4: AI-Assisted Intelligence

- safely enable backend-only model-provider configuration
- test whether model-assisted extraction improves unknown skill detection
- add stricter provider-specific rate limiting
- keep deterministic fallback behavior

### Milestone 5: Accounts and Saved Reports

- add authentication
- add user-owned resumes, searches, and reports
- save analysis history per user
- consider PostgreSQL Row Level Security after ownership is stable

### Milestone 6: Polish, Demo, and Resume Packaging

- polish UI after workflows are stable
- refresh screenshots
- record demo walkthrough
- write final project story and resume bullets
