# Milestone 8 Kickoff — Optional AI-Assisted Analysis

Milestone 8 begins after completion of Milestone 7.1 search-correctness hardening.

## Goal

Improve Smart Fit with optional model-assisted semantic analysis while preserving the deterministic system as a safe, fully functional fallback.

This milestone is not a chatbot integration. Model assistance must be evidence-grounded, measurable, privacy-conscious, observable, and bounded by structured outputs and failure-safe behavior.

## Planned sequence

### 8A — Evaluation foundation

- create representative resume/job pairs across career sectors and experience levels
- define expected required and preferred qualifications
- define acceptable resume evidence and genuine gaps
- evaluate deterministic extraction and matching as the baseline
- add metrics and critical cases that cannot be silently removed

### 8B — Semantic requirement extraction

- distinguish required, preferred, credential, experience, responsibility, tool, domain, and implied-capability requirements
- use structured model output with schema validation
- retain deterministic extraction when model assistance is unavailable or invalid

### 8C — Evidence-grounded matching

- connect each coverage or gap conclusion to specific resume and job-description evidence
- prohibit unsupported strengths, experience, credentials, or skills
- preserve deterministic scoring boundaries where they are safer

### 8D — Personalized coaching

- explain which gaps matter most
- distinguish wording fixes from actual experience or learning gaps
- suggest targeted resume, project, coursework, and application actions

### 8E — Reliability and operations

- model-status transparency
- timeout, retry, and deterministic fallback behavior
- prompt and schema versioning
- cost and latency measurements
- model-versus-baseline evaluation reports
- redaction and backend-only provider credentials

### 8.1 — Career Planning Agent

After the analysis layer is reliable, add a tool-calling workflow that can:

1. search for jobs
2. select promising opportunities
3. run Smart Fit
4. identify repeated gaps
5. produce a prioritized application and learning plan
6. preserve workflow state
7. expose an audit trail
8. require human approval before consequential actions

The agent phase must reuse tested MarketLens tools rather than bypassing product logic with an unrestricted chatbot.

## Completion principles

- no provider key in the frontend
- no model dependency for core functionality
- no unsupported claims presented as evidence
- no raw resume or job-description persistence merely because a model was used
- no AI feature accepted without deterministic fallback and evaluation coverage
