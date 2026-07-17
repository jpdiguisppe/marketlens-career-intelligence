# Milestone 2 Smoke Test: Online Job Search + Smart Fit Comparison

This checklist verifies the online job-search workflow after the backend and frontend are deployed.

## Goal

Confirm that MarketLens can:

```text
Upload or paste a resume
Search public job boards
Filter by experience level
Select returned jobs
Compare selected jobs with Smart Fit
Show ranked fit results
```

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
- `results` contains general software engineering roles when matching configured boards have openings
- descriptions are readable plain text, not raw HTML

Internship search:

```bash
curl "https://marketlens-career-intelligence-production.up.railway.app/jobs/search?query=SWE&level=intern&limit=3"
```

Expected:

- `level` is `intern`
- results, if any, should be internship/co-op-looking roles
- a `result_count` of `0` is acceptable when the configured boards have no matching internships
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
3. Confirm job cards appear when the configured boards have matching jobs.
4. Select one or more jobs.
5. Click **Compare selected**.
6. Confirm Smart Fit returns ranked results with:
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
senior SWE + Any level
```

Expected behavior:

- `Any level` stays general-purpose.
- `Internship` only returns internship/co-op-looking roles or a clear no-results note.
- `SWE Intern` should infer internship intent even if the dropdown is `Any level`.
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

Search coverage is intentionally limited to the configured public Greenhouse boards for now. A no-results response means no matching jobs were found in those configured sources, not that no such jobs exist anywhere.

Manual pasted-job comparison remains available for jobs outside the configured search sources.
