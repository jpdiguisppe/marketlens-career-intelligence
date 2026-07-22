# Milestone 7 — Source Registry

MarketLens now has a centralized registry for its configured public Greenhouse and Lever organization boards.

## Registry fields

Each source records:

- provider type and ATS identifier
- display organization name
- likely industries
- likely job-function families
- early-career relevance
- geographic focus
- enabled status
- an honest coverage note

## Current behavior

The existing default Greenhouse and Lever token lists now come from the registry, preserving the exact search order and current source behavior. Company display names also resolve through the same registry, with a safe title-cased fallback for environment-configured sources that are not registered yet.

This phase does **not** route searches differently yet. It establishes the structured configuration needed for the next phase: choosing source groups based on job function, industry, experience level, and location.

## Why this matters

Before this change, provider tokens and company-name formatting were hardcoded inside the search implementation. Expanding coverage would have required adding more one-off constants. The registry makes future source expansion reviewable, testable, and explainable without coupling every organization to the provider-fetching code.


## Security hardening

The registry now acts as an outbound allowlist rather than a display-only catalog.
Environment configuration can select only enabled, registered Greenhouse and Lever identifiers; malformed or unknown identifiers fail closed to the safe defaults.

Additional controls in this phase:

- provider identifiers use a strict lowercase token format
- application links must be public HTTPS URLs without embedded credentials
- unsafe links are rejected by the backend and independently hidden by the frontend
- provider HTTP clients do not automatically follow redirects
- ATS responses are cached briefly to avoid repeated network fan-out
- every search has a bounded outbound provider-request budget
- the public endpoint has both per-client and service-wide in-memory rate limits with bounded tracking state

These controls protect the portfolio-scale deployment. Large multi-instance deployments should add an edge or shared-store rate limiter because in-memory limits are instance-local.
