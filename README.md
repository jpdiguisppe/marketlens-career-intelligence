# MarketLens Career Intelligence

MarketLens is a career intelligence platform that analyzes job postings to identify in-demand skills, compare role requirements, and generate personalized skill-gap insights for early-career software, AI, cloud, and systems roles.

## Problem

Career advice is often vague, and job descriptions are noisy. Students and early-career candidates are told to “learn cloud,” “build projects,” or “get better at AI,” but it is hard to know which skills are actually showing up in the roles they want.

MarketLens turns messy job postings into evidence. Instead of guessing what to learn next, users can analyze real postings and see which skills, tools, and experience patterns appear most often.

## MVP Goal

The first version of MarketLens focuses on a Job Skill Analyzer.

Users will be able to:

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

## Persistence

MarketLens now uses SQLAlchemy for database-backed storage.

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
backend/
  app/
    database.py
    main.py
    models.py
    skill_extractor.py
  requirements.txt
frontend/
data/
  sample_job_postings.csv
docs/
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

### Phase 6: Polish and Deployment

- Add Docker setup
- Add tests
- Add GitHub Actions
- Deploy the app
- Add screenshots and a demo write-up

## Long-Term Ideas

- AI-generated learning roadmaps
- Company-specific career intelligence
- Regional market trends
- Role comparison between backend, systems, cloud, and AI jobs
- Vector search over job postings
- Authentication and saved user profiles
- Browser extension for saving postings from job sites
- Public job API integrations

## Status

MarketLens is currently at **Backend MVP v0.5**. The backend can accept manual job postings, import postings from CSV, persist postings in a local SQLite database, extract skills, and return skill-frequency comparisons overall, by company, and by role category.
