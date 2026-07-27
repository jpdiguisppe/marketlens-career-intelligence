# Milestone 8D — Evidence-Bound Personalized Coaching

Milestone 8D adds optional model-assisted coaching after Smart Fit has completed extraction, scoring, role-aware analysis, and evidence grounding.

## Product boundary

The coaching provider may improve prioritization and explanation. It cannot change:

- fit score or fit band
- requirement type, weight, status, or strength
- hard-requirement status
- job or resume provenance
- grounding warnings
- the deterministic fallback

The existing deterministic coaching actions remain the complete fallback and are also retained behind personalized actions when space allows.

## Provider input

The coaching call does not receive the raw resume or full job description. It receives a compact structured context containing only:

- the completed fit summary
- grounded requirement references
- exact grounded resume evidence already accepted by MarketLens
- exact grounded job evidence already accepted by MarketLens
- grounded hard requirements
- deterministic coaching actions

The request remains backend-only, strict-schema validated, timeout-bounded, `store=false`, and non-persistent.

## Coaching contract `8d.1`

Each generated action identifies one existing reference and one coaching basis:

- `strength_positioning` for demonstrated or explicit evidence
- `wording_proof_gap` for mentioned, implied, or related evidence
- `experience_learning_gap` for high-priority missing requirements
- `hard_constraint_check` for citizenship, clearance, degree, work authorization, experience, or travel checks
- `lower_priority_preference` for lower-weight missing preferences

The provider must copy job and resume evidence exactly from the supplied grounded context. MarketLens rejects plans that:

- reference an unknown requirement
- invent or alter resume evidence
- alter the grounded job quote
- present a missing requirement as existing experience
- use a coaching basis inconsistent with the assessment status
- make hiring-probability, ATS-success, interview, or offer predictions
- repeat the same requirement as multiple top-level actions

## User-facing behavior

When personalized coaching succeeds:

- the coach summary begins with a clearly labeled personalized strategy
- application guidance appears directly below it
- the existing **Best next actions** cards show the prioritized personalized actions
- each action retains its grounded resume and job evidence in structured output
- deterministic actions fill any remaining action slots

When coaching is not requested or fails validation, the existing deterministic coach remains fully functional.

## Evaluation

The permanent offline evaluation requires 100% on:

- valid grounded-plan acceptance
- unknown-reference rejection
- invented-evidence rejection
- status/basis mismatch rejection
- changed-job-quote rejection
- unsupported-prediction rejection
- immutable scored-analysis preservation
- deterministic fallback completeness

Milestones 8A, 8B, and 8C remain authoritative for scoring, semantic extraction, and provenance.
