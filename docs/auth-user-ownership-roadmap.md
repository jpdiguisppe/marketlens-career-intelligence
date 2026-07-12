# Auth and User Ownership Roadmap

This document describes the planned path from the current public demo model to a real multi-user MarketLens product.

## Current Demo Model

MarketLens currently uses one shared application database.

Public visitors can:

- view saved demo job postings
- view skill trend dashboards
- run resume gap analysis against the saved demo dataset
- extract skills from pasted non-sensitive text

Admin-only actions require the `X-Admin-API-Key` header:

- create a job posting
- import job postings from CSV
- delete saved job postings

This keeps the deployed demo useful while preventing anonymous users from modifying or deleting the shared demo data.

## Target Product Model

The long-term version should use real user accounts and per-user data ownership.

A logged-in user should be able to:

- import or paste their own job postings
- save their own career targets and role categories
- run resume gap analysis against their own saved postings
- delete only their own saved postings
- optionally keep resume-derived skill profiles without storing full resume text

A user should not be able to:

- see another user's saved postings
- edit another user's data
- delete another user's data
- access admin-only demo data controls

## Suggested Data Model

Possible future tables:

```text
users
- id
- email
- created_at

job_postings
- id
- user_id
- company
- title
- location
- role_category
- experience_level
- description
- extracted_skills_json
- created_at

resume_profiles
- id
- user_id
- label
- extracted_skills_json
- created_at
```

The `user_id` column becomes the ownership boundary for saved records.

## Backend Authorization Rule

Every saved-data query should be scoped to the logged-in user.

Example rule:

```text
Return job postings where job_postings.user_id = current_user.id
```

Avoid global queries such as:

```text
Return every job posting in the database
```

unless the endpoint is explicitly admin-only.

## Row Level Security Direction

PostgreSQL Row Level Security should be considered after authentication and ownership columns exist.

RLS is most useful once the database has:

- a `users` table
- user-owned rows
- reliable authentication
- a consistent way to map each API request to the current user

The application should still enforce authorization in backend code. RLS can provide an additional database-level safety layer.

## Implementation Phases

### Phase 1: Current Demo Safety

- Keep public demo read/analyze focused
- Protect create/import/delete with `ADMIN_API_KEY`
- Add input limits and basic rate limiting
- Warn users not to upload sensitive data

### Phase 2: Public Non-Persistent Custom Analysis

Allow users to paste their own job descriptions and resume-style text for analysis without saving anything to the shared database.

This gives real usefulness before full account support.

### Phase 3: Authentication

Add login/signup with a trusted auth provider or a simple backend auth system.

Required backend concepts:

- current user lookup
- protected routes
- session or token validation
- logout/session expiration behavior

### Phase 4: Per-User Saved Data

Add `user_id` ownership to saved job postings and any saved resume profile records.

Update endpoints so logged-in users can create/import/delete only their own data.

### Phase 5: Database-Level Ownership Hardening

Consider PostgreSQL RLS policies once user ownership is stable.

### Phase 6: Production Readiness

Before collecting real users or sensitive data, add:

- privacy policy
- terms of use
- stronger distributed rate limiting
- structured security logging
- dependency vulnerability scanning in CI
- accessibility audit
- backup and data deletion plan
