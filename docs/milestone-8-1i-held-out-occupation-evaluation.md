# Milestone 8.1I — Held-Out Occupation Evaluation

Date completed: August 5, 2026

## Status

```text
PASS — MILESTONE 8.1I COMPLETE
```

The universal occupation layer passed the independent deterministic benchmark and the bounded exact-revision production audit. Repeatable defects discovered during validation were converted into permanent regressions before completion.

## Purpose

This milestone measures occupation interpretation and title precision using committed cases stored separately from the production occupation registry.

The benchmark detects interpretation, ambiguity, unknown-query, and title-matching defects. A provider returning no current posting is not automatically treated as an occupation-understanding failure.

## Held-out benchmark results

The deterministic benchmark passed every committed case:

- 268/268 occupation queries
- 46 seed occupations
- all 23 SOC major groups
- 30 career spheres
- 46/46 canonical-title queries
- 46/46 level/search-modifier queries
- 46/46 misspelled-title queries
- 46/46 alternate-title queries
- 66/66 ambiguous-acronym cases covering 33 acronyms in bare and `jobs` forms
- 8/8 safe acronym or shortened-title queries
- 10/10 deliberately unknown phrases
- 92/92 title-precision checks
  - 46/46 relevant titles accepted
  - 46/46 misleading neighboring titles rejected

All configured benchmark thresholds were met with no case, threshold, or coverage failures.

## Exact-revision production audit

The production audit passed against exact deployed revision:

```text
9bd59046bc9c1f4efedc2ab13f2708c142a353e5
```

Measured live results:

- 40/40 cases passed
- 14 career spheres
- 32 recognized occupation cases
- 4 ambiguous cases
- 4 unknown cases
- 18 recognized searches returned current configured-source jobs
- 14 recognized searches produced honest zero-result/provider-coverage outcomes
- 47/47 returned titles were relevant after manual artifact review
- 100.0% returned-title precision
- ambiguous and unknown cases made zero provider requests
- 6,411.146 ms average measured case latency
- 30,204.991 ms maximum measured case latency
- 256,445.828 ms total measured audit latency

The audit bounded each response to at most three jobs and paced live requests below the public rate limit. Recognized zero-result cases were required to include an explanation and external continuation links.

## Production failures converted into regressions

Validation exposed and permanently covered:

- unsupported long nonsense queries unnecessarily fanning out to providers
- `Finance Fellow` admitted for Financial Analyst
- `School Nurse LPN` admitted for Registered Nurse
- `Medical Fellow` admitted for Medical Assistant
- generic rotational and internal-audit titles admitted for Accountant
- occupation-audit path filters failing to run after title-precision changes

Earlier production hardening in the same milestone sequence also covered unsupported abbreviations and accountant partner-program false positives.

The precision guards preserve legitimate forms such as `Emergency Department RN`, `School Nurse (RN)`, `Staff Accountant`, `Senior Analyst, Strategic Finance`, and `Certified Medical Assistant`.

## Permanent gates

The final title-precision candidate passed:

- 528/528 backend tests
- frontend TypeScript/Vite production build
- backend Docker build
- frontend Docker build
- Career Plan Agent Evaluation
- Provider Resilience
- Provider Telemetry
- Operational Reliability
- Secret and Log Safety
- both Railway deployments
- Production Career Plan Canary
- Milestone 8E Production Canary
- Production Occupation Audit

## Independence boundary

The benchmark labels are manually committed in evaluation files. Production code does not read the benchmark files, and the evaluator does not mutate the occupation catalog.

This is independent validation in the engineering sense. No friend, customer, or external-user beta is claimed.

## Provider limitations

Configured public providers do not represent every employer, platform, occupation, or location equally. Provider inventory and latency change independently of the occupation-understanding layer.

A recognized zero-result response is considered correct when MarketLens:

1. identifies the occupation deterministically;
2. reports attempted source coverage;
3. avoids unrelated filler results; and
4. provides an explanation and canonical continuation links.

The full O*NET-generated importer remains a future maintainability enhancement rather than a blocker because this evaluation did not reveal a material cross-sector registry gap.

## Follow-on

The completed evidence feeds [Milestone 8 Universal Search Production Sign-Off](milestone-8-universal-search-signoff.md) and issue #112.
