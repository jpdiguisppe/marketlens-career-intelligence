from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

CAREER_PLAN_SCHEMA_VERSION = "8.1.3"
MAX_EDITED_ACTIONS = 20
MAX_PLAN_ACTIONS = 20
MAX_RESUME_TEXT_LENGTH = 25_000


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


class CareerPlanOpportunityCategory(str, Enum):
    STRONG_MATCH = "strong_match"
    BALANCED = "balanced"
    STRETCH = "stretch"
    SKIP = "skip"


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


class CareerPlanModelStrategyTheme(str, Enum):
    PRIORITIZE_STRONG_MATCHES = "prioritize_strong_matches"
    BALANCE_APPLY_AND_BUILD = "balance_apply_and_build"
    CLOSE_REPEATED_GAP = "close_repeated_gap"
    VERIFY_CONSTRAINTS_FIRST = "verify_constraints_first"
    BROADEN_SEARCH = "broaden_search"


class CareerPlanModelJobFocus(str, Enum):
    APPLY = "apply"
    VERIFY = "verify"
    BUILD_PROOF = "build_proof"
    MONITOR = "monitor"
    DEPRIORITIZE = "deprioritize"


class CareerPlanModelActionEmphasis(str, Enum):
    ACT_NOW = "act_now"
    VERIFY_FIRST = "verify_first"
    BUILD_EVIDENCE = "build_evidence"
    PREPARE_STORY = "prepare_story"
    REVIEW_LATER = "review_later"
    DEPRIORITIZE = "deprioritize"


class CareerPlanExplanationType(str, Enum):
    WHY_JOB = "why_job"
    WHY_ACTION = "why_action"
    WHY_GAP = "why_gap"
    MODEL_ASSISTANCE = "model_assistance"


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


class CareerPlanExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resume_text: str = Field(..., min_length=20, max_length=MAX_RESUME_TEXT_LENGTH)
    expected_run_version: int = Field(..., ge=1)


class CareerPlanEvidenceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, max_length=120)
    kind: str = Field(..., min_length=1, max_length=50)
    job_ref: str | None = Field(default=None, max_length=100)
    capability: str | None = Field(default=None, max_length=255)
    assessment_status: str | None = Field(default=None, max_length=50)
    source_section: str | None = Field(default=None, max_length=80)
    source_origin: str = Field(..., min_length=1, max_length=50)
    smart_fit_schema_version: str | None = Field(default=None, max_length=40)
    analysis_ref: str | None = Field(default=None, max_length=255)
    summary: str = Field(..., min_length=1, max_length=240)


class CareerPlanPortfolioEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_ref: str = Field(..., min_length=1, max_length=100)
    category: CareerPlanOpportunityCategory
    rank: int = Field(..., ge=1, le=5)
    fit_score: int = Field(..., ge=0, le=100)
    fit_band: str = Field(..., min_length=1, max_length=80)
    confidence: float = Field(..., ge=0.0, le=1.0)
    company: str = Field(..., min_length=1, max_length=255)
    title: str = Field(..., min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    reason_codes: list[str] = Field(default_factory=list, max_length=20)
    evidence_refs: list[str] = Field(default_factory=list, max_length=50)
    gap_refs: list[str] = Field(default_factory=list, max_length=50)
    hard_requirement_flags: list[str] = Field(default_factory=list, max_length=30)
    safe_apply_url: str | None = Field(default=None, max_length=2048)


class CareerPlanRecurringFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability: str = Field(..., min_length=1, max_length=255)
    job_count: int = Field(..., ge=1, le=5)
    job_refs: list[str] = Field(..., min_length=1, max_length=5)
    evidence_refs: list[str] = Field(default_factory=list, max_length=50)
    priority: str | None = Field(default=None, max_length=20)
    summary: str = Field(..., min_length=1, max_length=500)


class CareerPlanAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, max_length=100)
    action_type: CareerPlanActionType
    priority: str = Field(..., min_length=1, max_length=20)
    title: str = Field(..., min_length=1, max_length=255)
    rationale: str = Field(..., min_length=1, max_length=2_000)
    job_refs: list[str] = Field(default_factory=list, max_length=5)
    evidence_refs: list[str] = Field(default_factory=list, max_length=50)
    status: CareerPlanActionStatus = CareerPlanActionStatus.PROPOSED


class CareerPlanProviderTokenUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_tokens: int = Field(default=0, ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    reasoning_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)


class CareerPlanModelTelemetry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requested: bool
    outcome: str = Field(..., min_length=1, max_length=40)
    status_code: str = Field(..., min_length=1, max_length=80)
    model: str | None = Field(default=None, max_length=120)
    prompt_version: str = Field(..., min_length=1, max_length=40)
    schema_version: str = Field(..., min_length=1, max_length=40)
    latency_ms: float = Field(default=0.0, ge=0.0)
    usage: CareerPlanProviderTokenUsage | None = None
    estimated_cost_usd: float | None = Field(default=None, ge=0.0)
    cost_estimate_status: str = Field(..., min_length=1, max_length=80)


class CareerPlanModelJobNote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_ref: str = Field(..., min_length=1, max_length=100)
    focus: CareerPlanModelJobFocus
    supporting_evidence_refs: list[str] = Field(default_factory=list, max_length=10)
    summary: str = Field(..., min_length=1, max_length=500)


class CareerPlanModelActionNote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(..., min_length=1, max_length=100)
    emphasis: CareerPlanModelActionEmphasis
    summary: str = Field(..., min_length=1, max_length=500)


class CareerPlanModelAssistance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(..., min_length=1, max_length=80)
    engine: str = Field(..., min_length=1, max_length=80)
    schema_version: str = Field(..., min_length=1, max_length=40)
    prompt_version: str = Field(..., min_length=1, max_length=40)
    strategy_theme: CareerPlanModelStrategyTheme | None = None
    strategy_summary: str | None = Field(default=None, max_length=800)
    priority_job_refs: list[str] = Field(default_factory=list, max_length=5)
    priority_action_ids: list[str] = Field(default_factory=list, max_length=8)
    job_notes: list[CareerPlanModelJobNote] = Field(default_factory=list, max_length=5)
    action_notes: list[CareerPlanModelActionNote] = Field(default_factory=list, max_length=8)
    uncertainty_codes: list[str] = Field(default_factory=list, max_length=8)
    telemetry: CareerPlanModelTelemetry


class CareerPlanProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(..., min_length=1, max_length=40)
    run_id: int
    generated_at: datetime
    proposal_engine: str = Field(..., min_length=1, max_length=80)
    proposal_status: str = Field(..., min_length=1, max_length=80)
    source_summary: dict[str, Any]
    portfolio: list[CareerPlanPortfolioEntry] = Field(default_factory=list, max_length=5)
    recurring_strengths: list[CareerPlanRecurringFinding] = Field(default_factory=list, max_length=30)
    recurring_gaps: list[CareerPlanRecurringFinding] = Field(default_factory=list, max_length=30)
    evidence_refs: list[CareerPlanEvidenceRef] = Field(default_factory=list, max_length=250)
    actions: list[CareerPlanAction] = Field(default_factory=list, max_length=MAX_PLAN_ACTIONS)
    limitations: list[str] = Field(default_factory=list, max_length=30)
    warnings: list[str] = Field(default_factory=list, max_length=30)
    fallback_status: str = Field(..., min_length=1, max_length=80)
    model_assisted: CareerPlanModelAssistance | None = None


class CareerPlanDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: CareerPlanDecision
    edited_actions: list[CareerPlanAction] = Field(default_factory=list, max_length=MAX_EDITED_ACTIONS)

    @model_validator(mode="after")
    def reject_edits_for_rejected_plan(self) -> "CareerPlanDecisionRequest":
        if self.decision == CareerPlanDecision.REJECTED and self.edited_actions:
            raise ValueError("Rejected plans cannot include edited actions.")
        return self


class CareerPlanExplanationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    explanation_type: CareerPlanExplanationType
    reference_id: str | None = Field(default=None, min_length=1, max_length=120)

    @model_validator(mode="after")
    def require_reference_for_specific_explanations(self) -> "CareerPlanExplanationRequest":
        requires_reference = self.explanation_type in {
            CareerPlanExplanationType.WHY_JOB,
            CareerPlanExplanationType.WHY_ACTION,
            CareerPlanExplanationType.WHY_GAP,
        }
        if requires_reference and not self.reference_id:
            raise ValueError("This explanation type requires a reference_id.")
        if not requires_reference and self.reference_id:
            raise ValueError("Model-assistance explanations do not accept a reference_id.")
        return self


class CareerPlanExplanationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    explanation_type: CareerPlanExplanationType
    reference_id: str | None
    answer: str = Field(..., min_length=1, max_length=2_000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=50)
    engine: str = Field(..., min_length=1, max_length=80)
    based_on_run_version: int = Field(..., ge=1)


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
