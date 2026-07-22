# Milestone 7 — Search Intent Foundation

The first Milestone 7 implementation separates a user's search into independent dimensions before source expansion begins.

## Dimensions

- **Job function:** software, data, cybersecurity, product, marketing, operations, healthcare, finance, design, or broader technology
- **Industry:** sports, entertainment, healthcare, financial services, education, nonprofit, or media
- **Experience level:** any, internship, entry, mid, or senior
- **Location:** the normalized optional location filter

This separation allows queries such as `sports marketing internship`, `healthcare data analyst`, and `financial services marketing` to preserve both the cross-industry function and the requested industry.

## Scope of this phase

- add a typed search-intent model
- detect the initial reusable industry taxonomy
- prefer a cross-industry function when a query includes both a function and an industry
- expose detected industry metadata through the search API
- preserve existing sports-industry precision rules

This phase does not yet expand external providers or enforce every detected industry during result filtering. Later Milestone 7 phases will use this metadata for source routing, coverage explanations, and broader industry-aware matching.
