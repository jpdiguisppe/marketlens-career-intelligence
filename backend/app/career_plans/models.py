from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _load_object(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


class CareerPlanRunDB(Base):
    __tablename__ = "career_plan_runs"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_career_plan_user_idempotency"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft", index=True)
    current_step: Mapped[str | None] = mapped_column(String(80), nullable=True)
    schema_version: Mapped[str] = mapped_column(String(40), nullable=False, default="8.1.1")
    run_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    goal_json: Mapped[str] = mapped_column(Text, nullable=False)
    search_summary_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    proposal_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    approval_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    fallback_status: Mapped[str] = mapped_column(String(80), nullable=False, default="not_requested")
    safe_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    resume_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resume_required_to_resume: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    steps: Mapped[list[CareerPlanStepDB]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="CareerPlanStepDB.id",
    )
    audit_events: Mapped[list[CareerPlanAuditEventDB]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="CareerPlanAuditEventDB.sequence_number",
    )

    @property
    def goal(self) -> dict[str, Any]:
        return _load_object(self.goal_json)

    @goal.setter
    def goal(self, value: dict[str, Any]) -> None:
        self.goal_json = json.dumps(value, sort_keys=True)

    @property
    def search_summary(self) -> dict[str, Any]:
        return _load_object(self.search_summary_json)

    @search_summary.setter
    def search_summary(self, value: dict[str, Any]) -> None:
        self.search_summary_json = json.dumps(value, sort_keys=True)

    @property
    def proposal(self) -> dict[str, Any]:
        return _load_object(self.proposal_json)

    @proposal.setter
    def proposal(self, value: dict[str, Any]) -> None:
        self.proposal_json = json.dumps(value, sort_keys=True)

    @property
    def approval(self) -> dict[str, Any]:
        return _load_object(self.approval_json)

    @approval.setter
    def approval(self, value: dict[str, Any]) -> None:
        self.approval_json = json.dumps(value, sort_keys=True)


class CareerPlanStepDB(Base):
    __tablename__ = "career_plan_steps"
    __table_args__ = (
        UniqueConstraint("run_id", "step_name", "attempt", name="uq_career_plan_step_attempt"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("career_plan_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_name: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    input_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    safe_output_summary_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    safe_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    run: Mapped[CareerPlanRunDB] = relationship(back_populates="steps")

    @property
    def safe_output_summary(self) -> dict[str, Any]:
        return _load_object(self.safe_output_summary_json)

    @safe_output_summary.setter
    def safe_output_summary(self, value: dict[str, Any]) -> None:
        self.safe_output_summary_json = json.dumps(value, sort_keys=True)


class CareerPlanAuditEventDB(Base):
    __tablename__ = "career_plan_audit_events"
    __table_args__ = (
        UniqueConstraint("run_id", "sequence_number", name="uq_career_plan_audit_sequence"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("career_plan_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    safe_payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    run: Mapped[CareerPlanRunDB] = relationship(back_populates="audit_events")

    @property
    def safe_payload(self) -> dict[str, Any]:
        return _load_object(self.safe_payload_json)

    @safe_payload.setter
    def safe_payload(self, value: dict[str, Any]) -> None:
        self.safe_payload_json = json.dumps(value, sort_keys=True)
