# Milestone 5 — Auth + Private Data Foundation

Milestone 5 prepares MarketLens for accounts, saved jobs, saved reports, and user dashboards without turning the demo into a privacy risk.

The main rule for this milestone is simple:

```text
Do not save personal career data until authentication, user ownership, and deletion controls are designed and tested.
```

## Goal

Add a private-data foundation so future users can safely save jobs, reports, searches, and optional resume snapshots.

This milestone is about security architecture first, product features second. Saved reports should not be built on top of anonymous shared database rows.

## Non-goals

This milestone should not immediately add:

- saved report history
- saved resumes
- job alerts
- AI-assisted analysis
- password storage implemented directly by MarketLens
- broad third-party job aggregation changes

Those belong after the auth/private-data foundation is stable.

## Privacy principles

MarketLens should follow these principles before it stores user-owned data:

1. **Analyze without saving by default.** Users should still be able to run Smart Fit without creating an account or saving raw resume text.
2. **Save only on explicit action.** Saving a job, report, search, or resume should require a clear user action.
3. **Minimize saved resume data.** Raw resume text should not be saved by default. If resume saving is added later, it should be opt-in and deletable.
4. **Every private row has an owner.** Any saved job, report, search, or resume snapshot must include a `user_id`/owner identifier.
5. **Server-side authorization only.** The backend must verify ownership. The frontend must never be trusted to enforce privacy.
6. **Delete controls are required.** Users must be able to delete saved jobs/reports/searches before the feature is considered complete.
7. **No secrets or personal text in logs.** Resume text, provider tokens, database URLs, and auth tokens must not be logged.
8. **Admin demo data stays separate.** Shared demo postings should remain separate from user-owned private data.

## Recommended architecture

Use an external auth provider instead of building password authentication directly inside MarketLens.

Target flow:

```text
Frontend login
↓
Auth provider issues signed token
↓
Frontend sends token to FastAPI
↓
FastAPI verifies token
↓
FastAPI maps token subject to a MarketLens user record
↓
Backend reads/writes only rows owned by that user
```

The backend should expose public demo endpoints and private user endpoints separately.

Example distinction:

```text
Public/demo endpoints:
GET /postings
GET /skills/top
POST /analysis/smart
POST /analysis/smart/batch

Private endpoints:
GET /me
GET /me/saved-jobs
POST /me/saved-jobs
DELETE /me/saved-jobs/{id}
GET /me/saved-reports
POST /me/saved-reports
DELETE /me/saved-reports/{id}
```

## Data model direction

Future user-owned tables should be designed around ownership and deletion.

Possible tables:

```text
users
saved_jobs
saved_reports
saved_searches
saved_resumes_optional
```

### `users`

Purpose: Map external auth identity to an internal MarketLens user.

Possible fields:

```text
id
external_auth_subject
email_hash or email_optional
created_at
updated_at
```

Avoid storing unnecessary profile data.

### `saved_jobs`

Purpose: Let users bookmark jobs they want to revisit.

Possible fields:

```text
id
user_id
title
company
location
source
apply_url
source_job_id_optional
job_description_snapshot_optional
created_at
updated_at
```

The job description snapshot should be considered optional because job descriptions can be long and may contain third-party content. A saved URL plus lightweight metadata may be enough for v1.

### `saved_reports`

Purpose: Save Smart Fit results without necessarily saving raw resume text.

Possible fields:

```text
id
user_id
saved_job_id_optional
job_title
company_optional
fit_score
fit_band
confidence
top_evidence_json
top_gaps_json
coaching_actions_json
limitations_json
resume_snapshot_label_optional
created_at
updated_at
```

Avoid storing raw resume text by default. Store the report output summary, not the full input documents, unless the user explicitly opts in later.

### `saved_searches`

Purpose: Let users rerun or revisit job searches.

Possible fields:

```text
id
user_id
query
level
location
created_at
updated_at
```

Alerts/notifications should not be added until saved searches are stable.

### `saved_resumes_optional`

Purpose: Optional future feature only.

Possible fields:

```text
id
user_id
label
extracted_text_encrypted_or_not_saved
skills_summary_json
created_at
updated_at
```

This should not be part of the first saved-data release unless there is a clear user benefit and a clear deletion story.

## Backend implementation checklist

Before Milestone 6 starts, the backend should have:

- auth configuration loaded from environment variables only
- current-user dependency for protected routes
- user lookup/create logic based on verified external auth subject
- user-owned database models
- private CRUD routes for saved jobs and saved reports
- authorization checks on every private route
- tests proving User A cannot access User B data
- tests proving unauthenticated users cannot call private routes
- tests proving public analysis still works without login
- no raw auth tokens, resume text, or secrets in logs

## Frontend implementation checklist

Before Milestone 6 starts, the frontend should have:

- login/logout UI
- clear signed-in user state
- private dashboard entry point only when signed in
- save buttons hidden or disabled when signed out
- messaging that analysis can still run without saving
- delete actions for saved private objects
- no auth secrets in frontend environment variables

## Security test cases

Minimum tests for the private-data foundation:

```text
Unauthenticated user cannot list saved jobs.
Unauthenticated user cannot create saved jobs.
Authenticated user can create and list their saved jobs.
Authenticated user cannot fetch another user's saved job by ID.
Authenticated user cannot delete another user's saved job by ID.
Authenticated user can delete their own saved job.
Public Smart Fit analysis still works without authentication.
Admin demo-posting protections still work.
```

For saved reports:

```text
Authenticated user can save a report summary.
Authenticated user can list their own saved reports.
Authenticated user cannot fetch another user's report.
Authenticated user cannot delete another user's report.
Saved report payload does not require raw resume text.
```

## Product behavior rules

The UI should make saving explicit:

```text
Analyze now
Save this job
Save this report
Delete saved report
```

Avoid vague behavior such as automatically saving everything after analysis.

If the user is not signed in:

```text
You can still run Smart Fit without saving. Sign in to save jobs and reports.
```

If the user is signed in:

```text
Save this report to your private dashboard.
```

## Deployment/environment checklist

Before enabling accounts in the deployed app:

- backend auth issuer/audience/client settings configured only in Railway backend variables
- frontend public auth client settings configured only as safe public values
- CORS still restricted to the deployed frontend origin
- database migrations applied cleanly
- no local-only auth shortcuts enabled in production
- test account created for demo validation
- README and SECURITY.md updated with the new privacy model

## Milestone 5 completion criteria

Milestone 5 is complete when:

- MarketLens has an auth/private-data design implemented in code
- protected backend routes require verified identity
- user-owned tables exist for the first saved-data objects
- cross-user access tests pass
- public demo analysis still works without login
- no raw resume saving is introduced by default
- README/SECURITY docs explain the privacy model

## Next milestone after this

After Milestone 5, Milestone 6 should add the user-facing saved-data product features:

```text
Saved jobs
Saved Smart Fit reports
Private dashboard
Delete controls
Maybe saved searches
```

Better job source coverage and optional AI-assisted analysis should come after the private-data foundation is stable.
