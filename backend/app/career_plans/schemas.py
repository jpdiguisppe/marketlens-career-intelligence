from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

CAREER_PLAN_SCHEMA_VERSION = "8.1.1"
MAX_EDITED_ACTIONS = 20


class CareerPlanRunStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    FAILED = "failed"


class CareerPlanStepName(str, Enum):
    VALIDATE_INPUT = "validate_input"
    SEARCH_JOBS = "search_jobs"
    SELECT_CANDIDATES = "select_candidates"
    ANALYZE_SMART_FIT = "analyze_smart_fit"
    SYNTHESIZE_DETERMINISTIC_PLAN = "synthesize_deterministic_plan"
    ENHANCE_PLAN_OPTIONAL = "enhance_plan_optional"
    FINALIZE_PROPOSAL = "finalize_proposal"


class CareerPlanStepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    FAILED = "failed"


class CareerPlanExperienceLevel(str, Enum):
    ANY = "any"
    INTERN = "intern"
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"


class CareerPlanWorkMode(str, Enum):
    ANY = "any"
    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE = "remote"


class CareerPlanPortfolioStrategy(str, Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AMBITIOUS = "ambitious"


class CareerPlanDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


class CareerPlanActionType(str, Enum):
    APPLY_NOW = "apply_now"
    VERIFY_HARD_REQUIREMENT = "verify_hard_requirement"
    STRENGTHEN_RESUME_EVIDENCE = "strengthen_resume_evidence"
    PREPARE_INTERVIEW_EVIDENCE = "prepare_interview_evidence"
    BUILD_PROOF = "build_proof"
    SAVE_FOR_LATER = "save_for_later"
    SKIP_OPPORTUNITY = "skip_opportunity"


class CareerPlanActionStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"
    COMPLETED = "completed"


class CareerPlanGoal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_occupation: str = Field(..., min_length=1, max_length=100)
    experience_level: CareerPlanExperienceLevel = CareerPlanExperienceLevel.ANY
    industry: str | None = Field(default=None, max_length=80)
    location: str | None = Field(default=None, max_length=120)
    work_mode: CareerPlanWorkMode = CareerPlanWorkMode.ANY
    portfolio_strategy: CareerPlanPortfolioStrategy = CareerPlanPortfolioStrategy.BALANCED
    max_jobs_to_analyze: int = Field(default=5, ge=1, le=5)
    model_assisted_planning: bool = False


class CareerPlanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: CareerPlanGoal
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=120)


class CareerPlanAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, max_length=100)
    action_type: CareerPlanActionType
    priority: str = Field(..., min_length=1, max_length=20)
    title: str = Field(..., min_length=1, max_length=255)
    rationale: str = Field(..., min_length=1, max_length=2_000)
    job_refs: list[str] = Field(default_factory=list, max_length=5)
    evidence_refs: list[str] = Field(default_factory=list, max_length=50)
    status: CareerPlanActionStatus = CareerPlanActionStatus.EDITED


class CareerPlanDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: CareerPlanDecision
    edited_actions: list[CareerPlanAction] = Field(default_factory=list, max_length=MAX_EDITED_ACTIONS)

    @model_validator(mode="after")
    def reject_edits_for_rejected_plan(self) -> "CareerPlanDecisionRequest":
        if self.decision == CareerPlanDecision.REJECTED and self.edited_actions:
            raise ValueError("Rejected plans cannot include edited actions.")
        return self


class CareerPlanStepResponse(BaseModel):
    id: int
    step_name: CareerPlanStepName
    status: CareerPlanStepStatus
    attempt: int
    safe_output_summary: dict[str, Any]
    safe_error_code: str | None
    started_at: datetime | None
    completed_at: datetime | None
    latency_ms: float


class CareerPlanAuditEventResponse(BaseModel):
    id: int
    sequence_number: int
    event_type: str
    safe_payload: dict[str, Any]
    created_at: datetime


class CareerPlanRunSummary(BaseModel):
    id: int
    status: CareerPlanRunStatus
    current_step: CareerPlanStepName | None
    schema_version: str
    run_version: int
    attempt_count: int
    goal: CareerPlanGoal
    fallback_status: str
    safe_error_code: str | None
    resume_required_to_resume: bool
    cancel_requested_at: datetime | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class CareerPlanRunResponse(CareerPlanRunSummary):
    search_summary: dict[str, Any]
    proposal: dict[str, Any]
    approval: dict[str, Any]
    steps: list[CareerPlanStepResponse]
    audit_events: list[CareerPlanAuditEventResponse]
