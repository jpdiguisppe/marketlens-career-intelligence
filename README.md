# MarketLens Career Intelligence

MarketLens is a full-stack career intelligence platform that analyzes saved job postings to identify in-demand skills, compare role requirements, and generate personalized resume skill-gap insights for early-career software, AI, cloud, and systems roles.

## Problem

Career advice is often vague, and job descriptions are noisy. Students and early-career candidates are told to “learn cloud,” “build projects,” or “get better at AI,” but it is hard to know which skills are actually showing up in the roles they want.

MarketLens turns messy job postings into evidence. Instead of guessing what to learn next, users can analyze real postings and see which skills, tools, and experience patterns appear most often.

## Demo

### Resume Gap Analysis

MarketLens compares pasted resume text against the skills extracted from saved job postings, then returns a match score, matched skills, missing skills, and learning priorities.

![MarketLens resume gap analysis](docs/images/marketlens-resume-gap-analysis.png)

### Skill Trend Dashboard

The dashboard summarizes saved postings, unique skills, top skills, company-specific skill signals, role-category skill signals, and saved job posting details.

![MarketLens skills dashboard](docs/images/marketlens-skills-dashboard.png)

### Saved Job Postings

Imported postings are persisted in a local database and displayed with extracted technical skills.

![MarketLens saved job postings](docs/images/marketlens-job-postings.png)

### FastAPI Documentation

The backend exposes documented API endpoints through Swagger UI, including CSV import, skill extraction, skill comparison, and resume analysis.

![MarketLens API docs](docs/images/marketlens-api-docs.png)

## MVP Goal

The first version of MarketLens focuses on a Job Skill Analyzer and Resume Gap Analyzer.

Users can:

- Add job postings manually or through a CSV import
- Store posting details such as company, title, location, role category, and description
- Extract technical skills from job descriptions
- View top skills by frequency
- Compare skill requirements across companies and role categories
- Paste a resume and compare it against target job postings
- Generate a skill-gap report with recommended learning priorities

## Current Backend Features

The FastAPI backend currently supports:

- `GET /health` — health check
- `POST /job-postings` — manually add one job posting
- `GET /job-postings` — list saved job postings
- `GET /job-postings/{posting_id}` — retrieve one saved job posting
- `DELETE /job-postings` — clear all saved job postings
- `POST /job-postings/import-csv` — upload a CSV file of job postings
- `POST /skills/extract` — extract skills from pasted text
- `GET /skills/top` — view overall skill frequency
- `GET /skills/top-by-company` — compare skill frequency by company
- `GET /skills/top-by-role` — compare skill frequency by role category
- `POST /resume/analyze` — compare resume skills against saved postings

## Current Frontend Features

The React frontend currently supports:

- Dashboard summary cards
- Saved job posting table
- Overall top skills list with simple bar visuals
- Skills grouped by company
- Skills grouped by role category
- Resume gap analysis panel
- Target role category dropdown generated from saved postings
- Match score, matched skills, missing skills, resume skills, and learning priorities
- Refresh button for reloading backend data
- Empty and error states

## Quality and CI

MarketLens includes automated quality checks so future changes are less likely to break existing behavior.

Current checks include:

- Backend unit tests for skill extraction
- Backend API tests for job posting creation, CSV import, skill counting, and resume analysis
- Frontend production build validation
- GitHub Actions continuous integration on pushes and pull requests to `main`

## Resume Gap Analysis

The resume analyzer compares skills extracted from pasted resume text against skills extracted from saved job postings.

Users can compare against all saved postings or narrow the analysis to one role category, such as `Backend SWE`, `Systems/Cloud`, or `Data/Backend`.

The analysis returns:

- Resume skills found
- Target skills from job postings
- Matched skills
- Missing skills
- Match percentage
- Learning priorities based on missing high-frequency skills

## Persistence

MarketLens uses SQLAlchemy for database-backed storage.

For local development, the backend defaults to SQLite:

```text
sqlite:///./marketlens.db
```

That means saved and imported job postings persist after the backend restarts.

Later, the same database layer can use PostgreSQL by setting a `DATABASE_URL` environment variable.

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

## Planned Tech Stack

- **Frontend:** React + TypeScript
- **Backend:** Python + FastAPI
- **Database:** SQLite locally, PostgreSQL later
- **AI/NLP:** skill dictionary first, AI-assisted extraction later
- **Charts:** Recharts or Chart.js
- **DevOps:** Docker + GitHub Actions
- **Deployment:** Render, Azure, or AWS

## Project Structure

```text
.github/
  workflows/
    ci.yml
backend/
  app/
    database.py
    main.py
    models.py
    skill_extractor.py
  tests/
    test_api.py
    test_skill_extractor.py
  requirements.txt
frontend/
  src/
    api.ts
    App.tsx
    main.tsx
    styles.css
    types.ts
  package.json
  package-lock.json
  tsconfig.json
  tsconfig.node.json
  index.html
data/
  sample_job_postings.csv
docs/
  images/
    marketlens-api-docs.png
    marketlens-job-postings.png
    marketlens-resume-gap-analysis.png
    marketlens-skills-dashboard.png
  project-plan.md
  database-schema.md
README.md
```

## Roadmap

### Phase 1: Project Foundation

- Create project structure
- Write README and planning docs
- Set up FastAPI backend
- Add a health-check endpoint

### Phase 2: Job Posting Storage

- Define job posting data model
- Add create/list API endpoints
- Add sample job posting data
- Add CSV import for batches of job postings
- Add database-backed persistence
- Prepare PostgreSQL support through `DATABASE_URL`

### Phase 3: Skill Extraction

- Build a skill dictionary
- Extract skills from job descriptions
- Normalize skill names such as `AWS`, `Amazon Web Services`, and `cloud`
- Store extracted job-skill relationships

### Phase 4: Dashboard

- Build React dashboard
- Show top skills overall
- Compare skills by company
- Compare skills by role category

### Phase 5: Resume Gap Analysis

- Accept pasted resume text
- Extract resume skills
- Compare resume skills against selected postings
- Generate strong matches, missing skills, and suggested learning priorities

### Phase 6: Polish, Quality, and Deployment

- Add screenshots and a demo write-up
- Add backend tests
- Add GitHub Actions CI
- Add Docker setup
- Deploy the app

## Long-Term Ideas

- AI-generated learning roadmaps
- Company-specific career intelligence
- Regional market trends
- Role comparison between backend, systems, cloud, and AI jobs
- Vector search over job postings
- Authentication and saved user profiles
- Browser extension for saving postings from job sites
- Public job API integrations
- Production security hardening, rate limiting, and monitoring

## Status

MarketLens is currently at **Full-Stack MVP v0.3**. The backend can accept manual job postings, import postings from CSV, persist postings in a local SQLite database, extract skills, return skill-frequency comparisons, and compare resume skills against target postings. The frontend displays those insights in a React dashboard with a resume gap analysis workflow. The repo now includes backend tests and GitHub Actions CI for backend tests and frontend build validation.
