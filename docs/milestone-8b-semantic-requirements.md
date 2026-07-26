# Milestone 8B — Semantic Requirement Extraction

Milestone 8B improves optional model-assisted Smart Fit extraction without replacing deterministic scoring or evidence rules.

## First implementation slice

This branch introduces a versioned semantic extraction contract (`8b.1`) that distinguishes:

- required qualifications
- preferred qualifications
- core responsibilities
- supporting context
- tools and technologies
- credentials and education
- years of experience
- domain knowledge
- implied capabilities
- methodologies and processes
- hard constraints

Resume signals also record whether the quoted evidence is direct application, an explicit mention, academic context, implied by another tool, or related experience.

## Safety boundaries

- Every accepted model signal must include the smallest useful exact source phrase.
- Source phrases are checked against the redacted resume or job description.
- Unknown technologies must be emitted as grounded normal signals; legacy ungrounded unknown lists are not scored.
- Requirement weights are derived by MarketLens from the requirement type rather than chosen by the model.
- Deterministic resume evidence remains authoritative.
- Model-only resume signals are capped at conservative evidence strength and cannot become demonstrated proof by themselves.
- Invalid versions, extra fields, fabricated source phrases, timeouts, provider errors, and invalid JSON produce typed failures that trigger deterministic fallback.
- Provider credentials remain backend-only and requests continue to use `store=false`.

## Offline validation

Fixture-backed tests require no live provider or API key. They cover:

- strict schema versioning
- extra-field rejection
- redaction and backend-only request behavior
- exact source grounding
- timeout conversion to typed fallback errors
- requirement weight derivation
- protection against model evidence inflation
- preservation of stronger deterministic requirements

## Remaining 8B work

- expand fixture cases across credentials, experience, responsibilities, domain knowledge, and ambiguous required/preferred language
- add model-assisted comparison metrics to the Milestone 8A evaluation report
- expose prompt/schema version transparency through model status
- validate end-to-end fallback and model-assisted Smart Fit behavior
- complete full CI and Docker validation
