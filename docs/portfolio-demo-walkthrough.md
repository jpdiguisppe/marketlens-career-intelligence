# MarketLens Portfolio Demo Walkthrough

These are the steps I use to show MarketLens in a demo or technical interview. The first three examples cover the main features. The last one shows how the app handles failures and restricted actions.

## What MarketLens does

MarketLens searches supported public job sources and compares them with a resume. It shows why jobs rank where they do, which requirements have supporting evidence, and which gaps someone may need to address. Signed-in users can also build and review a private career plan.

Career Plans runs a seven-step workflow using the existing search and Smart Fit features. Job scores and evidence come from the app's analysis rules. An optional AI step can organize the plan, but the user makes the final decision.

## Live demo links

- Frontend: https://marketlens-career-intelligence-production-8a34.up.railway.app
- Backend health: https://marketlens-career-intelligence-production.up.railway.app/health
- Deployment revision: https://marketlens-career-intelligence-production.up.railway.app/deployment/status

Use only non-sensitive or synthetic resume information during a demo.

## Demo path 1: Career Planning Agent

Use this example to demonstrate the saved Career Plans workflow.

1. Sign in through Clerk.
2. Open **Career Plans**.
3. Enter a target role such as `Software Engineer` or `Data Analyst`.
4. Choose an experience level, location, work mode, portfolio strategy, and a one-to-five-job analysis bound.
5. Upload or paste a non-sensitive resume.
6. Choose deterministic-only planning or optional bounded AI organization.
7. Create and execute the run.
8. Watch the seven persisted workflow steps update.
9. Open the Candidate Selection Audit and show:
   - provider coverage
   - every considered candidate
   - selected candidates
   - excluded candidates
   - search rank
   - deterministic exclusion reason codes
10. Review the opportunity portfolio, recurring strengths, recurring gaps, limitations, and proposed actions.
11. Ask why one job, gap, or action was recommended.
12. Explain the difference between deterministic results and optional AI organization.
13. Edit one proposed action and approve or reject the plan.
14. Reopen it from private history.
15. Delete the synthetic demo plan.

What to point out:

- Search and Smart Fit are actual tools; their logic is not copied into the model prompt.
- The workflow survives model failure because the deterministic plan is complete first.
- Raw resume text and full job descriptions are not persisted in Career Plan records.
- Every recommendation references saved derived evidence or explicit user preferences.
- The model cannot change scores, evidence, hard requirements, job selection, action types, or approval state.
- Approval does not apply to a job or contact anyone; it records the user’s decision about the plan.
- The run remains private and resumable across page refreshes.

## Demo path 2: Online search and ranked Smart Fit

1. Open **Job Intelligence**.
2. Upload or paste a non-sensitive resume.
3. Search a role such as `Data Analyst`, `Software Engineer`, or `Mechanical Engineer`.
4. Choose an experience level and optional location.
5. Review provider coverage and bounded job cards.
6. Select two or three jobs.
7. Run Smart Fit comparison.
8. Review the ranked jobs and open the ranking explanation.
9. Inspect requirement coverage, direct evidence, related evidence, gaps, hard requirements, and coaching actions.

What to point out:

- The same resume is evaluated against every selected job.
- Occupation, experience level, industry, and location are evaluated separately.
- The ranking explanation identifies why one job scored above another.
- Missing capabilities are not treated as proof that the user cannot learn or qualify later.
- Public-source coverage is shown honestly instead of implying complete internet coverage.

## Demo path 3: Manual pasted-job comparison

Use this when a posting comes from a closed or unsupported platform.

1. Paste or upload a resume.
2. Paste two or more job descriptions.
3. Separate them with `---`.
4. Run Smart Fit.
5. Review rankings and detailed reports.
6. Optionally save a reduced report summary when signed in.

This path demonstrates that MarketLens remains useful without scraping LinkedIn, Indeed, Handshake, Workday search pages, or school portals.

## Demo path 4: Failure and safety behavior

If someone asks how the app handles failure, these examples are useful:

Useful examples:

- Run deterministic-only planning and show that no provider is required.
- Enable optional AI and point out whether it was used or fell back.
- Cancel an active Career Plan and retry it.
- Open an excluded candidate and explain `duplicate_posting` or `outside_analysis_limit`.
- Show that signed-out access to `/career-plans` is rejected.
- Explain that malicious text inside a job title, description, company field, or link is treated as data.

The permanent evaluation suite includes instructions attempting to auto-apply, contact recruiters, expose secrets, invent qualifications, alter scores, bypass approval, and purchase services. Those attempts cannot add tools, actions, evidence, or approval decisions.

## Technical architecture summary

MarketLens uses:

- React + TypeScript + Vite
- FastAPI + Pydantic
- SQLAlchemy persistence
- SQLite locally and PostgreSQL in production
- Clerk authentication
- public Greenhouse, Lever, SmartRecruiters, Remote OK, and Remotive integrations
- deterministic Smart Fit analysis
- optional strict-schema model assistance
- durable Career Plan runs, steps, attempts, decisions, and audit events
- Dockerized frontend and backend services
- Railway deployment
- GitHub Actions CI, adversarial evaluation, provider-resilience, telemetry, secret-safety, and production-canary workflows

## Security and privacy posture

MarketLens is a portfolio product, not a service for highly sensitive information.

Current controls include:

- backend verification of Clerk session tokens
- user-owned private records with cross-user `404` behavior
- request-time resume processing
- raw resume and complete job-description exclusion from saved Career Plans and saved reports
- backend-only provider credentials
- strict schema and reference validation for model output
- sensitive-log context and secret scanning
- bounded job counts, actions, provider calls, context size, tokens, latency, and estimated cost
- explicit human approval
- deterministic fallback

## Architecture in brief

I built MarketLens around two existing pieces: public job search and Smart Fit comparison. Career Plans brings them together and saves each workflow step so users can return to their plan or retry a failed run. The plan is calculated first using application rules. AI is optional and cannot change the scores, requirements, or approval status. The project also includes tests for privacy, prompt injection, failed providers, cancellation, and production deployment.

## Short project description for a resume

```text
Built MarketLens, a job search and resume comparison app using React, FastAPI, and PostgreSQL. Added private career plans, a seven-step planning workflow, optional AI assistance, and automated tests for privacy and system reliability.
```

## Production evidence rule

Do not claim the final Milestone 8.1 launch is complete until:

- both Railway services report the exact intended revision
- the public production canary passes
- the full authenticated Career Plan lifecycle is exercised
- cancellation/retry is observed in production or explicitly recorded as a manual timing limitation
- model latency, token use, and estimated cost are recorded when the model is configured
- signed-in screenshots are captured from the exact deployed revision
- `docs/milestone-8-1-completion.md` records a final GO decision
