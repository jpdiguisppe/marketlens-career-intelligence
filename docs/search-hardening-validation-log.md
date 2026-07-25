# Search Hardening Validation Log

This log records the validation work for Issue #39 and PR #40.

## Deterministic evaluation

The expanded offline benchmark passes with:

- 20 intent cases
- 273 candidate cases
- 17 location cases
- 20 ranking cases
- 9 routing cases
- 55 critical cases
- 100% intent accuracy
- 100% candidate accuracy, precision, and recall
- 100% negative rejection
- 100% location accuracy
- 100% ranking accuracy
- 100% routing accuracy
- 100% critical-case pass rate

## Focused test matrix

The focused role, location, ranking, routing, and source-expansion matrix passes 85 tests. It includes the original `Electrical Engineer` / `Entry level` / `Philadelphia` regression and representative searches across all required sectors.

## Hosted-suite regressions found and fixed

The first complete hosted backend run caught two recall regressions outside the focused matrix:

1. `Technology Rotational Program` was rejected for `software engineer entry level` even when the description explicitly rotated through software-engineering and backend teams.
2. `Analytics Engineer` was rejected as a recognized data-family neighbor for `data analyst`.

The fixes preserve the stricter contract:

- generic early-career program titles are accepted only when the tuned family matcher finds explicit requested-role evidence in the description;
- unrelated business rotational programs remain rejected;
- Analytics Engineer remains eligible for a Data Analyst search, while exact Data Analyst titles retain the larger occupation/query score and rank first;
- unrelated analysts remain rejected.

The targeted regressions and the complete deterministic benchmark pass after the fix.

## Remaining gates

Before Issue #39 is closed, PR #40 must still complete the final authoritative pass:

- complete hosted backend suite;
- frontend production build;
- backend and frontend Docker builds;
- live public-provider smoke tests;
- final review of source reporting, role relevance, level relevance, strict metro/location behavior, and ranking.
