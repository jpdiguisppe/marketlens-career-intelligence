# Milestone 7 — Secondary Industry-Only Source Pool

## Objective

Allow MarketLens to keep adding specialized public ATS boards without forcing every broad search to request every niche source.

## Source pools

- **Primary** sources participate in broad searches and remain available to industry-aware routing.
- **Industry-only** sources stay inactive for broad searches and activate only when the detected industry exactly matches their registry metadata.

The Athletic, Feld Entertainment, and Stand Together now live in the industry-only pool. This preserves their value for sports, nonprofit, and education searches while removing three requests from uncached broad searches.

## Routing behavior

- `software engineer` searches only the primary pool.
- `sports marketing internship` activates The Athletic and Feld Entertainment.
- `nonprofit marketing internship` activates Stand Together.
- `education software entry level` activates Stand Together alongside the primary education sources.
- unrelated searches such as financial-services roles do not activate any of those niche boards.

Industry-specific searches still retain the existing capped routed set and provider fallbacks.

## Configuration and safety

The registry allowlist enforces each entry's pool assignment. A configured primary-source list cannot move an industry-only source into broad searches, and arbitrary or malformed provider identifiers remain rejected.

The existing request budget, caching, HTTPS validation, disabled redirects, rate limiting, and closed-board non-scraping behavior remain unchanged.

## Scope boundary

This phase adds the source-pool architecture only. It does not add legal taxonomy, new legal sources, credential filtering, or broader early-career matching. Those remain later steps in the agreed Milestone 7 sequence.
