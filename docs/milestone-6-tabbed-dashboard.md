# Milestone 6 — Tabbed Dashboard

The MarketLens frontend is organized into four focused sections instead of one long page:

- **Smart Fit** — resume upload, online job search, manual job input, ranking, and report saving
- **Saved Jobs** — private bookmarked postings
- **Saved Reports** — private Smart Fit history
- **Market Data** — sample dataset summary, skill trends, and sample comparison

## Behavior rules

- Switching sections does not unmount Smart Fit, so uploaded resume text, searched jobs, selections, and current analysis remain available.
- Saved jobs and saved reports retain their existing Clerk-backed private ownership and deletion behavior.
- Market-data API loading remains independent from public Smart Fit analysis.
- The layout collapses to two tab columns on tablets and one column on narrow mobile screens.

## Smoke test

1. Open Smart Fit and upload or paste a resume.
2. Search for jobs, select one, and run Smart Fit.
3. Switch to Saved Jobs and back to Smart Fit; confirm the current analysis is still visible.
4. Save the report, open Saved Reports, and confirm it appears.
5. Open Market Data and verify the sample cards, charts, and postings table render.
6. Resize to a narrow viewport and confirm the tab controls stack cleanly.
