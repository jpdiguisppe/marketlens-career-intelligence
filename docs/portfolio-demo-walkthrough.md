# MarketLens Portfolio Demo Walkthrough

This walkthrough is designed for a quick portfolio, recruiter, or interview demo. It shows the core value of MarketLens without requiring anyone to understand the entire codebase first.

## One-minute project pitch

MarketLens is a full-stack career intelligence app that compares resume evidence against real job descriptions. It helps a user search public job sources, select jobs, rank role fit, and understand which resume-backed skills and missing capabilities explain the ranking.

Instead of only saying "you match Python" or "you are missing AWS," MarketLens explains fit in context: whether the role is software, data, cybersecurity, finance, product, healthcare, operations, or admin-oriented, what the resume actually proves, and which gaps matter most for that role.

## Live demo links

- Frontend: https://marketlens-career-intelligence-production-8a34.up.railway.app
- Backend docs: https://marketlens-career-intelligence-production.up.railway.app/docs
- Backend health: https://marketlens-career-intelligence-production.up.railway.app/health

## Demo path 1: Online job search + role-aware comparison

Use this path to show the main product workflow.

1. Open the frontend demo.
2. Upload or paste a non-sensitive resume.
3. Search a role such as `Data Analyst`, `Computer Science`, or `SWE`.
4. Optionally choose a level such as Internship, Entry, Mid, or Senior.
5. Optionally enter a location such as Philadelphia, PA, Remote, or blank for broad U.S. matching.
6. Review the returned job cards and source notes.
7. Select two or three jobs.
8. Click Compare selected.
9. Review the ranked jobs.
10. Open Why this ranking? and explain how MarketLens compares score gap, direct resume proof, role-aware context, and runner-up gaps.
11. Click Show details on each ranked job to inspect the full Smart Fit report.

What to point out:

- MarketLens ranks selected jobs against the same resume, rather than analyzing each job in isolation.
- The ranking explanation shows why one role scored above another.
- Resume evidence is separated into direct proof and general resume signal.
- Role-specific gaps are shown even when the missing capability is broader than a single tool name.
- High-priority coaching actions appear before lower-priority polish items.

## Demo path 2: Manual pasted-job comparison

Use this path when online sources are thin or when demonstrating that MarketLens can analyze jobs copied from outside sources such as LinkedIn, Indeed, Handshake, Workday-backed career pages, or company sites.

1. Paste or upload a non-sensitive resume.
2. Paste two or more job descriptions into the manual job-description box.
3. Separate the job descriptions with `---`.
4. Run the Smart Fit comparison.
5. Review the ranked jobs and detailed reports.

What to point out:

- MarketLens does not need to scrape closed job boards to be useful.
- Users can paste any job posting they are considering.
- Manual comparison keeps the app useful even when public API-friendly job sources do not cover a role category well.

## Demo path 3: Conservative fallback behavior

Use this path to show that MarketLens handles non-pure-technical jobs without pretending to have exact evidence.

Example pasted job:

```text
Product Manager

Required Qualifications
Own product strategy, roadmap planning, backlog prioritization, and product requirements.
Lead user research, customer research, discovery interviews, and stakeholder interviews.
```

Expected behavior:

- MarketLens should not crash just because the posting lacks exact technical tool requirements.
- It should produce conservative role-context guidance.
- It should explain that the posting did not expose enough exact skill/tool requirements for a full evidence-backed score.
- It should still identify product capability gaps such as product strategy, roadmap ownership, user research, or requirements discovery when supported by the posting.

## Technical architecture summary

MarketLens uses:

- React + TypeScript frontend
- FastAPI backend
- SQLAlchemy database layer
- SQLite locally and PostgreSQL in deployment
- Railway deployment
- GitHub Actions CI
- pytest backend tests
- frontend production build validation
- public API-friendly job sources instead of scraping closed job boards

## Security and privacy posture

MarketLens is currently a portfolio/demo app, not a production service for sensitive personal information.

Current privacy posture:

- Resume uploads are processed for the current request and are not saved to the shared database.
- Public users can run analyses without creating saved private records.
- Admin-only write/delete actions require an API key.
- Model-assisted extraction is disabled unless configured through backend-only environment variables.
- Users are warned not to upload sensitive personal data, secrets, API keys, or confidential employer/customer data.

Future account and saved-report features should require a stronger private-data foundation before storing user-specific career data.

## Suggested interview explanation

"I built MarketLens because career advice is usually too vague. A student might hear 'learn cloud' or 'build AI projects,' but that does not tell them which jobs actually fit their current resume or what proof is missing. MarketLens turns job descriptions into a structured comparison: it searches public job sources, compares selected jobs against a resume, ranks them, and explains the ranking using evidence, role context, and missing capabilities."

## Suggested resume bullet

Built and deployed MarketLens, a full-stack career intelligence app using React, TypeScript, FastAPI, SQLAlchemy, PostgreSQL, and Railway to compare resumes against job postings, rank role fit, and surface role-aware skill gaps with tested backend analysis workflows.
