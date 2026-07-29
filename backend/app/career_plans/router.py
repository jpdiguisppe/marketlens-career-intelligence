from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import AuthenticatedUser, get_current_user
from app.career_plans.models import CareerPlanAuditEventDB, CareerPlanRunDB
from app.career_plans.orchestrator import execute_career_plan
from app.career_plans.runtime import (
    append_audit_event as _append_audit_event,
    get_owned_run as _get_owned_run,
    safe_conflict as _safe_conflict,
    utcnow as _utcnow,
    validate_safe_audit_payload as _validate_safe_audit_payload,
)
from app.career_plans.schemas import (
    CAREER_PLAN_SCHEMA_VERSION,
    CareerPlanAuditEventResponse,
    CareerPlanCreate,
    CareerPlanDecisionRequest,
    CareerPlanExecuteRequest,
    CareerPlanGoal,
    CareerPlanRunResponse,
    CareerPlanRunStatus,
    CareerPlanRunSummary,
    CareerPlanStepName,
    CareerPlanStepResponse,
)
from app.career_plans.state_machine import InvalidCareerPlanTransition, ensure_run_transition
from app.database import get_db

router = APIRouter(prefix="/career-plans", tags=["career-plans"])


def _to_step_response(step: Any) -> CareerPlanStepResponse:
    return CareerPlanStepResponse(
        id=step.id,
        step_name=step.step_name,
        status=step.status,
        attempt=step.attempt,
        safe_output_summary=step.safe_output_summary,
        safe_error_code=step.safe_error_code,
        started_at=step.started_at,
        completed_at=step.completed_at,
        latency_ms=step.latency_ms,
    )


def _to_audit_response(event: CareerPlanAuditEventDB) -> CareerPlanAuditEventResponse:
    return CareerPlanAuditEventResponse(
        id=event.id,
        sequence_number=event.sequence_number,
        event_type=event.event_type,
        safe_payload=event.safe_payload,
        created_at=event.created_at,
    )


def _to_summary(run: CareerPlanRunDB) -> CareerPlanRunSummary:
    return CareerPlanRunSummary(
        id=run.id,
        status=run.status,
        current_step=CareerPlanStepName(run.current_step) if run.current_step else None,
        schema_version=run.schema_version,
        run_version=run.run_version,
        attempt_count=run.attempt_count,
        goal=CareerPlanGoal.model_validate(run.goal),
        fallback_status=run.fallback_status,
        safe_error_code=run.safe_error_code,
        resume_required_to_resume=run.resume_required_to_resume,
        cancel_requested_at=run.cancel_requested_at,
        created_at=run.created_at,
        updated_at=run.updated_at,
        completed_at=run.completed_at,
    )


def _to_response(run: CareerPlanRunDB) -> CareerPlanRunResponse:
    summary = _to_summary(run)
    return CareerPlanRunResponse(
        **summary.model_dump(),
        search_summary=run.search_summary,
        proposal=run.proposal,
        approval=run.approval,
        steps=[_to_step_response(step) for step in run.steps],
        audit_events=[_to_audit_response(event) for event in run.audit_events],
    )


@router.post("", response_model=CareerPlanRunResponse, status_code=status.HTTP_201_CREATED)
def create_career_plan(
    request: CareerPlanCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CareerPlanRunResponse:
    if request.idempotency_key:
        existing = (
            db.query(CareerPlanRunDB)
            .filter(
                CareerPlanRunDB.user_id == current_user.user_id,
                CareerPlanRunDB.idempotency_key == request.idempotency_key,
            )
            .one_or_none()
        )
        if existing is not None:
            return _to_response(existing)

    run = CareerPlanRunDB(
        user_id=current_user.user_id,
        idempotency_key=request.idempotency_key,
        status=CareerPlanRunStatus.DRAFT.value,
        schema_version=CAREER_PLAN_SCHEMA_VERSION,
        goal_json="{}",
        search_summary_json="{}",
        proposal_json="{}",
        approval_json="{}",
    )
    run.goal = request.goal.model_dump(mode="json")
    try:
        db.add(run)
        db.flush()
        _append_audit_event(
            db,
            run,
            "run_created",
            {
                "status": CareerPlanRunStatus.DRAFT.value,
                "schema_version": CAREER_PLAN_SCHEMA_VERSION,
                "run_version": 1,
            },
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        if not request.idempotency_key:
            raise
        existing = (
            db.query(CareerPlanRunDB)
            .filter(
                CareerPlanRunDB.user_id == current_user.user_id,
                CareerPlanRunDB.idempotency_key == request.idempotency_key,
            )
            .one_or_none()
        )
        if existing is None:
            raise
        return _to_response(existing)

    db.refresh(run)
    return _to_response(run)


@router.get("", response_model=list[CareerPlanRunSummary])
def list_career_plans(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CareerPlanRunSummary]:
    runs = (
        db.query(CareerPlanRunDB)
        .filter(CareerPlanRunDB.user_id == current_user.user_id)
        .order_by(CareerPlanRunDB.created_at.desc(), CareerPlanRunDB.id.desc())
        .all()
    )
    return [_to_summary(run) for run in runs]


@router.get("/{run_id}", response_model=CareerPlanRunResponse)
def get_career_plan(
    run_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CareerPlanRunResponse:
    return _to_response(_get_owned_run(db, run_id, current_user.user_id))


@router.post("/{run_id}/execute", response_model=CareerPlanRunResponse)
def execute_or_resume_career_plan(
    run_id: int,
    request: CareerPlanExecuteRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CareerPlanRunResponse:
    run = _get_owned_run(db, run_id, current_user.user_id)
    return _to_response(execute_career_plan(db, run, request))


@router.post("/{run_id}/cancel", response_model=CareerPlanRunResponse)
def request_career_plan_cancellation(
    run_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CareerPlanRunResponse:
    run = _get_owned_run(db, run_id, current_user.user_id)
    if run.status != CareerPlanRunStatus.RUNNING.value:
        raise _safe_conflict("run_not_active", "Only a running Career Plan can be cancelled.")
    if run.cancel_requested_at is None:
        run.cancel_requested_at = _utcnow()
        run.run_version += 1
        _append_audit_event(
            db,
            run,
            "cancellation_requested",
            {"status": run.status, "run_version": run.run_version},
        )
        db.commit()
        db.refresh(run)
    return _to_response(run)


@router.post("/{run_id}/decision", response_model=CareerPlanRunResponse)
def decide_career_plan(
    run_id: int,
    request: CareerPlanDecisionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CareerPlanRunResponse:
    run = _get_owned_run(db, run_id, current_user.user_id)
    if run.status != CareerPlanRunStatus.AWAITING_APPROVAL.value:
        raise _safe_conflict(
            "run_not_awaiting_approval",
            "The Career Plan does not currently have a proposal awaiting approval.",
        )

    target_status = CareerPlanRunStatus(request.decision.value)
    try:
        ensure_run_transition(run.status, target_status)
    except InvalidCareerPlanTransition as exc:
        raise _safe_conflict("invalid_run_transition", str(exc)) from exc

    run.approval = {
        "decision": request.decision.value,
        "edited_actions": [action.model_dump(mode="json") for action in request.edited_actions],
        "decided_at": _utcnow().isoformat(),
    }
    run.status = target_status.value
    run.completed_at = _utcnow()
    run.run_version += 1
    _append_audit_event(
        db,
        run,
        "plan_decided",
        {
            "decision": request.decision.value,
            "edited_action_count": len(request.edited_actions),
            "run_version": run.run_version,
        },
    )
    db.commit()
    db.refresh(run)
    return _to_response(run)


@router.delete("/{run_id}")
def delete_career_plan(
    run_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    run = _get_owned_run(db, run_id, current_user.user_id)
    db.delete(run)
    db.commit()
    return {"status": "deleted"}
