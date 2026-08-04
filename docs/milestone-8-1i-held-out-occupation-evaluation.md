# Milestone 8.1I — Held-Out Occupation Evaluation

## Status

Evaluation harness candidate. Final results and production-audit evidence will be recorded only after CI, review, merge, exact-revision deployment, and the separate live production audit.

## Purpose

This milestone measures the universal occupation layer against committed cases that are stored separately from the production occupation registry and are not used to construct or modify that registry at runtime.

The benchmark is designed to detect interpretation and title-precision failures rather than provider inventory changes. A provider returning no current posting is not automatically treated as an occupation-understanding defect.

## Candidate benchmark coverage

- 268 total occupation-query cases
- 46 seed occupations
- all 23 SOC major groups
- at least 12 non-overlapping career spheres
- 46 canonical-title queries
- 46 level/search-modifier queries
- 46 misspelled-title queries
- 46 alternate-title queries
- 66 ambiguous-acronym queries covering 33 acronyms in bare and `jobs` forms
- 8 safe acronym or shortened-title queries
- 10 deliberately unknown phrases
- 92 title-precision checks: 46 relevant titles and 46 misleading neighboring titles

## What is measured

The evaluator reports:

- overall query accuracy
- recognized occupation accuracy
- canonical-title accuracy
- modifier handling
- spelling-repair accuracy
- alternate-title accuracy
- ambiguous-acronym clarification accuracy
- safe-acronym accuracy
- unknown-query rejection accuracy
- title accuracy, precision, recall, and negative rejection rate
- represented SOC groups and career spheres

Every candidate case is currently a blocking deterministic regression. Thresholds are intentionally strict because a known committed interpretation or title guard should not become flaky.

## Independence boundary

The benchmark labels are manually committed in evaluation files. Production code does not read the benchmark files, and the evaluator does not mutate the occupation catalog.

This is independent validation in the engineering sense, not a claim of external-user research. No friend or customer beta is being claimed.

## Remaining work before completion

Milestone 8.1I is not complete until:

1. the evaluator passes the full permanent CI gate set;
2. review findings are resolved and converted into regressions where appropriate;
3. at least 40 representative searches are audited against the deployed production revision;
4. repeatable production failures are fixed or explicitly documented;
5. measured results and public-provider limitations are recorded.

Successful completion feeds Milestone 8.1J, the final universal-search production sign-off.
