# Milestone 7 — Industry-Aware Source Routing

## Objective

Use the structured search intent and secure source registry to choose the most relevant public ATS boards before MarketLens makes provider requests.

## Routing behavior

- Broad searches without a detected industry keep the full configured Greenhouse and Lever registry.
- Industry-specific searches select a bounded set of exact-industry, adjacent-industry, and general fallback sources.
- Job function, experience level, and location influence ordering inside the routed set.
- At least a small Greenhouse and Lever fallback remains when each provider has configured sources.
- All selected identifiers still pass through the secure registry allowlist introduced in PR #28.

## Current examples

- `financial services marketing internship` prioritizes registered fintech and financial-services organizations while preserving marketing-capable fallbacks.
- `education software entry level` prioritizes Duolingo and Coursera.
- `sports marketing internship` currently uses entertainment and media adjacencies because the registry does not yet contain exact sports organizations. The coverage note states that limitation explicitly.
- `software engineer` remains broad and searches the full configured registry.

## Safety and performance

The routed source set is capped for industry-specific searches, reducing outbound fan-out and preserving the per-search request budget. Cached ATS responses, HTTPS-only provider endpoints, disabled automatic redirects, and application-link validation remain unchanged.

## Remaining work

Routing can only prioritize sources that exist in the registry. The next source-expansion phase must add verified public ATS boards for sports, healthcare, education, nonprofit, media, entertainment, finance, and internship-heavy employers, followed by recall and precision evaluation.
