# Milestone 7 — Closed-Source Fallback UX

MarketLens searches only configured API-friendly public sources. LinkedIn, Indeed, Handshake, and Workday search pages are not scraped or represented as searched providers.

## User workflow

After every completed search, the Smart Fit screen now shows:

1. **What MarketLens actually searched** — provider-by-provider fetched and matched counts plus routing/coverage notes.
2. **Ways to widen or refine the search** — the backend's existing query and location suggestions.
3. **Continue externally** — pre-filled outbound links for Google Jobs, Indeed, LinkedIn, Workday/company career sites, and Handshake for internship or entry-level searches.
4. **Bring the posting back** — users can copy an external job description and paste it into manual Smart Fit for the same deterministic or model-assisted analysis.

## Responsible source boundary

- External links are navigation aids, not imported search results.
- MarketLens does not bypass logins, crawl result pages, or imply source coverage it does not have.
- The Workday option uses a Google site-restricted discovery query for indexed postings rather than scraping Workday tenant search pages.
- Handshake is included for both internship and entry-level searches because campus systems frequently cover new-graduate roles as well as internships.
- All outbound URLs remain HTTPS and pass through the frontend's safe external-link component.
