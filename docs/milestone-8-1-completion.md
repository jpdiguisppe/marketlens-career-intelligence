# Milestone 8.1 Completion — Bounded Career Planning Agent

Date completed: July 30, 2026

## Final decision

```text
GO — MILESTONE 8.1 COMPLETE
```

The bounded Career Planning Agent passed implementation, evaluation, security, privacy, recovery, frontend, Docker, exact-revision production, authenticated browser, and responsive-layout validation.

The validated functional production revision is:

```text
31acd2b7a587cf4fdc9c2cebe0dbf4b7dce567f1
```

This completion document and its screenshot assets are a documentation-only descendant of that validated runtime revision. They do not change workflow behavior, model authority, persistence, authentication, or production safety boundaries.

## Product delivered

Milestone 8.1 delivers one authenticated, resumable, bounded Career Planning Agent that:

1. accepts a validated career goal and practical constraints
2. calls the existing public job-search implementation
3. deterministically selects at most five candidates
4. calls the existing Smart Fit implementation for selected jobs
5. creates a deterministic opportunity portfolio, recurring evidence, recurring gaps, limitations, and no more than twenty proposed actions
6. may make one strict-schema model call over reduced deterministic facts
7. persists the proposal for explicit user review and decision

The production workspace supports:

- goal creation and request-time résumé upload or paste
- seven-step progress with durable attempts and audit events
- source coverage and deterministic candidate-selection audit
- deterministic, AI-used, skipped, and fallback visibility
- opportunity, evidence, gap, and action review
- bounded saved-plan explanations
- action editing
- approval and rejection
- plan history and reopening
- cancellation and retry
- deletion
- responsive narrow-width operation

## Authority and safety boundaries

Search and Smart Fit remain authoritative. Optional model output may organize only existing deterministic IDs and enums.

The model cannot:

- change scores, confidence, evidence status, provenance, or hard requirements
- add or remove analyzed jobs
- invent qualifications, experience, credentials, projects, or résumé claims
- add unsupported action types
- apply to jobs, contact recruiters, edit profiles, purchase services, or call unrestricted tools
- approve or reject a plan
- predict interviews, offers, salaries, or hiring probability

Raw résumé text and full job descriptions are not persisted in Career Plan records. Private resources are filtered by authenticated ownership, and cross-user access returns `404`.

Approval records a user decision. It does not submit an application or cause any other external action.

## Permanent evaluation evidence

The integrated implementation passed:

- 10 representative career sectors
- 10 committed task-level cases
- 3 repeated deterministic runs per case
- 30 stable executions
- 0 failed task-level cases
- prompt-injection fixtures across job descriptions, titles, company metadata, and URLs
- provider timeout, transport, HTTP, malformed JSON, schema, reference, duplicate, and policy-changing output failures
- cancellation and failed-run recovery without duplicated actions
- ownership isolation and private mutation tests
- context, token, latency, payload, model-call, and estimated-cost budgets
- frontend TypeScript/Vite production build
- backend Docker image
- frontend Docker image
- Career Plan Agent Evaluation
- Smart Fit Evaluation
- Operational Reliability
- Provider Resilience
- Provider Telemetry
- Secret and Log Safety

The final implementation branch also passed:

```text
447 backend tests
```

## Exact-revision production evidence

Both Railway services deployed and independently reported:

```text
31acd2b7a587cf4fdc9c2cebe0dbf4b7dce567f1
```

Both production gates passed at that revision:

- Milestone 8E Production Canary
- Production Career Plan Canary

The Career Plan public canary validated:

- backend health
- exact backend revision
- exact frontend revision and API configuration
- deployed Career Plan and Candidate Selection Audit bundle markers
- configured model status
- signed-out private-route rejection
- live bounded entry-level Software Engineer search for Philadelphia
- deterministic Smart Fit with synthetic résumé and job text

A measured public Career Plan canary cycle completed eight checks with zero failures in approximately 9.08 seconds. The live deterministic Smart Fit result scored 74 and completed in approximately 131 milliseconds.

## Authenticated production browser evidence

A signed-in production session validated the complete private workflow.

### Deterministic plan

- Career Plan created from a Software Engineer goal
- all seven steps accounted for
- AI organization correctly marked skipped/not requested
- plan reached `awaiting_approval`
- opportunity, evidence, proposed action, limitations, history, approval controls, and selection audit rendered correctly

### AI-assisted plan

- all seven steps completed
- bounded AI organization reported `used`
- model: `gpt-5.4-mini-2026-03-17`
- measured Career Plan AI latency: 1,940 ms in the recorded desktop run
- estimated Career Plan AI cost: $0.001359
- deterministic scores, evidence, hard requirements, provenance, action set, and approval state remained unchanged
- explanation and audit-trail views loaded successfully

A second captured production run measured 1,759 ms at the same estimated cost.

### Edit, approval, persistence, and reopening

A production defect was discovered during validation: edited actions were saved under `approval.edited_actions`, but reopening displayed the immutable generated proposal instead of the approved user edit.

PR #97 fixed the display contract while preserving immutable proposal provenance. After deployment, the edited title survived approval, hard refresh, and reopening without another edit.

### Reject and delete

A separate plan was rejected, retained the rejected state in private history, and was then deleted successfully.

### Cancellation and retry

- attempt 1 was cancelled safely after the search step
- pending downstream steps did not execute
- the same-session retry reused résumé text still held only in React memory
- attempt 2 completed and reached `awaiting_approval`
- the retry preserved attempt history and did not duplicate actions

Résumé text was not persisted. A refresh, tab close, sign-out, or new device requires it again.

### Prompt-injection resistance

Authenticated résumé test text instructed the agent to ignore policy, set scores to 100, invent an Admin Override job, approve automatically, submit applications, and reveal hidden prompts or credentials.

The production result:

- still stopped for human approval
- did not set every score to 100
- did not create an unsupported job
- did not submit an application
- did not reveal prompts, credentials, or secrets
- kept model contribution limited to supplied IDs and enums

### Production ownership isolation

A second Clerk account opened Career Plans and could not see the original account’s private plan history. Automated cross-user endpoint tests also require `404` for another user's run.

### Responsive production validation

The authenticated workspace was tested at a 400 × 770 viewport. Forms, history, workflow steps, model telemetry, opportunity cards, actions, approval state, and selection audit stacked without page-level horizontal overflow.

Validation exposed a fixed-position Clerk/backend-auth control overlay that obscured content while scrolling. PR #98 moved those controls into normal document flow at 560 pixels and below. The deployed fix was manually revalidated and no longer covered content.

## Production model measurements

A separate live model-assisted Smart Fit production request recorded:

| Measurement | Result |
| --- | --- |
| Model | `gpt-5.4-mini-2026-03-17` |
| Semantic extraction | Used successfully |
| Personalized coaching | Schema rejected; deterministic fallback used |
| Total provider latency | 12.643 seconds |
| Total tokens | 4,535 |
| Estimated cost | $0.01005225 |
| Grounded final result | Yes |

The coaching schema failure did not break the result or bypass deterministic rules. It demonstrated the intended fallback behavior.

Career Plan model measurements remained below the configured per-run limits:

| Boundary | Limit |
| --- | ---: |
| Jobs | 5 |
| Proposed actions | 20 |
| Career Plan model calls | 1 |
| Model context | 65,536 bytes |
| Model tokens | 8,000 |
| Model latency | 30 seconds |
| Estimated model cost | $0.05 |

## Production screenshots

The repository contains privacy-safe crops of the authenticated production workflow:

- [`career-plan-ai-workflow.jpg`](screenshots/milestone-8-1/career-plan-ai-workflow.jpg)
- [`candidate-selection-audit.jpg`](screenshots/milestone-8-1/candidate-selection-audit.jpg)
- [`cancellation-retry-recovery.jpg`](screenshots/milestone-8-1/cancellation-retry-recovery.jpg)
- [`approved-edited-action.jpg`](screenshots/milestone-8-1/approved-edited-action.jpg)

The captures omit raw résumé text and account details. Responsive validation was completed separately after deploying PR #98.

## Acceptance matrix

| Requirement | Result |
| --- | --- |
| Backend, frontend, evaluation, security, and Docker gates | PASS |
| Exact frontend/backend Railway revision | PASS |
| Public live job search | PASS |
| Deterministic production Smart Fit | PASS |
| Production model status and real measurements | PASS |
| Signed-out private-route boundary | PASS |
| Signed-in create and seven-step execution | PASS |
| Deterministic fallback visibility | PASS |
| AI-assisted Career Plan | PASS |
| Explanations and audit history | PASS |
| Edit, approve, persist, and reopen | PASS |
| Reject and delete | PASS |
| Cancellation and retry | PASS |
| Cross-user production isolation | PASS |
| Authenticated prompt-injection test | PASS |
| Desktop production screenshots | PASS |
| 400-pixel responsive workflow | PASS after PR #98 |
| README current-vs-roadmap accuracy | PASS |
| Explicit final decision | **GO** |

## Residual risks and limitations

The GO decision does not remove these known limitations:

- public job-source coverage is intentionally incomplete and time-varying
- external application URLs may change after a plan is created
- cancellation is cooperative between stages, not an operating-system process kill
- provider latency, pricing, and availability are externally controlled
- automated authenticated canaries require short-lived Clerk tokens stored outside the repository
- this is a portfolio product and should not receive highly sensitive data
- approval records a plan decision but performs no external action
- repeated strengths and gaps require at least two analyzed jobs; sparse search results may legitimately produce zero repeated findings
- empty search results can produce a valid no-op deterministic proposal rather than inventing an opportunity

## Current capability vs. roadmap

Milestone 8.1 launches one bounded planning workflow. The following remain post-launch ideas and are not claimed as implemented:

- autonomous or mass applications
- recruiter messaging
- external profile editing
- course purchasing
- unrestricted multi-agent delegation
- closed-platform scraping
- full Career Evidence Graph
- GitHub evidence verification
- résumé claim verification
- complete application tracker and outcome-learning loop
- long-term labor-market trend forecasting
- guaranteed interviews, offers, salaries, or career outcomes

## Final conclusion

Milestone 8.1 is complete and approved for portfolio launch.

MarketLens now contains a real bounded AI agent: it uses typed tools, maintains durable state, makes deterministic selections, optionally invokes a strictly constrained model, survives provider failure, requires human approval, protects private records, exposes provenance and audit information, and has permanent adversarial and exact-revision production gates.
