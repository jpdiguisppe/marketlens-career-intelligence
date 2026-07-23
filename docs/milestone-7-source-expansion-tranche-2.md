# Milestone 7 — Broader Source Coverage, Tranche 2

This tranche uses the secondary industry-only source pool to expand healthcare, education, media, legal/public-interest, policy, and early-career coverage without increasing broad-search provider fan-out.

## Added verified public ATS boards

- **ACLU** (`greenhouse:aclu`) — legal services, public interest, government, policy, advocacy, and nonprofit roles
- **Avalere Health** (`lever:avalerehealth`) — healthcare, life sciences, policy, compliance, advisory, and operations roles
- **WEBTOON / Wattpad** (`lever:wattpad`) — media, entertainment, content policy, legal-business, and internship roles
- **The Dispatch** (`lever:thedispatch`) — journalism, policy-adjacent media, legal-current-events work, and recurring internships
- **Kiddom** (`lever:kiddom`) — education technology, curriculum, product, and operations roles
- **Strada Education Foundation** (`lever:stradaeducation`) — education, workforce policy, nonprofit, internship, and co-op pathways

All six sources are classified as `industry_only`. They stay inactive for broad searches and are activated only when an exact registered industry is detected.

## Taxonomy expansion

Job functions now include `legal`, `compliance`, `policy`, `legal_operations`, and `contracts`. Industries now include `legal_services`, `government`, `public_interest`, `corporate_legal`, and `public_policy`. This supports searches such as:

- `legal internship Philadelphia`
- `sports legal operations internship`
- `healthcare compliance analyst entry level`
- `public interest policy internship`
- `financial services regulatory analyst`

## Precision behavior

Law-adjacent functions use strict title-aware matching before the generic occupation fallback. A clearly unrelated title such as `Software Engineering Intern` is therefore not accepted for `legal internship` merely because its description mentions work for a legal team.

Existing job families retain their established compatibility behavior; the strict path is limited to `legal`, `compliance`, `policy`, `legal_operations`, and `contracts`.

## Deliberate boundary

This tranche improves intent parsing, routing, and source coverage. It does not yet classify JD, bar-admission, law-school, or undergraduate credential requirements. Credential-aware legal filtering remains a separate later phase.
