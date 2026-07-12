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
