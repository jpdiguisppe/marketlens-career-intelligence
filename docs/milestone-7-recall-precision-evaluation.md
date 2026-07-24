# Milestone 7 — Recall and Precision Evaluation

MarketLens now has a deterministic, offline benchmark for job-search behavior. It measures the search logic independently from live provider availability so CI failures point to product regressions rather than changing job-board inventory.

## Coverage

The benchmark includes three layers:

1. **Intent accuracy** — job function, industry, experience level, and location parsing.
2. **Candidate recall and precision** — relevant postings admitted and obvious false positives rejected.
3. **Source-routing correctness** — broad searches stay on primary sources while matching industry-only boards activate for sports, nonprofit, healthcare, education, media, legal, public-interest, and financial-services searches.

The curated cases cover general technology, software, data, cybersecurity, finance, marketing, sports, healthcare, education, nonprofit, media, legal, compliance, policy, legal operations, contracts, internships, co-ops, fellowships, rotational programs, law-student roles, and licensed-attorney roles.

## Acceptance thresholds

The benchmark enforces:

- 100% intent accuracy
- at least 95% candidate accuracy
- at least 95% candidate recall
- at least 95% candidate precision
- at least 95% negative rejection
- 100% routing accuracy
- 100% pass rate for critical safety cases

It also enforces minimum benchmark size so future changes cannot make CI green by silently deleting difficult cases.

## Running the evaluation

From `backend`:

```bash
python scripts/run_job_search_evaluation.py
```

The command prints a readable summary and a JSON report, then exits nonzero if any acceptance threshold or critical case fails. The same benchmark runs automatically through pytest in CI.

## Scope boundary

This evaluation is deterministic and does not contact live job providers. Live source health, production deployment, external-link behavior, and end-to-end search UX are verified separately in the Milestone 7 production smoke test.
