# Milestone 8C — Evidence-Grounded Smart Fit Matching

Milestone 8C makes Smart Fit conclusions auditable. Semantic extraction can improve recall, but a strength, partial match, or gap is useful only when MarketLens can show the exact request-time evidence behind it.

## Provenance contract

The structured Smart Fit response now uses provenance version `8c.1`.

Each scored requirement assessment includes:

- the exact job-description quote supporting the requirement
- whether that quote was verified against the current job input
- the exact resume quote supporting a non-missing match
- whether that quote was verified against the current resume input
- the source of the conclusion: `deterministic`, `model_assisted`, or `merged`
- a combined grounded flag used by evaluation and UI messaging

Existing `job_evidence`, `resume_evidence`, status, score, gap, and coaching fields remain available for response compatibility.

## Enforcement behavior

- An ungrounded job requirement is assigned zero scoring weight and cannot create a strength or important gap.
- An ungrounded resume quote is downgraded to missing proof and cannot create a strong match.
- Model-only evidence remains subject to the Milestone 8B direct-application and action-language safeguards.
- When deterministic and model-assisted extraction identify the same signal, provenance is reported as `merged` without letting the model override stronger deterministic evidence.
- Hard constraints remain conservative. An unverified hard-constraint quote is marked unclear rather than treated as confirmed.
- Gap groups carry the grounded posting quotes that produced them.

## User-facing evidence

The existing expandable **View detailed requirement breakdown** section shows the verified resume quote and an explanation containing the verified job quote and conclusion source. Main gap summaries also include their top grounded posting quote.

This avoids generating a second free-form AI explanation layer. The UI displays evidence already verified by the backend.

## Privacy

Grounding is request-scoped and does not require storing raw resume text or full job descriptions. The current request text is normalized in memory, checked against extracted quotes, and discarded after analysis.

## Evaluation

A permanent offline provenance benchmark runs across the Milestone 8A cases and separately measures:

- job-evidence grounding
- resume-evidence grounding
- provenance coverage
- direct evidence behind strong matches
- required/core job evidence behind high-priority gaps
- hard-requirement grounding
- critical-case and overall case pass rates

Every metric is required to pass at 100%. The workflow also runs focused adversarial tests and the complete backend suite without requiring a live model provider or API key.
