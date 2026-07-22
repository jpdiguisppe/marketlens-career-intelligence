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
