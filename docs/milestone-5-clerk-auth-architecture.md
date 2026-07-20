# Milestone 5 — Clerk Auth Architecture Decision

MarketLens will use Clerk as the first authentication provider for Milestone 5.

This decision keeps the current deployment and database setup mostly intact while still giving the app a real account foundation for private saved jobs, saved reports, and future dashboards.

## Decision

```text
Clerk for authentication
FastAPI for backend identity verification and authorization
Railway Postgres for the existing application database
SQLAlchemy for user-owned tables and queries
Postgres RLS documented as a later hardening option
```

MarketLens uses Clerk for authentication and enforces user-owned data access in the FastAPI backend, with tests proving cross-user access is blocked. Database-level RLS is documented as a future hardening option.

## Why Clerk first

Clerk is the right first choice for this project because it lets MarketLens add real login/session behavior without moving away from the existing React, FastAPI, Railway, Railway Postgres, and SQLAlchemy architecture.

The goal of this milestone is not to rebuild the whole infrastructure. The goal is to safely introduce identity, ownership, and private data boundaries before adding saved jobs and saved reports.

## Target architecture

```text
React frontend
↓
Clerk login/logout and session state
↓
Frontend sends Clerk session token to FastAPI
↓
FastAPI verifies token using Clerk configuration
↓
FastAPI resolves or creates an internal MarketLens user
↓
Private routes read/write only rows owned by that user
↓
Railway Postgres stores user-owned records with owner_user_id
```

## User ownership model

Every private table must include an owner field.

Examples:

```text
saved_jobs.owner_user_id
saved_reports.owner_user_id
saved_searches.owner_user_id
saved_resumes_optional.owner_user_id
```

The frontend must never send a trusted `owner_user_id`. The backend should derive ownership only from the verified Clerk token.

## Authorization rule

All private routes must follow this pattern:

```text
Verify Clerk token
Resolve current MarketLens user
Query by both object ID and owner_user_id
Return 404 or 403 if the object does not belong to the current user
```

Example:

```text
Correct:
SELECT saved job WHERE id = requested_id AND owner_user_id = current_user.id

Wrong:
SELECT saved job WHERE id = requested_id
Then trust the frontend to hide other users' data
```

## Public vs private behavior

Public behavior should remain available without login:

```text
search public configured job sources
paste a resume
upload a resume for one-time extraction
run Smart Fit analysis
compare selected jobs
view demo dataset/dashboard
```

Private behavior should require login:

```text
save a job
save a report
view private dashboard
delete saved jobs
delete saved reports
manage saved searches
```

## Privacy rules

Milestone 5 should not quietly start saving sensitive data.

Rules:

```text
Analyze without saving remains the default.
Saving requires a clear user action.
Raw resume text is not saved by default.
Saved reports should store summarized output, not full input documents.
Users must be able to delete their saved objects.
Auth tokens, resume text, provider keys, and database URLs must not be logged.
```

## RLS position

Clerk alone does not automatically provide Supabase-style Row Level Security.

For Milestone 5A, MarketLens will enforce user-owned access in FastAPI and prove that behavior with tests.

For later hardening, MarketLens can evaluate Postgres RLS by passing verified user identity into the database/session layer and adding database policies. This is a future hardening option, not a blocker for the first Clerk implementation.

## Milestone 5A implementation plan

```text
1. Add Clerk frontend configuration.
2. Add login/logout UI.
3. Add backend Clerk token verification configuration.
4. Add current-user dependency in FastAPI.
5. Add /me endpoint for authenticated users.
6. Add internal users table mapping Clerk subject to MarketLens user ID.
7. Add first user-owned table, likely saved_jobs.
8. Add saved job CRUD routes.
9. Add tests for unauthenticated access rejection.
10. Add tests proving User A cannot access User B's saved jobs.
```

## Milestone 5B implementation plan

After saved jobs are stable:

```text
1. Add saved_reports table.
2. Save Smart Fit report summaries only when the user explicitly clicks save.
3. Avoid raw resume storage by default.
4. Add report delete controls.
5. Add cross-user saved report tests.
6. Add private dashboard UI.
```

## Done criteria

This architecture is successfully implemented when:

```text
Clerk login/logout works in the frontend.
FastAPI verifies Clerk tokens.
/me returns the authenticated MarketLens user.
Private routes require login.
Private database rows have owner_user_id.
Backend tests prove cross-user access is blocked.
Public analysis still works without login.
README and SECURITY docs explain the privacy model honestly.
```
