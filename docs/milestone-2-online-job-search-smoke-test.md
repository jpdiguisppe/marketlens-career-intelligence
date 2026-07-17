# Milestone 2 Smoke Test: Online Job Search + Smart Fit Comparison

This checklist verifies the online job-search workflow after the backend and frontend are deployed.

## Goal

Confirm that MarketLens can:

```text
Upload or paste a resume
Search configured public job sources
Filter by experience level
Filter by location when useful
Select returned jobs
Compare selected jobs with Smart Fit
Show ranked fit results
```

## Source coverage

Milestone 2 searches public job APIs instead of scraping closed job boards.

Current source types:

```text
Greenhouse Job Board API
Lever Postings API
Remote OK public JSON feed
```

Default configured sources are intentionally editable through backend environment variables:

```text
JOB_SEARCH_GREENHOUSE_BOARDS=<comma-separated board tokens>
JOB_SEARCH_LEVER_SITES=<comma-separated site tokens>
JOB_SEARCH_REMOTEOK_ENABLED=true
```

Remote OK is used as a broad remote-job source. MarketLens keeps the provider source on each job card and links users back to the original posting URL.

A no-results response means no matching jobs were found in the currently configured sources, not that no such jobs exist anywhere.

## Backend API checks

Run from anywhere:

```bash
curl "https://marketlens-career-intelligence-production.up.railway.app/health"
```

Expected:

```json
{"status":"ok"}
```

General SWE search:

```bash
curl "https://marketlens-career-intelligence-production.up.railway.app/jobs/search?query=SWE&level=any&limit=3"
```

Expected:

- `level` is `any`
- response includes `providers_searched`
- `providers_searched` can include `greenhouse:*`, `lever:*`, and `remoteok`
- `results` contains general software engineering roles when matching configured sources have openings
- descriptions are readable plain text, not raw HTML

Remote SWE search:

```bash
curl "https://marketlens-career-intelligence-production.up.railway.app/jobs/search?query=SWE&level=any&location=Remote&limit=3"
```

Expected:

- returned roles, if any, should be remote-looking roles
- obvious country-specific non-U.S. remote locations such as `Remote, Brazil` should not appear
- Remote OK results may appear when they match the query and level filters

U.S. city search:

```bash
curl "https://marketlens-career-intelligence-production.up.railway.app/jobs/search?query=SWE&level=any&location=Philadelphia&limit=3"
```

Expected:

- exact Philadelphia/Philly matches may appear when available
- U.S.-remote or broad remote roles may also appear as a fallback because many software jobs are labeled remote instead of listing every eligible city
- Pittsburgh should not appear for `Philadelphia`; use `PA` or `Pennsylvania` for state-wide results
- obvious non-U.S. remote roles should not appear

Pennsylvania mid-level search:

```bash
curl "https://marketlens-career-intelligence-production.up.railway.app/jobs/search?query=SWE&level=mid&location=PA&limit=3"
```

Expected:

- mid-level roles such as Software Engineer II/III may appear
- Pittsburgh, Philadelphia, PA-wide, and remote roles are acceptable
- senior/staff/principal roles should not appear for `level=mid`

Internship search:

```bash
curl "https://marketlens-career-intelligence-production.up.railway.app/jobs/search?query=SWE&level=intern&limit=3"
```

Expected:

- `level` is `intern`
- results, if any, should be internship/co-op-looking roles
- a `result_count` of `0` is acceptable when the configured sources have no matching internships
- Software Engineer II, Principal, Staff, or Senior roles should not appear for `level=intern`

Typed internship search:

```bash
curl "https://marketlens-career-intelligence-production.up.railway.app/jobs/search?query=SWE%20Intern&limit=3"
```

Expected:

- query-level inference treats `SWE Intern` as an internship search
- no fake intern matches caused by words like `internal` or `internally`

Senior search:

```bash
curl "https://marketlens-career-intelligence-production.up.railway.app/jobs/search?query=senior%20SWE&limit=3"
```

Expected:

- `level` is `senior`
- senior, staff, principal, lead, or high-years roles may appear

## Frontend checks

Open the live frontend:

```text
https://marketlens-career-intelligence-production-8a34.up.railway.app
```

1. Upload or paste resume text in the main Smart Fit panel.
2. In **Online job search**, search `SWE` with **Any level**.
3. Try `Remote`, `Philadelphia`, and `PA` as locations.
4. Confirm job cards appear when the configured sources have matching jobs.
5. Select one or more jobs.
6. Click **Compare selected**.
7. Confirm Smart Fit returns ranked results with:
   - job fit ranking
   - top matches
   - top gaps
   - detailed Smart Fit report switching

## Level filter checks in the UI

Search these combinations:

```text
SWE + Any level
SWE + Internship
SWE Intern + Any level
entry level SWE + Any level
SWE + Mid level + PA
senior SWE + Any level
```

Expected behavior:

- `Any level` stays general-purpose.
- `Internship` only returns internship/co-op-looking roles or a clear no-results note.
- `SWE Intern` should infer internship intent even if the dropdown is `Any level`.
- `Mid level` may include Engineer II/III roles, but should not include entry-level or senior/staff/principal roles.
- `senior SWE` should infer senior intent.

## Local development check

Run backend and frontend in two terminals.

Backend:

```bash
cd ~/Desktop/marketlens-career-intelligence/backend
source .venv/bin/activate
python -m uvicorn app.main:app --reload
```

Frontend:

```bash
cd ~/Desktop/marketlens-career-intelligence/frontend
npm run dev
```

Open:

```text
http://localhost:5173
```

Expected:

- local frontend reaches `http://127.0.0.1:8000`
- no `Failed to fetch` errors after backend is running

## Known limitation

Search coverage is broader than the first Milestone 2 pass, but it is still limited to configured public Greenhouse, Lever, and Remote OK sources. Manual pasted-job comparison remains available for jobs outside those sources.
