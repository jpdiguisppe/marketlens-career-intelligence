export type JobPosting = {
  id: number;
  company: string;
  title: string;
  location: string | null;
  role_category: string | null;
  experience_level: string | null;
  description: string;
  extracted_skills: string[];
};

export type SkillCounts = Record<string, number>;

export type GroupedSkillCounts = Record<string, SkillCounts>;

export type ResumeAnalysisRequest = {
  resume_text: string;
  target_role_category?: string | null;
};

export type CustomAnalysisRequest = {
  resume_text: string;
  job_descriptions: string[];
};

export type ResumeAnalysisResponse = {
  resume_skills: string[];
  target_skills: string[];
  matched_skills: string[];
  missing_skills: string[];
  match_percentage: number;
  learning_priorities: string[];
  postings_analyzed: number;
  target_role_category: string | null;
};

export type SmartFitAnalysisRequest = {
  resume_text: string;
  job_description: string;
  use_model_assisted?: boolean;
};

export type FitBand =
  | "strong_alignment"
  | "credible_alignment"
  | "partial_alignment"
  | "limited_alignment";

export type EvidenceStatus =
  | "demonstrated"
  | "explicit"
  | "mentioned"
  | "implied"
  | "related"
  | "missing";

export type RequirementType =
  | "required_qualification"
  | "core_responsibility"
  | "preferred_qualification"
  | "supporting_context";

export type CoachingActionType =
  | "resume_rewrite"
  | "interview_prep"
  | "learning_focus"
  | "lower_priority"
  | "hard_requirement_check";

export type FitSummary = {
  score: number;
  band: FitBand;
  confidence: number;
  headline: string;
};

export type DocumentQuality = {
  resume_extraction_confidence: number;
  job_extraction_confidence: number;
  warnings: string[];
};

export type HardRequirementAssessment = {
  category: string;
  requirement: string;
  status: "meets" | "does_not_meet" | "unclear";
  source_text: string;
  resume_evidence: string | null;
  explanation: string;
};

export type RequirementAssessment = {
  skill: string;
  requirement_type: RequirementType;
  weight: number;
  status: EvidenceStatus;
  strength: number;
  resume_evidence: string[];
  job_evidence: string;
  explanation: string;
};

export type CategoryCoverage = {
  category: string;
  score: number;
  priority_weight: number;
  strong_skills: string[];
  weak_or_missing_skills: string[];
  summary: string;
};

export type GapGroup = {
  title: string;
  category: string;
  priority: string;
  skills: string[];
  summary: string;
};

export type CoachingAction = {
  action_type: CoachingActionType;
  priority: string;
  title: string;
  skill: string | null;
  category: string | null;
  source_evidence: string[];
  job_evidence: string | null;
  advice: string;
};

export type AnalysisEngine = "deterministic" | "model_assisted";

export type SmartFitAnalysisResponse = {
  fit_summary: FitSummary;
  document_quality: DocumentQuality;
  hard_requirements: HardRequirementAssessment[];
  requirement_assessments: RequirementAssessment[];
  category_coverage: CategoryCoverage[];
  coaching_actions: CoachingAction[];
  report_summary: string[];
  gap_groups: GapGroup[];
  resume_skills_found: string[];
  job_relevant_resume_skills: string[];
  other_resume_skills: string[];
  strong_matches: string[];
  related_matches: string[];
  important_gaps: string[];
  under_sold_experience: string[];
  lower_priority_items: string[];
  recommendations: string[];
  limitations: string[];
  analysis_engine: AnalysisEngine;
  model_assisted_status: string;
};
