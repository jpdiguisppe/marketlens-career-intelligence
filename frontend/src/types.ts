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
