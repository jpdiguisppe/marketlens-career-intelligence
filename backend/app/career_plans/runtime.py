from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.career_plans.models import CareerPlanAuditEventDB, CareerPlanRunDB

MAX_AUDIT_EVENTS_PER_RUN = 100
MAX_SAFE_AUDIT_PAYLOAD_CHARACTERS = 4_000
_FORBIDDEN_AUDIT_KEY_PARTS = {
    "resume",
    "description",
    "document",
    "quote",
    "authorization",
    "token",
    "secret",
    "api_key",
    "database_url",
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def safe_conflict(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=409, detail={"code": code, "message": message})


def get_owned_run(db: Session, run_id: int, user_id: str) -> CareerPlanRunDB:
    run = (
        db.query(CareerPlanRunDB)
        .filter(CareerPlanRunDB.id == run_id, CareerPlanRunDB.user_id == user_id)
        .one_or_none()
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Career Plan run not found.")
    return run


def validate_safe_audit_payload(payload: dict[str, Any]) -> None:
    serialized = str(payload)
    if len(serialized) > MAX_SAFE_AUDIT_PAYLOAD_CHARACTERS:
        raise safe_conflict("audit_payload_too_large", "The audit payload exceeds the safe size limit.")

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                normalized_key = str(key).strip().lower()
                if any(part in normalized_key for part in _FORBIDDEN_AUDIT_KEY_PARTS):
                    raise safe_conflict(
                        "unsafe_audit_payload",
                        "Audit payloads may contain only safe IDs, counts, statuses, reason codes, and versions.",
                    )
                visit(nested)
        elif isinstance(value, list):
            for nested in value:
                visit(nested)
        elif not isinstance(value, (str, int, float, bool, type(None))):
            raise safe_conflict("unsafe_audit_payload", "Audit payload values must be JSON-safe primitives.")

    visit(payload)


def append_audit_event(
    db: Session,
    run: CareerPlanRunDB,
    event_type: str,
    safe_payload: dict[str, Any],
) -> None:
    validate_safe_audit_payload(safe_payload)
    event_count = (
        db.query(func.count(CareerPlanAuditEventDB.id))
        .filter(CareerPlanAuditEventDB.run_id == run.id)
        .scalar()
        or 0
    )
    if event_count >= MAX_AUDIT_EVENTS_PER_RUN:
        raise safe_conflict("audit_limit_reached", "The Career Plan audit-event limit was reached.")

    last_sequence = (
        db.query(func.max(CareerPlanAuditEventDB.sequence_number))
        .filter(CareerPlanAuditEventDB.run_id == run.id)
        .scalar()
        or 0
    )
    event = CareerPlanAuditEventDB(
        run=run,
        sequence_number=last_sequence + 1,
        event_type=event_type,
        safe_payload_json="{}",
    )
    event.safe_payload = safe_payload
    db.add(event)
