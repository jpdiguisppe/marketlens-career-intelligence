# Milestone 8A — Smart Fit Evaluation Foundation

Milestone 8A establishes a permanent offline benchmark for Smart Fit before MarketLens expands optional model-assisted behavior.

## Why this comes first

A model response sounding more polished does not prove that analysis improved. MarketLens needs measurable checks for whether it extracted the correct requirements, connected them to real resume evidence, identified genuine gaps, rejected unsupported strengths, and preserved deterministic fallback behavior.

The benchmark therefore runs without an API key and treats the deterministic engine as the initial baseline. Future model-assisted changes must run against the same cases and report whether they improve, preserve, or regress each metric.

## Evaluated dimensions

- complete requirement-set recall and precision
- required, preferred, and core-responsibility classification
- evidence-status accuracy
- resume-evidence linkage
- genuine gap recall
- false-gap rejection
- unsupported-strength rejection
- hard-constraint handling
- deterministic and model-unavailable fallback behavior
- bounded fit-score expectations
- sector-level and critical-case pass rates

## Permanent shrinkage guards

The versioned dataset enforces minimum case, sector, and critical-case counts, along with globally unique case IDs. Removing difficult coverage silently causes the benchmark loader or pytest gate to fail.

The initial dataset covers software, data/AI, systems/cloud, frontend, cybersecurity, finance, healthcare, sales/marketing, operations/administration, and regulated technical work.

## Run locally

From the repository root:

```bash
cd backend
python scripts/run_smart_fit_evaluation.py
```

The command prints a readable summary followed by a JSON report and exits nonzero when a critical case or configured threshold fails.

The same benchmark is also enforced through pytest:

```bash
cd backend
pytest -q tests/test_smart_fit_evaluation.py
```

## Privacy and provider boundaries

- the benchmark contains synthetic resume and job text only
- it does not persist resume or job-description input
- it does not require or expose a provider key
- it does not contact a model provider during the normal baseline run
- the model-unavailable case verifies safe deterministic fallback
- future provider-backed evaluations must remain explicitly opt-in and separately report cost and latency

## Milestone 8 continuation

This foundation precedes semantic model extraction, evidence-grounded model matching, personalized coaching, operational controls, and the later Career Planning Agent. No AI feature should be considered complete merely because it produces plausible prose; it must remain schema-valid, evidence-grounded, measurable, and safely replaceable by deterministic behavior.
