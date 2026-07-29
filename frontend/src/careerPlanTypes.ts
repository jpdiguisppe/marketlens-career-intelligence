export type CareerPlanRunStatus =
  | "draft"
  | "running"
  | "awaiting_approval"
  | "approved"
  | "rejected"
  | "cancelled"
  | "failed";

export type CareerPlanStepName =
  | "validate_input"
  | "search_jobs"
  | "select_candidates"
  | "analyze_smart_fit"
  | "synthesize_deterministic_plan"
  | "enhance_plan_optional"
  | "finalize_proposal";

export type CareerPlanStepStatus =
  | "pending"
  | "running"
  | "completed"
  | "skipped"
  | "cancelled"
  | "failed";

export type CareerPlanExperienceLevel = "any" | "intern" | "entry" | "mid" | "senior";
export type CareerPlanWorkMode = "any" | "onsite" | "hybrid" | "remote";
export type CareerPlanPortfolioStrategy = "conservative" | "balanced" | "ambitious";
export type CareerPlanOpportunityCategory = "strong_match" | "balanced" | "stretch" | "skip";

export type CareerPlanActionType =
  | "apply_now"
  | "verify_hard_requirement"
  | "strengthen_resume_evidence"
  | "prepare_interview_evidence"
  | "build_proof"
  | "save_for_later"
  | "skip_opportunity";

export type CareerPlanActionStatus = "proposed" | "approved" | "edited" | "rejected" | "completed";
export type CareerPlanDecision = "approved" | "rejected";
export type CareerPlanExplanationType = "why_job" | "why_action" | "why_gap" | "model_assistance";

export type CareerPlanGoal = {
  target_occupation: string;
  experience_level: CareerPlanExperienceLevel;
  industry: string | null;
  location: string | null;
  work_mode: CareerPlanWorkMode;
  portfolio_strategy: CareerPlanPortfolioStrategy;
  max_jobs_to_analyze: number;
  model_assisted_planning: boolean;
};

export type CareerPlanCreateRequest = {
  goal: CareerPlanGoal;
  idempotency_key?: string | null;
};

export type CareerPlanExecuteRequest = {
  resume_text: string;
  expected_run_version: number;
};

export type CareerPlanEvidenceRef = {
  id: string;
  kind: string;
  job_ref: string | null;
  capability: string | null;
  assessment_status: string | null;
  source_section: string | null;
  source_origin: string;
  smart_fit_schema_version: string | null;
  analysis_ref: string | null;
  summary: string;
};

export type CareerPlanPortfolioEntry = {
  job_ref: string;
  category: CareerPlanOpportunityCategory;
  rank: number;
  fit_score: number;
  fit_band: string;
  confidence: number;
  company: string;
  title: string;
  location: string | null;
  reason_codes: string[];
  evidence_refs: string[];
  gap_refs: string[];
  hard_requirement_flags: string[];
  safe_apply_url: string | null;
};

export type CareerPlanRecurringFinding = {
  capability: string;
  job_count: number;
  job_refs: string[];
  evidence_refs: string[];
  priority: string | null;
  summary: string;
};

export type CareerPlanAction = {
  id: string;
  action_type: CareerPlanActionType;
  priority: string;
  title: string;
  rationale: string;
  job_refs: string[];
  evidence_refs: string[];
  status: CareerPlanActionStatus;
};

export type CareerPlanProviderTokenUsage = {
  input_tokens: number;
  cached_input_tokens: number;
  output_tokens: number;
  reasoning_tokens: number;
  total_tokens: number;
};

export type CareerPlanModelTelemetry = {
  requested: boolean;
  outcome: string;
  status_code: string;
  model: string | null;
  prompt_version: string;
  schema_version: string;
  latency_ms: number;
  usage: CareerPlanProviderTokenUsage | null;
  estimated_cost_usd: number | null;
  cost_estimate_status: string;
};

export type CareerPlanModelJobNote = {
  job_ref: string;
  focus: string;
  supporting_evidence_refs: string[];
  summary: string;
};

export type CareerPlanModelActionNote = {
  action_id: string;
  emphasis: string;
  summary: string;
};

export type CareerPlanModelAssistance = {
  status: string;
  engine: string;
  schema_version: string;
  prompt_version: string;
  strategy_theme: string | null;
  strategy_summary: string | null;
  priority_job_refs: string[];
  priority_action_ids: string[];
  job_notes: CareerPlanModelJobNote[];
  action_notes: CareerPlanModelActionNote[];
  uncertainty_codes: string[];
  telemetry: CareerPlanModelTelemetry;
};

export type CareerPlanProposal = {
  schema_version: string;
  run_id: number;
  generated_at: string;
  proposal_engine: string;
  proposal_status: string;
  source_summary: Record<string, unknown>;
  portfolio: CareerPlanPortfolioEntry[];
  recurring_strengths: CareerPlanRecurringFinding[];
  recurring_gaps: CareerPlanRecurringFinding[];
  evidence_refs: CareerPlanEvidenceRef[];
  actions: CareerPlanAction[];
  limitations: string[];
  warnings: string[];
  fallback_status: string;
  model_assisted: CareerPlanModelAssistance | null;
};

export type CareerPlanStep = {
  id: number;
  step_name: CareerPlanStepName;
  status: CareerPlanStepStatus;
  attempt: number;
  safe_output_summary: Record<string, unknown>;
  safe_error_code: string | null;
  started_at: string | null;
  completed_at: string | null;
  latency_ms: number;
};

export type CareerPlanAuditEvent = {
  id: number;
  sequence_number: number;
  event_type: string;
  safe_payload: Record<string, unknown>;
  created_at: string;
};

export type CareerPlanRunSummary = {
  id: number;
  status: CareerPlanRunStatus;
  current_step: CareerPlanStepName | null;
  schema_version: string;
  run_version: number;
  attempt_count: number;
  goal: CareerPlanGoal;
  fallback_status: string;
  safe_error_code: string | null;
  resume_required_to_resume: boolean;
  cancel_requested_at: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
};

export type CareerPlanRun = CareerPlanRunSummary & {
  search_summary: Record<string, unknown>;
  proposal: CareerPlanProposal | Record<string, never>;
  approval: Record<string, unknown>;
  steps: CareerPlanStep[];
  audit_events: CareerPlanAuditEvent[];
};

export type CareerPlanDecisionRequest = {
  decision: CareerPlanDecision;
  edited_actions: CareerPlanAction[];
};

export type CareerPlanExplanationRequest = {
  explanation_type: CareerPlanExplanationType;
  reference_id?: string | null;
};

export type CareerPlanExplanation = {
  explanation_type: CareerPlanExplanationType;
  reference_id: string | null;
  answer: string;
  evidence_refs: string[];
  engine: string;
  based_on_run_version: number;
};

export function hasCareerPlanProposal(
  proposal: CareerPlanRun["proposal"],
): proposal is CareerPlanProposal {
  return (
    typeof proposal === "object" &&
    proposal !== null &&
    "schema_version" in proposal &&
    Array.isArray((proposal as CareerPlanProposal).portfolio) &&
    Array.isArray((proposal as CareerPlanProposal).actions)
  );
}
