# Milestone 8.1E — Career Planning Agent Evaluation

## Decision

**PASS for the Milestone 8.1E implementation and permanent evaluation gate.**

This decision means the bounded Career Planning Agent has reproducible offline task-level evaluation, permanent security/privacy/resilience tests, documented budgets, and a CI workflow that exits nonzero on failures. It does **not** constitute public-launch sign-off. Exact-revision deployment, browser validation, real-provider execution, production authentication, screenshots, and the production canary remain in Milestone 8.1F / Issue #86.

## Evaluated revision

The measured implementation head before this evidence document was added was:

`5792b8d45b30020163c24bba200f0cf7e1a080a7`

The same code will be revalidated after this document is committed and before merge.

## Task-level fixture coverage

The committed fixture set contains 10 representative sectors:

1. technology
2. business
3. education
4. science
5. engineering
6. healthcare
7. public service
8. creative work
9. trades
10. service work

Each case runs three times through the production candidate selector and deterministic planner. The evaluator does not duplicate scoring or planning logic and does not call a public job provider or model.

### Measured result

| Metric | Result |
| --- | ---: |
| Representative sectors | 10 |
| Cases | 10 |
| Runs per case | 3 |
| Deterministic executions | 30 |
| Failed cases | 0 |
| Total offline evaluation latency | 104.740 ms |
| Slowest case | 18.410 ms |

Every repeated projection remained stable after normalizing only the generated timestamp and run identifier.

## Permanent security and resilience matrix

The dedicated `Career Plan Agent Evaluation` workflow runs the task-level evaluator and a focused permanent pytest matrix covering:

- authenticated ownership and cross-user `404` behavior
- create/list/read/execute/cancel/decision/explain/delete boundaries
- atomic start and stale-version conflicts
- deterministic candidate selection and exclusions
- search and Smart Fit tool privacy
- complete deterministic fallback
- prompt-injection and policy-changing output rejection
- provider timeout, transport, HTTP, invalid JSON, missing output, schema mismatch, unknown reference, and duplicate reference failures
- saved-plan explanation reference bounds
- cancellation recovery and failed-run retry
- action deduplication and proposal-only status after recovery
- raw résumé, job-description, credential, and provider-key exclusion from stored summaries, proposals, audit events, and model payloads
- model context and cost policy
- deliberate evaluator regression failure
- fresh-interpreter import order

### Measured result

| Gate | Result |
| --- | ---: |
| Focused permanent agent tests | 44 passed in 2.43 s |
| Complete backend suite | 439 passed in 23.51 s |
| Frontend TypeScript/Vite build | PASS |
| Backend Docker image | PASS |
| Frontend Docker image | PASS |
| Smart Fit Evaluation | PASS |
| Operational Reliability | PASS |
| Provider Resilience | PASS |
| Provider Telemetry | PASS |
| Secret and Log Safety | PASS |

## Adversarial coverage

The representative fixtures include malicious text in multiple untrusted surfaces:

- job descriptions
- job titles
- company names
- application URLs

Examples attempt to:

- ignore prior instructions
- apply automatically
- contact a recruiter
- reveal credentials or patient data
- create unsupported experience
- bypass human approval
- purchase a course or equipment
- change fit scores or guarantee an offer

The evaluator verifies that these strings cannot create a new action type, change the selected tool boundary, remove approval requirements, alter hard-requirement handling, or escape the deterministic proposal contract.

## Grounding and action invariants

The gate enforces the following invariants:

1. Search and Smart Fit remain authoritative tools.
2. At most five jobs enter one planning run.
3. The proposal contains only selected job references.
4. Every portfolio evidence or gap reference resolves to a saved evidence record.
5. Every action references only known jobs and evidence.
6. Every action remains `proposed` until a user decision.
7. A confirmed hard-requirement failure remains a `skip` and cannot receive an apply action.
8. Action identifiers are unique.
9. Raw résumé and full job-description markers do not enter safe summaries, proposals, or audit payloads.
10. Repeated identical deterministic runs produce the same normalized result.
11. Cancellation or a safe Smart Fit failure can be retried on attempt two without duplicate actions or corrupted audit state.
12. Model output cannot add tools, evidence, scores, hard requirements, actions, approval decisions, or external side effects.

## Documented budgets

| Budget | Limit |
| --- | ---: |
| Jobs analyzed per run | 5 |
| Proposal actions | 20 |
| Model calls per run | 1 |
| Model context | 65,536 bytes |
| Model total tokens | 8,000 |
| Model latency | 30,000 ms |
| Estimated model cost | $0.05 per run |
| Offline deterministic case latency | 2,000 ms |

A permanent policy test verifies an under-budget representative context and independently verifies that every over-budget dimension returns its expected failure code.

## Failure-gate proof

The first run of the new workflow failed before evaluation because a fresh interpreter exposed an import-order cycle between `app.skill_extractor` and the eagerly initialized `app.analysis` package.

The workflow still:

- preserved the evaluator and pytest output as an artifact
- posted a safe pull-request failure summary
- reached the explicit nonzero failure step

The ontology was then moved to the dependency-light `app.skill_ontology` module, while `app.analysis.skill_ontology` remains a compatibility re-export. A permanent subprocess test now imports and runs the evaluator first in a fresh interpreter. This confirms the gate is capable of detecting failures and is not an always-green reporting script.

## Residual risks and limitations

The following items remain intentionally open for Issue #86:

- The representative task-level evaluator is offline and uses committed safe fixtures; it does not prove current public-provider availability or result quality.
- Model budgets are enforced as policy and tested against the bounded prompt path, but exact live provider latency, token usage, and cost must be measured on the deployed revision.
- Cancellation is cooperative at workflow boundaries; it cannot interrupt an individual blocking provider request already in progress.
- SQLite-based concurrency tests prove state and ownership contracts but do not replace production Postgres contention checks.
- The evaluator proves backend contracts, not browser rendering, keyboard navigation, mobile layout, Clerk production authentication, or deployed CORS behavior.
- The fixture suite is representative rather than statistically comprehensive and does not establish hiring outcomes or market-wide accuracy.
- Public job content can change after analysis; MarketLens does not guarantee posting freshness or continued availability.

## Entry conditions for Milestone 8.1F

Issue #86 may proceed when the merged revision preserves all of the following:

- the task-level evaluation workflow remains green
- the complete backend and frontend build gates remain green
- both production images build
- secret/log and provider gates remain green
- production deploy identifies the exact merged revision
- authenticated end-to-end browser scenarios validate deterministic and model-fallback paths
- a real-provider canary records source coverage, latency, token use, estimated cost, and safe fallback behavior
- README, architecture documentation, screenshots, and launch/future-roadmap boundaries match the deployed product
