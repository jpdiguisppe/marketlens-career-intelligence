from pathlib import Path
import re

README_PATH = Path("README.md")
MILESTONE_6_PATH = Path("docs/milestone-6-completion.md")
MILESTONE_7_PATH = Path("docs/milestone-7-source-coverage-plan.md")


def replace_section(text: str, start_heading: str, end_heading: str, replacement: str) -> str:
    pattern = rf"{re.escape(start_heading)}\n.*?(?=\n{re.escape(end_heading)}\n)"
    updated, count = re.subn(pattern, replacement.rstrip(), text, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError(f"Could not replace section: {start_heading}")
    return updated


readme = README_PATH.read_text(encoding="utf-8")

readme = readme.replace(
    "- **Security-conscious demo design:** Public users can analyze non-sensitive text without saving reports, while write/delete endpoints remain admin-protected.",
    "- **Private career workspace:** Clerk-authenticated users can save jobs and reduced Smart Fit report summaries with server-side ownership checks.",
)

readme = readme.replace(
    "- **Auth/private-data plan:** [Milestone 5 planning doc](docs/milestone-5-auth-private-data-plan.md)",
    "- **Milestone 6 completion:** [Private workspace completion record](docs/milestone-6-completion.md)\n- **Milestone 7 plan:** [Job-source coverage roadmap](docs/milestone-7-source-coverage-plan.md)",
)

readme = readme.replace(
    "The deployed version is a secured portfolio/demo app. Public visitors can view the saved demo dataset, explore skill dashboards, upload or paste non-sensitive resume text, search configured public job sources, paste job descriptions manually, and run non-saved Smart Fit comparisons. Creating postings, importing CSV files, and deleting saved postings are admin-only actions protected by an `X-Admin-API-Key` header.",
    "The deployed version is a secured portfolio application. Visitors can search configured public sources and run Smart Fit without saving. Signed-in users can privately save searched jobs and reduced Smart Fit report summaries. Creating shared demo postings, importing CSV files, and deleting shared postings remain admin-only actions protected by an `X-Admin-API-Key` header.",
)

current_workflow = """## Current Product Workflow

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
"""
readme = replace_section(readme, "## Current Product Workflow", "## Current Demo Capabilities", current_workflow)

capabilities = """## Current Demo Capabilities

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
"""
readme = replace_section(readme, "## Current Demo Capabilities", "## Backend Features", capabilities)

backend_features = """## Backend Features

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
"""
readme = replace_section(readme, "## Backend Features", "## Online Job Search Sources", backend_features)

frontend_features = """## Frontend Features

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
"""
readme = replace_section(readme, "## Frontend Features", "## Security and Privacy Notes", frontend_features)

security = """## Security and Privacy Notes

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
"""
readme = replace_section(readme, "## Security and Privacy Notes", "## Quality and CI", security)

roadmap = """## Roadmap

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
"""
roadmap_pattern = r"## Roadmap\n.*\Z"
readme, count = re.subn(roadmap_pattern, roadmap.rstrip() + "\n", readme, count=1, flags=re.DOTALL)
if count != 1:
    raise RuntimeError("Could not replace roadmap")

README_PATH.write_text(readme, encoding="utf-8")

MILESTONE_6_PATH.write_text(
    """# Milestone 6 Completion — Private Career Workspace

Milestone 6 is complete after the production smoke test of the deployed MarketLens application.

## Delivered

- Clerk-authenticated private saved jobs
- duplicate prevention for saved external postings
- saved-job persistence, original-posting links, and deletion
- explicitly saved reduced Smart Fit report summaries
- saved-report list, detail, and deletion flows
- server-side user ownership filtering and cross-user isolation
- support for saving report summaries from searched and manually pasted job analyses
- a tabbed interface for Smart Fit, Saved Jobs, Saved Reports, and Market Data
- preserved Smart Fit state while switching tabs

## Privacy boundary

Running Smart Fit does not automatically persist an analysis. A report is stored only after the user explicitly saves it.

Saved-report records do not include raw resume text or the full job description. They do include derived report information such as fit summaries, skill names, gaps, coaching actions, analysis metadata, and job identity fields.

## Production verification

The final smoke test covered:

1. signing in through the deployed application
2. uploading a resume and running Smart Fit against a searched job
3. switching across all application tabs and returning to preserved Smart Fit state
4. saving a searched job, refreshing, reopening it, and deleting it
5. saving a Smart Fit report, refreshing, reviewing it, and deleting it
6. signing out to confirm private information was hidden, then signing back in

## Explicitly deferred optional work

The following features are useful but are not required for Milestone 6 completion:

- saved searches or job alerts
- custom collections or folders
- saving a manually pasted job as a standalone Saved Job record

A report produced from a manually pasted job can already be saved.

## Status

```text
Milestones 1–6: Complete
Milestone 7: In progress
Milestone 8: Partially started
```
""",
    encoding="utf-8",
)

MILESTONE_7_PATH.write_text(
    """# Milestone 7 Plan — Better Job Source Coverage

## Objective

Improve MarketLens recall across industries without weakening precision or scraping closed job boards irresponsibly.

The current search system can normalize and filter configured Greenhouse, Lever, Remote OK, and Remotive results. Its main limitation is source coverage: a correct filter cannot return a relevant role that was never present in the searched providers.

## Phase 1 — Search intent model

Represent each search with independent dimensions:

- **job function** — marketing, software, finance, nursing, data, operations, and others
- **industry/domain** — sports, entertainment, healthcare, fintech, nonprofit, education, media, and others
- **experience level** — internship, entry, mid, senior, or unspecified
- **location** — city, state, remote, or unspecified

The model should preserve the expected relationship between broad and specific queries. For example, `marketing` can include sports marketing, while `sports marketing` must require sports-industry evidence.

## Phase 2 — Reusable industry taxonomy

Create a centralized taxonomy containing:

- canonical industry identifiers
- user query aliases
- strong organization/title phrases
- description evidence rules
- industry exclusions and ambiguity notes

This replaces one-off query logic with a design that can expand beyond sports.

## Phase 3 — Source registry

Create a configurable registry for public sources and organization boards. Each entry should record:

- provider type and identifier
- organization name
- likely industries and role families
- internship or entry-level relevance
- geographic focus
- enabled/disabled status
- coverage notes shown to users

## Phase 4 — Source expansion

Evaluate and add legitimate sources for:

- sports and entertainment
- healthcare
- finance and fintech
- education and universities
- nonprofits
- media and communications
- internship-heavy employers

Prefer official public ATS endpoints and documented public APIs. Do not scrape closed search-result pages.

## Phase 5 — Closed-source fallback workflow

For Workday, Handshake, LinkedIn, Indeed, school portals, and other closed sources:

- clearly state that MarketLens did not search them directly
- generate targeted fallback searches or links
- support an easy user-assisted paste/import path back into Smart Fit
- avoid claiming comprehensive coverage

## Phase 6 — Quality and evaluation

Add tests and evaluation cases for:

- function-only queries
- industry + function combinations
- internships and entry-level roles
- local versus remote intent
- recall across configured source groups
- precision against incidental industry mentions
- transparent low-coverage responses

## Initial acceptance criteria

- source selection is informed by function, industry, level, and location
- industry-specific queries do not fill with unrelated general jobs
- broad function searches remain broad
- materially more relevant organizations are searched for underrepresented industries
- source coverage and missing closed sources are explained honestly
- the design generalizes beyond sports without adding bespoke logic for every phrase

## Tracking

The source-expansion problem and acceptance criteria are also tracked in GitHub issue #21.
""",
    encoding="utf-8",
)
