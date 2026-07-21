# Milestone 6: Private Saved Smart Fit Reports

Authenticated users can save Smart Fit report summaries to their private MarketLens workspace.

## What is stored

- job identity and optional posting link
- fit score, band, confidence, and headline
- coach summary
- category coverage
- strong matches and important gaps
- prioritized coaching actions
- analysis engine/status metadata

## What is not stored

The saved-report API does not accept or persist raw resume text or the full job description. Saving is explicit; running Smart Fit does not automatically create a private report.

## Ownership rules

Every create, list, read, and delete operation uses the verified authenticated user ID. A report owned by another user returns `404` rather than exposing whether it exists.

## Smoke test

1. Sign in.
2. Search for or paste a job description.
3. Run Smart Fit.
4. Select a ranked report and click **Save Smart Fit report**.
5. Confirm it appears under **Your saved Smart Fit reports**.
6. Refresh the page and confirm the report remains.
7. Open the saved report and review the summary, matches, gaps, and coaching actions.
8. Delete the report and confirm it disappears.
9. Sign out and confirm private saved reports are no longer visible.
