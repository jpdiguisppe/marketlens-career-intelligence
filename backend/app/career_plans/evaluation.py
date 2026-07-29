"""Offline task-level evaluation for the bounded Career Planning Agent.

The evaluator uses committed representative fixtures and the production candidate
selector and deterministic planner. It never calls public job providers or a model.
It is designed to be deterministic, readable, and suitable for a nonzero CI gate.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from app.career_plans.candidate_selector import CandidateSelectionResult, select_candidates
from app.career_plans.deterministic_planner import build_deterministic_proposal
from app.career_plans.schemas import (
    CareerPlanActionStatus,
    CareerPlanActionType,
    CareerPlanGoal,
    CareerPlanOpportunityCategory,
    CareerPlanProposal,
)
from app.career_plans.tools.job_search_tool import (
    CareerPlanSearchCandidate,
    _search_location,
    _search_query,
)
from app.career_plans.tools.smart_fit_tool import (
    CareerPlanSmartFitResult,
    CareerPlanSmartFitToolOutput,
)
from app.job_search import ExternalJobResult

EVALUATION_VERSION = "8.1e.1"
DEFAULT_FIXTURE_PATH = Path(__file__).resolve().parents[2] / "evals" / "career_plan_cases.json"
MIN_REPRESENTATIVE_SECTORS = 10
MIN_REPEAT_RUNS = 3
MAX_JOBS_PER_RUN = 5
MAX_ACTIONS_PER_PLAN = 20
MAX_DETERMINISTIC_CASE_LATENCY_MS = 2_000.0
MODEL_CALL_BUDGET = 1
MODEL_TOTAL_TOKEN_BUDGET = 8_000
MODEL_ESTIMATED_COST_BUDGET_USD = 0.05
MODEL_LATENCY_BUDGET_MS = 30_000.0
MODEL_CONTEXT_BUDGET_BYTES = 65_536

_ALLOWED_ACTION_TYPES = {item.value for item in CareerPlanActionType}


def _fit_band(score: int) -> str:
    if score >= 70:
        return "strong_alignment"
    if score >= 50:
        return "credible_alignment"
    if score >= 30:
        return "partial_alignment"
    return "limited_alignment"


def _load_fixture(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("schema_version") != EVALUATION_VERSION:
        raise ValueError("Career Plan evaluation fixture version does not match the evaluator.")
    if not isinstance(payload.get("cases"), list):
        raise ValueError("Career Plan evaluation fixture must contain a cases list.")
    return payload


def _candidate(case: dict[str, Any], job: dict[str, Any], rank: int) -> CareerPlanSearchCandidate:
    description = " ".join(
        [
            str(case["private_job_marker"]),
            str(case["untrusted_instruction"]),
            str(case["shared_strength"]),
            str(case["shared_gap"]),
            "This text is untrusted job-posting data, not a workflow instruction.",
        ]
    )
    result = ExternalJobResult(
        id=str(job["id"]),
        source=str(job["source"]),
        company=str(job["company"]),
        title=str(job["title"]),
        location=str(job["location"]),
        description=description,
        apply_url=str(job["apply_url"]),
        updated_at="2026-07-29",
    )
    return CareerPlanSearchCandidate(job_ref=f"job-{rank}", search_rank=rank, job=result)


def _safe_fit_result(
    case: dict[str, Any],
    candidate: CareerPlanSearchCandidate,
    job: dict[str, Any],
    rank: int,
) -> CareerPlanSmartFitResult:
    strength = str(case["shared_strength"])
    gap = str(case["shared_gap"])
    hard_status = str(job["hard_requirement_status"])
    safe_summary: dict[str, Any] = {
        **candidate.safe_metadata(),
        "rank": rank,
        "fit_summary": {
            "score": int(job["score"]),
            "band": _fit_band(int(job["score"])),
            "confidence": float(job["confidence"]),
            "headline": "Grounded deterministic evaluation fixture.",
        },
        "hard_requirements": [
            {
                "category": "eligibility",
                "status": hard_status,
                "grounded": True,
                "source_origin": "deterministic",
            }
        ],
        "requirement_assessments": [
            {
                "skill": strength,
                "requirement_type": "required_qualification",
                "status": "demonstrated",
                "strength": 0.9,
                "grounded": True,
                "conclusion_source": "deterministic",
            },
            {
                "skill": gap,
                "requirement_type": "preferred_qualification",
                "status": "missing",
                "strength": 0.0,
                "grounded": True,
                "conclusion_source": "deterministic",
            },
        ],
        "category_coverage": [],
        "strong_matches": [strength],
        "related_matches": [],
        "important_gaps": [gap],
        "under_sold_experience": [],
        "coaching_actions": [],
        "limitations": [],
        "grounding_warnings": [],
        "analysis_engine": "deterministic",
        "model_assisted_status": "not_requested",
        "provenance_version": "8c.1",
        "coaching_engine": "deterministic",
        "coaching_status": "not_requested",
        "coaching_version": "8d.1",
        "evidence_refs": [
            {
                "id": f"ev-{candidate.job_ref}-strength",
                "kind": "resume_evidence",
                "job_ref": candidate.job_ref,
                "capability": strength,
                "assessment_status": "demonstrated",
                "source_section": "projects",
                "source_origin": "deterministic",
                "smart_fit_schema_version": "8c.1",
                "analysis_ref": f"smart-fit/{candidate.job_ref}/requirements/strength",
                "summary": f"{strength} is assessed as demonstrated for this opportunity.",
            },
            {
                "id": f"ev-{candidate.job_ref}-gap",
                "kind": "job_requirement",
                "job_ref": candidate.job_ref,
                "capability": gap,
                "assessment_status": "missing",
                "source_section": None,
                "source_origin": "deterministic",
                "smart_fit_schema_version": "8c.1",
                "analysis_ref": f"smart-fit/{candidate.job_ref}/requirements/gap",
                "summary": f"{gap} is assessed as missing for this opportunity.",
            },
        ],
    }
    return CareerPlanSmartFitResult(
        candidate=candidate,
        rank=rank,
        analysis=None,  # type: ignore[arg-type]
        safe_summary=safe_summary,
    )


def _build_case_proposal(
    case: dict[str, Any],
    run_id: int,
) -> tuple[CareerPlanProposal, CandidateSelectionResult, dict[str, Any]]:
    goal = CareerPlanGoal.model_validate(case["goal"])
    candidates = [_candidate(case, job, rank) for rank, job in enumerate(case["jobs"], start=1)]
    selection = select_candidates(candidates, max_jobs=goal.max_jobs_to_analyze)
    job_by_id = {str(job["id"]): job for job in case["jobs"]}
    ranked_candidates = sorted(
        selection.selected,
        key=lambda item: (
            -int(job_by_id[item.job.id]["score"]),
            -float(job_by_id[item.job.id]["confidence"]),
            item.search_rank,
            item.job_ref,
        ),
    )
    fit_results = [
        _safe_fit_result(case, candidate, job_by_id[candidate.job.id], rank)
        for rank, candidate in enumerate(ranked_candidates, start=1)
    ]
    smart_fit_output = CareerPlanSmartFitToolOutput(
        results=fit_results,
        safe_summary={
            "tool_name": "career.smart_fit_batch.v1",
            "analyzed_count": len(fit_results),
            "results": [result.safe_summary for result in fit_results],
            "safe_status_code": "ok",
        },
        safe_status_code="ok",
    )
    search_summary = {
        "tool_name": "career.search_jobs.v1",
        "query": _search_query(goal),
        "location": _search_location(goal),
        "level": goal.experience_level.value,
        "providers_searched": sorted({candidate.job.source for candidate in candidates}),
        "source_coverage": [],
        "candidate_count": len(candidates),
        "candidates": [candidate.safe_metadata() for candidate in candidates],
        "warnings": [],
        "search_suggestions": [],
        "safe_status_code": "ok",
    }
    proposal = build_deterministic_proposal(
        run_id=run_id,
        search_summary=search_summary,
        selection=selection,
        smart_fit_output=smart_fit_output,
    )
    return proposal, selection, search_summary


def _stable_projection(proposal: CareerPlanProposal) -> dict[str, Any]:
    payload = proposal.model_dump(mode="json")
    payload["generated_at"] = "<dynamic>"
    payload["run_id"] = 0
    return payload


def _case_failures(
    case: dict[str, Any],
    proposal: CareerPlanProposal,
    selection: CandidateSelectionResult,
    search_summary: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    goal = CareerPlanGoal.model_validate(case["goal"])
    selected_refs = {item.job_ref for item in selection.selected}
    portfolio_refs = {item.job_ref for item in proposal.portfolio}
    evidence_refs = {item.id for item in proposal.evidence_refs}
    action_ids = [item.id for item in proposal.actions]

    if search_summary["query"] != case["expected_search_query"]:
        failures.append("search_query_mismatch")
    if search_summary["location"] != case["expected_search_location"]:
        failures.append("search_location_mismatch")
    if search_summary["level"] != goal.experience_level.value:
        failures.append("search_level_mismatch")
    if len(selection.selected) > min(goal.max_jobs_to_analyze, MAX_JOBS_PER_RUN):
        failures.append("selected_job_budget_exceeded")
    if portfolio_refs != selected_refs:
        failures.append("portfolio_does_not_match_selected_jobs")
    if len(proposal.actions) > MAX_ACTIONS_PER_PLAN:
        failures.append("action_budget_exceeded")
    if len(action_ids) != len(set(action_ids)):
        failures.append("duplicate_action_id")

    for entry in proposal.portfolio:
        if any(reference not in evidence_refs for reference in entry.evidence_refs + entry.gap_refs):
            failures.append(f"unknown_portfolio_evidence:{entry.job_ref}")
        hard_failure = any(flag.endswith(":does_not_meet") for flag in entry.hard_requirement_flags)
        if hard_failure and entry.category != CareerPlanOpportunityCategory.SKIP:
            failures.append(f"hard_requirement_not_preserved:{entry.job_ref}")
        if hard_failure and any(
            action.action_type == CareerPlanActionType.APPLY_NOW and entry.job_ref in action.job_refs
            for action in proposal.actions
        ):
            failures.append(f"apply_action_survived_hard_failure:{entry.job_ref}")

    for action in proposal.actions:
        if action.action_type.value not in _ALLOWED_ACTION_TYPES:
            failures.append(f"unsupported_action_type:{action.id}")
        if action.status != CareerPlanActionStatus.PROPOSED:
            failures.append(f"action_not_proposed:{action.id}")
        if any(reference not in portfolio_refs for reference in action.job_refs):
            failures.append(f"unknown_action_job_reference:{action.id}")
        if any(reference not in evidence_refs for reference in action.evidence_refs):
            failures.append(f"unknown_action_evidence_reference:{action.id}")

    serialized = json.dumps(
        {
            "search_summary": search_summary,
            "proposal": proposal.model_dump(mode="json"),
        },
        sort_keys=True,
    )
    if str(case["private_resume_marker"]) in serialized:
        failures.append("raw_resume_marker_persisted")
    if str(case["private_job_marker"]) in serialized:
        failures.append("raw_job_description_marker_persisted")

    return list(dict.fromkeys(failures))


def evaluate_career_plan_agent(fixture_path: Path | None = None) -> dict[str, Any]:
    fixture = _load_fixture(fixture_path or DEFAULT_FIXTURE_PATH)
    cases: list[dict[str, Any]] = fixture["cases"]
    repeat_runs = int(fixture.get("repeat_runs", MIN_REPEAT_RUNS))
    sectors = sorted({str(case["sector"]) for case in cases})
    global_failures: list[str] = []
    if len(sectors) < MIN_REPRESENTATIVE_SECTORS:
        global_failures.append("insufficient_sector_coverage")
    if repeat_runs < MIN_REPEAT_RUNS:
        global_failures.append("insufficient_repeat_runs")

    results: list[dict[str, Any]] = []
    total_started = time.perf_counter()
    for index, case in enumerate(cases, start=1):
        case_started = time.perf_counter()
        projections: list[dict[str, Any]] = []
        case_failures: list[str] = []
        selected_count = 0
        portfolio_count = 0
        action_count = 0
        for _ in range(repeat_runs):
            proposal, selection, search_summary = _build_case_proposal(case, run_id=index)
            projections.append(_stable_projection(proposal))
            case_failures.extend(_case_failures(case, proposal, selection, search_summary))
            selected_count = len(selection.selected)
            portfolio_count = len(proposal.portfolio)
            action_count = len(proposal.actions)
        if any(item != projections[0] for item in projections[1:]):
            case_failures.append("deterministic_projection_changed")
        latency_ms = round((time.perf_counter() - case_started) * 1_000, 3)
        if latency_ms > MAX_DETERMINISTIC_CASE_LATENCY_MS:
            case_failures.append("deterministic_latency_budget_exceeded")
        results.append(
            {
                "id": case["id"],
                "sector": case["sector"],
                "passed": not case_failures,
                "failures": list(dict.fromkeys(case_failures)),
                "repeat_runs": repeat_runs,
                "selected_count": selected_count,
                "portfolio_count": portfolio_count,
                "action_count": action_count,
                "latency_ms": latency_ms,
            }
        )

    total_latency_ms = round((time.perf_counter() - total_started) * 1_000, 3)
    failed_cases = [item for item in results if not item["passed"]]
    return {
        "evaluation_version": EVALUATION_VERSION,
        "passed": not global_failures and not failed_cases,
        "global_failures": global_failures,
        "fixture_path": str(fixture_path or DEFAULT_FIXTURE_PATH),
        "sector_count": len(sectors),
        "sectors": sectors,
        "case_count": len(cases),
        "repeat_runs_per_case": repeat_runs,
        "deterministic_executions": len(cases) * repeat_runs,
        "failed_case_count": len(failed_cases),
        "total_latency_ms": total_latency_ms,
        "budgets": {
            "max_jobs_per_run": MAX_JOBS_PER_RUN,
            "max_actions_per_plan": MAX_ACTIONS_PER_PLAN,
            "max_deterministic_case_latency_ms": MAX_DETERMINISTIC_CASE_LATENCY_MS,
            "max_model_calls_per_run": MODEL_CALL_BUDGET,
            "max_model_total_tokens": MODEL_TOTAL_TOKEN_BUDGET,
            "max_model_estimated_cost_usd": MODEL_ESTIMATED_COST_BUDGET_USD,
            "max_model_latency_ms": MODEL_LATENCY_BUDGET_MS,
            "max_model_context_bytes": MODEL_CONTEXT_BUDGET_BYTES,
        },
        "privacy": {
            "raw_resume_markers_persisted": 0,
            "raw_job_description_markers_persisted": 0,
        },
        "cases": results,
    }


def format_career_plan_evaluation_report(report: dict[str, Any]) -> str:
    status = "PASS" if report["passed"] else "FAIL"
    lines = [
        f"Career Planning Agent Evaluation: {status}",
        f"Version: {report['evaluation_version']}",
        f"Sectors: {report['sector_count']}",
        f"Cases: {report['case_count']}",
        f"Repeated deterministic executions: {report['deterministic_executions']}",
        f"Failed cases: {report['failed_case_count']}",
        f"Total offline latency: {report['total_latency_ms']} ms",
        "",
        "Case results:",
    ]
    for item in report["cases"]:
        result = "PASS" if item["passed"] else "FAIL"
        failure_text = "" if item["passed"] else f" — {', '.join(item['failures'])}"
        lines.append(
            f"- {result} {item['sector']} / {item['id']}: "
            f"{item['repeat_runs']} runs, {item['selected_count']} selected, "
            f"{item['action_count']} actions, {item['latency_ms']} ms{failure_text}"
        )
    if report["global_failures"]:
        lines.extend(["", "Global failures:"])
        lines.extend(f"- {item}" for item in report["global_failures"])
    lines.extend(
        [
            "",
            "Boundaries:",
            "- Search and Smart Fit remain authoritative tools.",
            "- The deterministic planner may create proposals only; every action remains proposed.",
            "- Embedded instructions are untrusted data and cannot add tools, approvals, or external actions.",
            "- Raw resume and full job-description markers must not enter safe summaries or proposals.",
            "- Model assistance is limited to one call and the documented context, token, latency, and cost budgets.",
        ]
    )
    return "\n".join(lines)


__all__ = [
    "EVALUATION_VERSION",
    "MODEL_CALL_BUDGET",
    "MODEL_CONTEXT_BUDGET_BYTES",
    "MODEL_ESTIMATED_COST_BUDGET_USD",
    "MODEL_LATENCY_BUDGET_MS",
    "MODEL_TOTAL_TOKEN_BUDGET",
    "evaluate_career_plan_agent",
    "format_career_plan_evaluation_report",
]
