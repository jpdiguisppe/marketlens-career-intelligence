# Milestone 8B — Semantic Requirement Extraction

Milestone 8B improves optional model-assisted Smart Fit extraction without replacing deterministic scoring or evidence rules.

## Delivered contract

MarketLens now uses a versioned semantic extraction contract (`8b.1`) that distinguishes:

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

- Every accepted provider signal must include the smallest useful exact source phrase.
- Source phrases are checked against the redacted resume or job description.
- Provider output is validated in a strict context: the exact schema version and semantic fields are required, extra fields are rejected, and legacy provider-selected weights are invalid.
- Compatibility migration is limited to old internal Python fixtures; it is disabled for provider JSON.
- Unknown technologies must be emitted as grounded normal signals; legacy ungrounded unknown lists are not scored.
- Requirement weights are derived by MarketLens from requirement type rather than chosen by the model.
- Deterministic resume evidence remains authoritative whenever it already exists.
- A new model-only resume signal can count as demonstrated only when its exact source quote is grounded, it is classified as direct application, and deterministic action-language verification confirms applied work such as built, implemented, analyzed, or deployed.
- Other model-only signals remain mentioned, implied, or related rather than being inflated into strong proof.
- Credentials, experience, citizenship, clearance, work authorization, and travel remain conservative hard constraints. MarketLens does not guess that missing resume text satisfies them.
- Invalid versions, extra fields, fabricated source phrases, timeouts, HTTP failures, provider errors, invalid JSON, and schema failures produce typed errors that trigger deterministic fallback.
- Provider credentials remain backend-only and requests continue to use `store=false`.
- Raw resume and full job-description text are not persisted merely because model assistance was requested.

## Evaluation suite

The permanent fixture-backed evaluation requires no live provider or API key. It combines:

- six semantic-gap cases deliberately outside the curated skill ontology
- two overlap cases where deterministic extraction already recognizes Python, SQL, Docker, and Linux
- eight sectors: software, data, DevOps, cybersecurity, healthcare, finance, marketing, and education
- 26 expected requirements
- 10 resume-evidence checks
- 7 hard-constraint checks
- 4 critical cases

Final comparison:

- deterministic baseline requirement recall: **15.4%**
- grounded model requirement recall: **100%**
- grounded model requirement precision: **100%**
- merged requirement recall: **100%**
- semantic recall gain over the deterministic baseline: **84.6 percentage points**
- required/preferred/responsibility classification accuracy: **100%**
- semantic-category accuracy: **100%**
- evidence-status accuracy: **100%**
- hard-constraint accuracy: **100%**
- source-grounding pass rate: **100%**
- critical-case pass rate: **100%**

These results describe the reviewed synthetic benchmark, not universal real-world model accuracy. Live provider behavior, cost, latency, and model-to-model variance remain operational concerns for later Milestone 8 work.

## Automated validation

- 14 focused semantic contract, merge, and evaluation tests pass
- all 308 backend tests pass
- the original Milestone 8A deterministic Smart Fit benchmark remains green
- frontend TypeScript/Vite production build passes
- backend and frontend Docker images pass through standard CI
- the semantic benchmark CLI prints a readable report and JSON payload and exits nonzero on failure

## Next milestone

Milestone 8C will use this contract to make every model-assisted match and gap explanation explicitly evidence-grounded in the user-facing Smart Fit report. Personalized coaching, cost/latency controls, and the Career Planning Agent remain later phases.
