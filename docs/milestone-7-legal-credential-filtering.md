# Milestone 7 — Credential-Aware Legal Filtering

This phase separates legal and law-adjacent postings by the minimum credential level indicated by their titles and requirements.

## Credential bands

- **Undergraduate-accessible** — legal intern, legal assistant, paralegal, compliance analyst, policy analyst/intern, contracts analyst, legal operations, and similar roles that do not require law-school enrollment or attorney licensure.
- **Law-student-only** — summer associate, law clerk, legal extern, judicial intern/extern, 1L/2L/3L, JD-candidate, and other postings that explicitly require current law-school enrollment.
- **Licensed/JD-required** — attorney, counsel, lawyer, prosecutor, public defender, solicitor, barrister, and postings that explicitly require a JD, bar admission, or a license to practice law.
- **Unknown** — postings whose title and description do not provide enough evidence to assign a credential band.

## Search behavior

- `legal internship` and early-career legal/compliance/policy/contracts searches default to undergraduate-accessible roles.
- `law student internship`, `2L summer associate`, `law clerk`, and similar searches target law-student roles.
- `attorney`, `counsel`, JD-required, and bar-admission searches target licensed roles.
- Generic searches such as `legal jobs` remain unfiltered by credential when the user has not expressed a credential level.
- Unknown postings remain eligible when they do not explicitly contradict the requested band, preserving recall without admitting known mismatches.

## Precision safeguards

- An `Associate Attorney` is not treated as an undergraduate entry-level result merely because the title contains `associate`.
- A `Compliance Counsel` requiring a JD or bar admission is excluded from entry-level compliance searches.
- A generic undergraduate legal internship is excluded from a law-student-specific search.
- A summer-associate, law-clerk, or judicial-intern posting is excluded from a generic undergraduate legal-internship search when law-school requirements are present.
- Non-legal search behavior is unchanged.

## Validation boundary

The regression suite covers query-band inference, posting classification, undergraduate legal internships, law-student searches, licensed-attorney searches, compliance-counsel exclusions, inclusive undergraduate/law-student postings, unknown evidence, and unchanged non-legal scoring. The full backend suite must pass before the integration is committed, followed by the normal frontend and Docker validation pipeline on the clean branch head.

This filtering is deterministic and evidence-based. It does not infer a candidate's personal credentials, provide legal advice, or claim that every employer uses legal titles consistently.