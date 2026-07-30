# Milestone 8.1 Completion — Bounded Career Planning Agent

Date opened for final validation: July 30, 2026

## Current decision

```text
NO-GO FOR MILESTONE CLOSURE
```

The implementation, permanent evaluation, security, privacy, recovery, frontend, and Docker gates are complete. Final closure remains blocked until the exact deployed Railway revision and the authenticated production browser lifecycle are validated and recorded below.

This is a launch-evidence decision, not an implementation failure.

## Product delivered

Milestone 8.1 delivers one bounded, authenticated, resumable Career Planning Agent that:

1. accepts a validated career goal and practical constraints
2. calls the existing public job-search implementation
3. deterministically selects at most five candidates
4. calls existing Smart Fit analysis for selected jobs
5. synthesizes a deterministic opportunity portfolio, recurring evidence, recurring gaps, limitations, and at most twenty proposed actions
6. optionally makes one strict-schema model call over reduced deterministic facts
7. persists the final proposal for explicit user review

The private workspace supports:

- goal creation
- résumé upload or paste for request-time analysis
- seven-step progress
- source and candidate-selection audit
- cancellation and retry
- deterministic and model/fallback visibility
- evidence-linked opportunity and action review
- bounded explanations
- action editing
- approval and rejection
- plan history and reopening
- deletion

## Authority and safety boundaries

Search and Smart Fit remain authoritative tools. The optional model may organize only existing deterministic IDs and enums.

The model cannot:

- change scores, confidence, evidence status, provenance, or hard requirements
- add or remove analyzed jobs
- invent qualifications, experience, credentials, projects, or résumé claims
- add unsupported action types
- apply to jobs, contact recruiters, edit profiles, purchase services, or call unrestricted tools
- approve or reject a plan
- predict interviews, offers, salaries, or hiring probability

Raw résumé text and full job descriptions are not persisted in Career Plan records. Every private resource is filtered by authenticated user ownership, and cross-user access returns `404`.

## Integrated implementation evidence

The integrated Milestone 8.1E revision is:

```text
68fb6b6451b1815610f7cd828d75af01f7882670
```

Measured evaluation evidence at that revision:

- 10 representative career sectors
- 10 committed task-level cases
- 3 repeated runs per case
- 30 stable deterministic executions
- 0 failed cases
- 104.740 ms total offline evaluation latency
- 44 focused agent security/privacy/resilience tests passed in 2.43 seconds
- 439 complete backend tests passed in 23.51 seconds
- frontend TypeScript/Vite production build passed
- backend Docker image passed
- frontend Docker image passed
- Career Plan Agent Evaluation passed
- Smart Fit Evaluation passed
- Operational Reliability passed
- Provider Resilience passed
- Provider Telemetry passed
- Secret and Log Safety passed

See [`milestone-8-1-agent-evaluation.md`](milestone-8-1-agent-evaluation.md) for the detailed fixture, budget, failure, and residual-risk evidence.

## Production-signoff additions

Milestone 8.1F adds:

- a canonical public `GET /deployment/status` endpoint
- a compatibility deployment-revision alias under Saved Jobs
- sanitized Railway branch/environment reporting
- frontend runtime revision verification through `config.js`
- a production canary client using only synthetic documents
- a GitHub Actions production canary with retained evidence artifacts
- automatic public exact-revision validation after every `main` deployment
- manually dispatchable full authenticated validation
- README and portfolio walkthrough reconciliation
- this measured GO/NO-GO record

The canary never prints bearer tokens or provider credentials. Every authenticated canary plan is deleted in a `finally` cleanup path.

## Production canary modes

### Public mode

Public mode waits for the frontend and backend Railway services to report the expected 40-character commit SHA, then checks:

- backend health
- backend revision, branch, and environment
- frontend runtime revision
- frontend API base URL
- deployed Career Plan bundle markers
- model configuration status
- signed-out rejection of private Career Plan access
- live bounded public-source search and source coverage
- deterministic Smart Fit with synthetic résumé/job text

When explicitly requested and the backend model is configured, public mode can also exercise one model-assisted Smart Fit request and record provider latency, token use, and estimated cost.

### Full authenticated mode

Full mode requires a short-lived canary bearer token stored as a GitHub Actions secret. It adds:

- private Career Plan creation
- deterministic execution through all seven steps
- proposal and action bounds
- proposed-only action state
- saved explanation request
- action edit and explicit approval
- reopening the approved plan
- deletion and cleanup
- optional second-identity ownership isolation
- optional model-assisted Career Plan execution and telemetry
- timing-sensitive cancellation followed by retry and action-deduplication validation

The repository secrets are referenced only as:

```text
MARKETLENS_CANARY_BEARER_TOKEN
MARKETLENS_CANARY_SECOND_BEARER_TOKEN
```

Their values must never be committed, printed, or copied into this document.

## Acceptance matrix

| Requirement | Status | Evidence |
| --- | --- | --- |
| Complete backend, frontend, evaluation, security, and Docker gates | PASS at integrated implementation | 439 backend tests and all named workflows passed at `68fb6b6` |
| Safe backend deployment identity | IMPLEMENTED, production result pending | `GET /deployment/status` |
| Safe frontend deployment identity | IMPLEMENTED, production result pending | Railway `config.js` runtime revision |
| Exact frontend/backend revision | PENDING | automatic post-merge public canary |
| Public live job search | PENDING | production canary artifact |
| Deterministic production Smart Fit | PENDING | production canary artifact |
| Production model status and optional live measurement | PENDING | production canary artifact |
| Signed-out private-route boundary | PENDING | production canary artifact |
| Signed-in create/execute/edit/approve/reopen/delete | PENDING | full authenticated canary or recorded browser session |
| Production cancellation and retry | PENDING | full authenticated canary or recorded browser session |
| Cross-user production isolation | PENDING | second canary identity or documented manual verification |
| Prompt-injection production canary | PENDING | synthetic authenticated plan content |
| Current signed-in screenshots | PENDING | exact-revision browser capture |
| README and walkthrough separate current vs. future work | IMPLEMENTED, review pending | README and portfolio walkthrough in sign-off PR |
| Explicit final GO/NO-GO | NO-GO | this document |

## Manual browser validation checklist

Use only synthetic or non-sensitive data.

1. Confirm the frontend revision from `/config.js` matches the intended merged SHA.
2. Confirm the backend `/deployment/status` revision matches the same SHA.
3. Open the frontend in a clean browser session.
4. Sign in through Clerk.
5. Open `#career-plans`.
6. Create a deterministic Career Plan for an entry-level software role in Philadelphia.
7. Confirm all seven steps become visible and the final status is `awaiting_approval`.
8. Inspect provider coverage and the Candidate Selection Audit.
9. Confirm selected and excluded jobs show deterministic reason codes.
10. Confirm every action is shown as a proposal.
11. Request a job, action, gap, or model-contribution explanation.
12. Edit one action and approve the plan.
13. Refresh and reopen the approved plan from history.
14. Create another plan, request cancellation while it is running, and retry it.
15. Confirm the retry does not duplicate actions.
16. Run an optional AI-organized plan when the production model is configured.
17. Record model status, latency, total tokens, estimated cost, and fallback behavior.
18. Sign out and confirm private history disappears.
19. Sign back in and delete all synthetic canary plans.
20. Capture current desktop and narrow-width screenshots from the exact deployed revision.

## Required screenshots

The final sign-off should include production captures of:

- Career Plan goal form and workspace switcher
- seven-step running or completed progress
- Candidate Selection Audit
- opportunity portfolio and evidence-linked actions
- deterministic/model/fallback status
- bounded explanation result
- edited approval state
- private plan history
- narrow/mobile-width layout

Mocked or local-only images do not satisfy the production screenshot requirement.

## Residual risks

Even after a GO decision, the following limitations remain:

- public job-source coverage is intentionally incomplete and time-varying
- external application URLs can change after a plan is created
- Railway deploy timing may temporarily produce different frontend/backend revisions; the canary must wait for convergence
- cancellation is cooperative between workflow stages, not a process kill
- provider latency and cost are externally controlled and can change
- a short-lived Clerk token is required for automated authenticated canaries
- this is a portfolio product and should not receive highly sensitive data
- approval records a plan decision but does not execute external actions

## GO criteria

Change the decision to `GO` only after:

- the final sign-off PR and all required workflows pass
- Railway deploys the intended merged revision
- both services report the same exact SHA
- public production canary passes
- signed-in lifecycle passes
- cancellation/retry is observed or a precise limitation is accepted and documented
- production model behavior is measured when configured
- current production screenshots are committed
- README and walkthrough claims match the deployed product
- Issue #86 contains the measured evidence
- parent Issue #80 is updated before closure

## Final evidence log

This section must be updated after deployment.

| Field | Result |
| --- | --- |
| Intended revision | Pending sign-off PR merge |
| Backend deployed revision | Pending |
| Frontend deployed revision | Pending |
| Public canary | Pending |
| Authenticated canary | Pending |
| Model configured | Pending |
| Model latency | Pending |
| Model total tokens | Pending |
| Model estimated cost | Pending |
| Cancellation/retry | Pending |
| Cross-user production isolation | Pending |
| Screenshots committed | Pending |
| Final decision | **NO-GO** |
