# Milestone 8.1G — Universal occupation search foundation

## Purpose

This increment replaces title-by-title search patching with a deterministic cross-sector occupation layer.

## Canonical sources

- U.S. Bureau of Labor Statistics 2018 Standard Occupational Classification major groups
- O*NET occupation and job-title datasets as the design model for canonical and alternate titles

MarketLens packages a compact reviewed index rather than downloading O*NET data during a user request. This keeps interpretation deterministic, private, fast, and resilient to upstream downtime.

## Shipped foundation

- all 23 SOC major groups represented
- 214 occupation concepts
- 454 accepted canonical and alternate titles
- 33 ambiguous acronym clarification cases
- high-confidence spelling correction
- generic recognition for descriptive occupations not yet listed verbatim
- strict title-level matching so specific searches do not degrade into broad family noise
- canonical and alternate provider search terms
- expanded cross-sector SmartRecruiters routing terms
- USAJOBS, public-sector, and Apprenticeship.gov fallback discovery where relevant
- explicit distinction between ambiguous/unrecognized abbreviations and understood occupations with limited current coverage

## Immediate SAE regression

Bare `SAE` is treated as ambiguous and providers are not queried until the user chooses a meaning. The following full variants resolve to the same occupation concept:

- System Application Engineer
- Systems Application Engineer
- Systems Applications Engineer
- Application Systems Engineer

Neighboring titles such as Sales Engineer and Systems Administrator are rejected by strict occupation matching.

## Validation scope

The permanent benchmark covers:

- every catalog occupation and alias
- every SOC major group
- finance, accounting, law enforcement, healthcare, business, skilled trades, engineering, education, law, marketing, sports, economics, and technology
- all configured ambiguous acronyms
- safe acronyms such as RN, EMT, CNA, and DBA
- spelling variants
- generic unseen engineering titles
- source routing enrichment
- sector-specific external coverage links

## Remaining 8.1G work

This foundation is intentionally not the final universal-search sign-off. Remaining work includes:

- ingesting a generated O*NET-derived artifact rather than maintaining only the compact reviewed index
- adding more verified public employer sources and sector-specific routing
- recording explicit machine-readable search-state fields in the API and UI
- expanding the benchmark with live provider cases and location/level combinations
- friend beta testing across at least 12 career spheres
- measured recall/precision and production canary sign-off
