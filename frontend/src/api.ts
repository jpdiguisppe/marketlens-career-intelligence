import type { GroupedSkillCounts, JobPosting, SkillCounts } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

export async function getJobPostings(): Promise<JobPosting[]> {
  return fetchJson<JobPosting[]>("/job-postings");
}

export async function getTopSkills(): Promise<SkillCounts> {
  return fetchJson<SkillCounts>("/skills/top");
}

export async function getTopSkillsByCompany(): Promise<GroupedSkillCounts> {
  return fetchJson<GroupedSkillCounts>("/skills/top-by-company");
}

export async function getTopSkillsByRole(): Promise<GroupedSkillCounts> {
  return fetchJson<GroupedSkillCounts>("/skills/top-by-role");
}
