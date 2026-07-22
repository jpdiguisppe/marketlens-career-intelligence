# Milestone 7 — Broader Source Coverage, Tranche 1

This tranche adds three verified public Lever organization boards to close two of MarketLens' largest coverage gaps without exceeding the existing outbound-request safety budget.

## Added sources

- **The Athletic** (`lever:theathletic`) — sports, media, and entertainment
- **Feld Entertainment** (`lever:feldinc`) — sports, live entertainment, motorsports, media, and event operations
- **Stand Together** (`lever:standtogether`) — nonprofit, education, social impact, media, and early-career fellowship pathways

## Search behavior

The industry-aware router now has exact registered sources for sports and nonprofit searches:

- sports marketing and sports operations searches prioritize The Athletic and Feld Entertainment
- nonprofit marketing and operations searches prioritize Stand Together
- broad searches continue to retain the full configured registry

## Safety and performance

- all new identifiers are fixed registry entries and remain behind the provider allowlist
- no arbitrary URLs or user-supplied provider identifiers are introduced
- the total default ATS source count remains at least three requests below the default per-search provider budget, preserving request headroom for remote feeds
- existing HTTPS validation, redirect restrictions, caching, rate limits, and closed-board non-scraping behavior remain unchanged

## Deliberate scope

This is a focused first expansion rather than a large unverified company dump. Later tranches should add healthcare, education, media, nonprofit, and internship-heavy employers through verified public boards while protecting broad-search request budgets. A future secondary-source-pool design may allow more niche boards to participate only when their industries are requested.
