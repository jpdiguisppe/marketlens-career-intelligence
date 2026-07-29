from __future__ import annotations

import hashlib
import json
import time
from typing import Callable

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.career_plans.candidate_selector import CandidateSelectionResult, select_candidates
from app.career_plans.deterministic_planner import build_deterministic_proposal
from app.career_plans.models import CareerPlanRunDB, CareerPlanStepDB
from app.career_plans.runtime import append_audit_event, safe_conflict, utcnow
from app.career_plans.schemas import (
    CAREER_PLAN_SCHEMA_VERSION,
    CareerPlanExecuteRequest,
    CareerPlanGoal,
    CareerPlanRunStatus,
    CareerPlanStepName,
    CareerPlanStepStatus,
)
from app.career_plans.state_machine import InvalidCareerPlanTransition, ensure_run_transition
from app.career_plans.tools.job_search_tool import (
    CareerPlanSearchCandidate,
    CareerPlanSearchToolOutput,
    run_job_search_tool,
)
from app.career_plans.tools.smart_fit_tool import (
    CareerPlanSmartFitToolError,
    CareerPlanSmartFitToolOutput,
    run_smart_fit_tool,
)


def _input_fingerprint(goal: CareerPlanGoal, resume_text: str) -> str:
    payload = json.dumps(goal.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256()
    digest.update(CAREER_PLAN_SCHEMA_VERSION.encode("utf-8"))
    digest.update(b"\0")
    digest.update(payload.encode("utf-8"))
    digest.update(b"\0")
    digest.update(resume_text.encode("utf-8"))
    return digest.hexdigest()


def _begin_execution(
    db: Session,
    run: CareerPlanRunDB,
    request: CareerPlanExecuteRequest,
    fingerprint: str,
) -> CareerPlanRunDB:
    if run.resume_fingerprint == fingerprint and run.status in {
        CareerPlanRunStatus.AWAITING_APPROVAL.value,
        CareerPlanRunStatus.APPROVED.value,
        CareerPlanRunStatus.REJECTED.value,
    }:
        return run

    if run.run_version != request.expected_run_version:
        raise safe_conflict("stale_run_version", "The Career Plan changed before this execution request.")
    if run.status == CareerPlanRunStatus.RUNNING.value:
        raise safe_conflict("run_already_active", "This Career Plan already has an active execution.")
    if run.status in {CareerPlanRunStatus.APPROVED.value, CareerPlanRunStatus.REJECTED.value}:
        raise safe_conflict("run_terminal", "A decided Career Plan cannot be executed again.")

    try:
        ensure_run_transition(run.status, CareerPlanRunStatus.RUNNING)
    except InvalidCareerPlanTransition as exc:
        raise safe_conflict("invalid_run_transition", str(exc)) from exc

    allowed_statuses = {
        CareerPlanRunStatus.DRAFT.value,
        CareerPlanRunStatus.FAILED.value,
        CareerPlanRunStatus.CANCELLED.value,
        CareerPlanRunStatus.AWAITING_APPROVAL.value,
    }
    updated = (
        db.query(CareerPlanRunDB)
        .filter(
            CareerPlanRunDB.id == run.id,
            CareerPlanRunDB.user_id == run.user_id,
            CareerPlanRunDB.run_version == request.expected_run_version,
            CareerPlanRunDB.status.in_(allowed_statuses),
        )
        .update(
            {
                CareerPlanRunDB.status: CareerPlanRunStatus.RUNNING.value,
                CareerPlanRunDB.current_step: CareerPlanStepName.VALIDATE_INPUT.value,
                CareerPlanRunDB.schema_version: CAREER_PLAN_SCHEMA_VERSION,
                CareerPlanRunDB.run_version: CareerPlanRunDB.run_version + 1,
                CareerPlanRunDB.attempt_count: CareerPlanRunDB.attempt_count + 1,
                CareerPlanRunDB.proposal_json: "{}",
                CareerPlanRunDB.approval_json: "{}",
                CareerPlanRunDB.fallback_status: "deterministic_pending",
                CareerPlanRunDB.safe_error_code: None,
                CareerPlanRunDB.resume_fingerprint: fingerprint,
                CareerPlanRunDB.resume_required_to_resume: True,
                CareerPlanRunDB.cancel_requested_at: None,
                CareerPlanRunDB.completed_at: None,
            },
            synchronize_session=False,
        )
    )
    if updated != 1:
        db.rollback()
        raise safe_conflict("run_already_active", "This Career Plan was started by another request.")
    db.commit()
    db.refresh(run)
    append_audit_event(
        db,
        run,
        "execution_started",
        {
            "attempt": run.attempt_count,
            "run_version": run.run_version,
            "workflow_schema_version": CAREER_PLAN_SCHEMA_VERSION,
            "input_fingerprint_prefix": fingerprint[:12],
        },
    )
    db.commit()
    db.refresh(run)
    return run


def _begin_step(
    db: Session,
    run: CareerPlanRunDB,
    step_name: CareerPlanStepName,
    input_fingerprint: str,
) -> tuple[CareerPlanStepDB, float]:
    run.current_step = step_name.value
    run.run_version += 1
    step = CareerPlanStepDB(
        run_id=run.id,
        step_name=step_name.value,
        status=CareerPlanStepStatus.RUNNING.value,
        attempt=run.attempt_count,
        input_fingerprint=input_fingerprint,
        safe_output_summary_json="{}",
        started_at=utcnow(),
        latency_ms=0.0,
    )
    db.add(step)
    append_audit_event(
        db,
        run,
        "step_started",
        {"step": step_name.value, "attempt": run.attempt_count, "run_version": run.run_version},
    )
    db.commit()
    db.refresh(step)
    db.refresh(run)
    return step, time.perf_counter()


def _complete_step(
    db: Session,
    run: CareerPlanRunDB,
    step: CareerPlanStepDB,
    started_at: float,
    safe_summary: dict[str, object],
    status: CareerPlanStepStatus = CareerPlanStepStatus.COMPLETED,
) -> None:
    step.status = status.value
    step.safe_output_summary = safe_summary
    step.completed_at = utcnow()
    step.latency_ms = round((time.perf_counter() - started_at) * 1_000, 3)
    run.run_version += 1
    append_audit_event(
        db,
        run,
        "step_finished",
        {
            "step": step.step_name,
            "step_status": step.status,
            "attempt": step.attempt,
            "latency_ms": step.latency_ms,
            "run_version": run.run_version,
        },
    )
    db.commit()
    db.refresh(run)


def _fail_active_step(
    db: Session,
    run: CareerPlanRunDB,
    step: CareerPlanStepDB | None,
    started_at: float | None,
    safe_code: str,
) -> CareerPlanRunDB:
    if step is not None:
        step.status = CareerPlanStepStatus.FAILED.value
        step.safe_error_code = safe_code
        step.completed_at = utcnow()
        if started_at is not None:
            step.latency_ms = round((time.perf_counter() - started_at) * 1_000, 3)
    run.status = CareerPlanRunStatus.FAILED.value
    run.safe_error_code = safe_code
    run.resume_required_to_resume = True
    run.completed_at = utcnow()
    run.run_version += 1
    append_audit_event(
        db,
        run,
        "execution_failed",
        {
            "safe_error_code": safe_code,
            "attempt": run.attempt_count,
            "step": step.step_name if step is not None else run.current_step,
            "run_version": run.run_version,
        },
    )
    db.commit()
    db.refresh(run)
    return run


def _cancel_if_requested(
    db: Session,
    run: CareerPlanRunDB,
    step: CareerPlanStepDB | None = None,
    started_at: float | None = None,
) -> bool:
    db.expire(run)
    db.refresh(run)
    if run.cancel_requested_at is None:
        return False
    if step is not None and step.status == CareerPlanStepStatus.RUNNING.value:
        step.status = CareerPlanStepStatus.CANCELLED.value
        step.safe_error_code = "cancelled_by_user"
        step.completed_at = utcnow()
        if started_at is not None:
            step.latency_ms = round((time.perf_counter() - started_at) * 1_000, 3)
    run.status = CareerPlanRunStatus.CANCELLED.value
    run.safe_error_code = "cancelled_by_user"
    run.resume_required_to_resume = True
    run.completed_at = utcnow()
    run.run_version += 1
    append_audit_event(
        db,
        run,
        "execution_cancelled",
        {
            "attempt": run.attempt_count,
            "step": step.step_name if step is not None else run.current_step,
            "run_version": run.run_version,
        },
    )
    db.commit()
    db.refresh(run)
    return True


def execute_career_plan(
    db: Session,
    run: CareerPlanRunDB,
    request: CareerPlanExecuteRequest,
    search_tool: Callable[[CareerPlanGoal], CareerPlanSearchToolOutput] | None = None,
    smart_fit_tool: Callable[[str, list[CareerPlanSearchCandidate]], CareerPlanSmartFitToolOutput] | None = None,
) -> CareerPlanRunDB:
    search_tool_fn = search_tool or run_job_search_tool
    smart_fit_tool_fn = smart_fit_tool or run_smart_fit_tool
    goal = CareerPlanGoal.model_validate(run.goal)
    fingerprint = _input_fingerprint(goal, request.resume_text)
    run = _begin_execution(db, run, request, fingerprint)
    if run.resume_fingerprint == fingerprint and run.status in {
        CareerPlanRunStatus.AWAITING_APPROVAL.value,
        CareerPlanRunStatus.APPROVED.value,
        CareerPlanRunStatus.REJECTED.value,
    }:
        return run

    active_step: CareerPlanStepDB | None = None
    step_started: float | None = None
    try:
        active_step, step_started = _begin_step(db, run, CareerPlanStepName.VALIDATE_INPUT, fingerprint)
        _complete_step(
            db,
            run,
            active_step,
            step_started,
            {
                "target_occupation": goal.target_occupation,
                "experience_level": goal.experience_level.value,
                "location_present": bool(goal.location),
                "industry_present": bool(goal.industry),
                "max_jobs_to_analyze": goal.max_jobs_to_analyze,
                "model_assisted_planning_requested": goal.model_assisted_planning,
            },
        )
        if _cancel_if_requested(db, run):
            return run

        active_step, step_started = _begin_step(db, run, CareerPlanStepName.SEARCH_JOBS, fingerprint)
        search_output = search_tool_fn(goal)
        run.search_summary = search_output.safe_summary
        _complete_step(db, run, active_step, step_started, search_output.safe_summary)
        if _cancel_if_requested(db, run):
            return run

        active_step, step_started = _begin_step(db, run, CareerPlanStepName.SELECT_CANDIDATES, fingerprint)
        selection: CandidateSelectionResult = select_candidates(
            search_output.candidates,
            max_jobs=goal.max_jobs_to_analyze,
        )
        _complete_step(db, run, active_step, step_started, selection.safe_summary())
        if _cancel_if_requested(db, run):
            return run

        active_step, step_started = _begin_step(db, run, CareerPlanStepName.ANALYZE_SMART_FIT, fingerprint)
        smart_fit_output = smart_fit_tool_fn(request.resume_text, selection.selected)
        _complete_step(
            db,
            run,
            active_step,
            step_started,
            smart_fit_output.safe_summary,
            status=CareerPlanStepStatus.COMPLETED if selection.selected else CareerPlanStepStatus.SKIPPED,
        )
        if _cancel_if_requested(db, run):
            return run

        active_step, step_started = _begin_step(
            db, run, CareerPlanStepName.SYNTHESIZE_DETERMINISTIC_PLAN, fingerprint
        )
        proposal = build_deterministic_proposal(
            run_id=run.id,
            search_summary=search_output.safe_summary,
            selection=selection,
            smart_fit_output=smart_fit_output,
        )
        if goal.model_assisted_planning:
            proposal = proposal.model_copy(
                update={
                    "warnings": (
                        proposal.warnings
                        + [
                            "Model-assisted planning was requested but is not part of this deterministic implementation slice; the complete deterministic proposal was preserved."
                        ]
                    )[:30]
                }
            )
        run.proposal = proposal.model_dump(mode="json")
        run.fallback_status = proposal.fallback_status
        _complete_step(
            db,
            run,
            active_step,
            step_started,
            {
                "proposal_status": proposal.proposal_status,
                "portfolio_count": len(proposal.portfolio),
                "recurring_strength_count": len(proposal.recurring_strengths),
                "recurring_gap_count": len(proposal.recurring_gaps),
                "action_count": len(proposal.actions),
                "proposal_engine": proposal.proposal_engine,
            },
        )
        if _cancel_if_requested(db, run):
            return run

        active_step, step_started = _begin_step(db, run, CareerPlanStepName.ENHANCE_PLAN_OPTIONAL, fingerprint)
        _complete_step(
            db,
            run,
            active_step,
            step_started,
            {
                "requested": goal.model_assisted_planning,
                "used": False,
                "status": "deferred_to_milestone_8_1c" if goal.model_assisted_planning else "not_requested",
            },
            status=CareerPlanStepStatus.SKIPPED,
        )
        if _cancel_if_requested(db, run):
            return run

        active_step, step_started = _begin_step(db, run, CareerPlanStepName.FINALIZE_PROPOSAL, fingerprint)
        run.status = CareerPlanRunStatus.AWAITING_APPROVAL.value
        run.safe_error_code = None
        run.resume_required_to_resume = False
        run.completed_at = None
        run.current_step = CareerPlanStepName.FINALIZE_PROPOSAL.value
        _complete_step(
            db,
            run,
            active_step,
            step_started,
            {
                "status": CareerPlanRunStatus.AWAITING_APPROVAL.value,
                "proposal_status": proposal.proposal_status,
                "fallback_status": proposal.fallback_status,
            },
        )
        append_audit_event(
            db,
            run,
            "proposal_ready",
            {
                "status": run.status,
                "proposal_status": proposal.proposal_status,
                "portfolio_count": len(proposal.portfolio),
                "action_count": len(proposal.actions),
                "attempt": run.attempt_count,
                "run_version": run.run_version,
            },
        )
        db.commit()
        db.refresh(run)
        return run
    except HTTPException:
        db.rollback()
        raise
    except CareerPlanSmartFitToolError as exc:
        return _fail_active_step(db, run, active_step, step_started, exc.safe_code)
    except ValueError:
        return _fail_active_step(db, run, active_step, step_started, "invalid_input")
    except Exception as exc:
        return _fail_active_step(
            db,
            run,
            active_step,
            step_started,
            str(getattr(exc, "safe_code", "internal_error")),
        )
