# Milestone 7 Plan — Better Job Source Coverage

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
