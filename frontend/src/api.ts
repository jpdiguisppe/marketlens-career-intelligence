import type {
  GroupedSkillCounts,
  JobPosting,
  ResumeAnalysisRequest,
  ResumeAnalysisResponse,
  SkillCounts,
} from "./types";

declare global {
  interface Window {
    __MARKETLENS_CONFIG__?: {
      apiBaseUrl?: string;
    };
  }
}

function normalizeApiBaseUrl(url: string | undefined): string | undefined {
  const trimmedUrl = url?.trim();

  if (!trimmedUrl) {
    return undefined;
  }

  return trimmedUrl.replace(/\/$/, "");
}

const API_BASE_URL =
  normalizeApiBaseUrl(window.__MARKETLENS_CONFIG__?.apiBaseUrl) ??
  normalizeApiBaseUrl(import.meta.env.VITE_API_BASE_URL) ??
  "http://127.0.0.1:8000";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

async function postJson<TResponse, TRequest>(path: string, body: TRequest): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;

    try {
      const errorBody = (await response.json()) as { detail?: string };
      detail = errorBody.detail ?? detail;
    } catch {
      // Keep the default error message if the response is not JSON.
    }

    throw new Error(`Request failed: ${detail}`);
  }

  return response.json() as Promise<TResponse>;
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

export async function analyzeResume(request: ResumeAnalysisRequest): Promise<ResumeAnalysisResponse> {
  return postJson<ResumeAnalysisResponse, ResumeAnalysisRequest>("/resume/analyze", request);
}
