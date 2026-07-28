# Milestone 8E Completion — Reliability and Operations

## Decision

**GO for Milestone 8.1, the Career Planning Agent, under the existing MarketLens safety boundaries.**

Milestone 8E demonstrated that Smart Fit remains complete and useful when provider stages are disabled, unavailable, malformed, rejected, or slow. Successful semantic extraction may add grounded recall and therefore change the scored requirement set; provider failure must instead return the exact deterministic report. Personalized coaching remains non-authoritative and cannot change scores, evidence status, hard constraints, or provenance.

This is not approval for an unrestricted chatbot or autonomous application system. Milestone 8.1 must reuse the tested MarketLens search and Smart Fit tools, retain their provenance and telemetry, preserve workflow state, and require human approval before consequential actions.

## Acceptance summary

| Gate | Required threshold | Measured result | Decision |
| --- | ---: | ---: | --- |
| Repeated deterministic output stability | 100% | 100% across 12 cases, 10 sectors, and 3 runs per case | Pass |
| Operational invariant pass rate | 100% | 100% | Pass |
| Disabled-provider fallback preservation | 100% | 100% across 6 cases | Pass |
| Provider-failure fallback preservation | 100% | 100% across 15 simulated scenarios | Pass |
| Unsupported or ungrounded scored conclusions | 0 | 0 accepted in permanent evaluation gates and production canaries | Pass |
| High-confidence secret exposures | 0 | 0 across 230 tracked files and every reachable commit patch | Pass |
| Rejected-input echo in HTTP 422 | 0 | 0 in production canary | Pass |
| Internal exception details in HTTP 500 | 0 | 0 by permanent safety tests | Pass |
| Unknown-model guessed pricing | 0 | 0; unknown models report `pricing_unavailable` | Pass |
| Frontend fallback/status contract | Required | Deterministic, AI-assisted, explicit fallback, collapsed Operational details, and unavailable-cost states validated | Pass |
| Exact deployed revision | Exact match | Backend and frontend expose bounded Railway Git revisions; post-merge canary waits for both to match `github.sha` | Pass |
| Permanent repository gates | All green | Reliability, resilience, telemetry, secret/log safety, backend, frontend, and Docker gates green before merge | Pass |

## 8E.1 — Operational reliability

Completed in PR #69, merge commit `3f3bec1bd7589a28d4dede762d4c5cd4d33720a6`.

- 12 operational cases covered 10 sectors.
- Each case ran three times through the deterministic path.
- Repeated-run output stability was 100%.
- Operational invariants passed at 100%.
- Six disabled-provider cases preserved the complete deterministic report at 100%.
- Reports contain only case IDs, metrics, fingerprints, and bounded status summaries; fixture document text is excluded.

## 8E.2 — Provider resilience

Completed in PR #71, merge commit `78c404e3d4e051602f163039f3f88bc02fa0c086`.

Fifteen offline scenarios covered unavailable configuration and extraction/coaching failures involving:

- timeout and transport failures
- HTTP 429 and other provider HTTP errors
- invalid JSON and missing output
- schema mismatches
- ungrounded extraction
- rejected coaching references

Every scenario preserved the deterministic report. Public fallback metadata retained bounded codes such as `provider_timeout` and `coaching_schema_mismatch`, while malformed or unsafe exception values collapsed to generic safe codes. Evaluation artifacts exclude documents, API keys, provider bodies, prompts, and stack traces.

## 8E.3 — Telemetry and version reporting

Completed in PR #73, merge commit `ac0b027424dee98a5c991723eb45999f4a3abc8c`.

Request-scoped telemetry now reports, separately for extraction and coaching:

- requested state, outcome, and bounded status code
- configured or returned model
- prompt and schema versions
- provider latency
- Responses API token usage
- bounded standard-rate USD cost estimates when pricing is known

The pricing catalog is versioned as `openai-standard-2026-07-28`. Known `gpt-5.4-mini` IDs use the verified standard rates current on that date: $0.75 per million uncached input tokens, $0.075 per million cached input tokens, and $4.50 per million output tokens. Regional, priority, batch, negotiated, and other adjustments are explicitly outside the estimate.

Unknown models are never assigned guessed prices. Failed stages never invent token usage or cost, and mixed outcomes are labeled `partial_estimate`. Live reports expose telemetry in a collapsed **Operational details** panel; saved reports omit it.

## 8E.4 — Secret and log safety

Completed in PR #75, squash merge commit `139fdcb48ab843c1387c23add5862f19b04d1ae8`.

Controls now include:

- request-scoped résumé and job-text redaction
- credential, bearer-token, credential-bearing URL, and high-confidence provider-key redaction
- control-character and log-injection protection with bounded single-line values
- removal of raw traceback text from operational logs
- safe HTTP 422 responses that do not echo rejected values
- generic HTTP 500 responses without internal exception details
- tracked-tree and full reachable-history secret scanning
- a permanent Secret and Log Safety CI gate

The first complete scan examined 230 tracked files and every reachable commit patch and found zero high-confidence secret exposures.

## 8E.5 — Production canary and frontend validation

Implemented in PR #77, squash merge commit `3332bee082018572b101b3364dec6e1e962f0d1e`.

The permanent canary runs on relevant pull requests, every push to `main`, a daily schedule, and manual dispatch. It validates:

- backend health and safe model-status metadata
- frontend root, JavaScript assets, HTTPS runtime API configuration, and deployed UX markers
- deterministic Smart Fit completeness and grounding
- model-assisted success or exact deterministic fallback
- prompt/schema/model, latency, token, and cost telemetry shape
- safe HTTP 422 behavior without rejected-input echo
- bounded document-free success and failure artifacts

For push runs, both Railway services expose a validated `RAILWAY_GIT_COMMIT_SHA`. The canary waits until the backend and frontend each report the exact triggering `github.sha` before issuing Smart Fit probes. The workflow also publishes a visible `Milestone 8E Production Canary` commit status.

### Measured live observations

The production canary observed both major provider paths:

1. **Degraded provider path:** a provider timeout and rejected coaching output still returned the exact deterministic fingerprint, a 55% baseline score, zero grounding warnings, and a bounded partial estimate of $0.00444825.
2. **Successful semantic extraction path:** the deterministic baseline scored 55%. Grounded model-assisted extraction expanded the evaluated set to 12 requirements and scored 37%, with zero grounding warnings. The request used 4,541 provider tokens, approximately $0.01007925, and 16,142.36 ms of provider latency. Coaching then encountered a schema mismatch and safely fell back without changing the analysis.

The score difference in the successful path is expected: grounded semantic extraction may add legitimate requirements that deterministic parsing did not recognize. This differs from a provider failure, where the report fingerprint must remain exactly deterministic.

## Required invariants after 8E

- No duplicate requirements may be created from the same grounded evidence.
- No unsupported strengths, experience, credentials, or skills may be presented as conclusions.
- Every scored conclusion must remain traceable to exact job and résumé evidence.
- Successful semantic extraction may add grounded recall, but it cannot bypass conservative evidence rules.
- Personalized coaching cannot change scores, evidence status, hard constraints, or provenance.
- Every provider failure must return the complete deterministic report unchanged.
- Résumé text, job text, credentials, provider keys, prompts, provider bodies, and raw exceptions must not enter operational logs or evaluation artifacts.
- Token, latency, model, version, and approximate cost telemetry must remain document-free and request-scoped.

## Residual risks and follow-ups

These items are not blockers for Milestone 8.1, but they remain explicit engineering follow-ups:

- Provider latency is material. The observed assisted request spent about 16.1 seconds in provider stages, so the agent must preserve progress visibility, timeouts, cancellation boundaries, and deterministic continuation.
- Coaching schema mismatches occurred in live canaries. The fallback is safe and complete, but prompt/schema compatibility should continue to be measured and improved.
- Cost values are estimates rather than invoices. Budgets should use telemetry distributions and conservative ceilings rather than treating one request as representative.
- The daily canary uses a synthetic résumé/job pair. It proves production contracts and failure behavior, not every real-world domain case; the offline multi-sector suites remain the broader correctness gate.
- Exact-revision canaries depend on Railway exposing a valid Git commit SHA. Invalid or missing values deliberately prevent a false green result.

## Milestone 8.1 entry conditions

The Career Planning Agent may begin only if it:

1. calls the existing job-search and Smart Fit tools instead of reproducing their logic in a prompt;
2. retains evidence provenance, deterministic fallback, safe status codes, and provider telemetry;
3. stores workflow state and an audit trail without persisting raw documents unnecessarily;
4. treats model-generated plans as proposals rather than authoritative facts;
5. requires human approval before applications, outreach, profile changes, purchases, or other consequential actions;
6. remains useful when every model-assisted stage is unavailable.

## Final result

Milestone 8E met every defined reliability, fallback, grounding, observability, privacy, secret-safety, frontend, deployment, and CI gate. The measured result supports a **GO** decision for the bounded Career Planning Agent phase.
