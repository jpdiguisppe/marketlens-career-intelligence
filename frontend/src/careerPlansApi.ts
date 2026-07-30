import type {
  CareerPlanAction,
  CareerPlanCreateRequest,
  CareerPlanDecisionRequest,
  CareerPlanExecuteRequest,
  CareerPlanExplanation,
  CareerPlanExplanationRequest,
  CareerPlanRun,
  CareerPlanRunSummary,
} from "./careerPlanTypes";
import { hasCareerPlanProposal } from "./careerPlanTypes";

declare global {
  interface Window {
    __MARKETLENS_CONFIG__?: {
      apiBaseUrl?: string;
    };
  }
}

export const CAREER_PLANS_CHANGED_EVENT = "marketlens:career-plans-changed";

function notifyCareerPlansChanged(): void {
  window.dispatchEvent(new Event(CAREER_PLANS_CHANGED_EVENT));
}

function normalizeApiBaseUrl(url: string | undefined): string | undefined {
  const trimmed = url?.trim();
  return trimmed ? trimmed.replace(/\/$/, "") : undefined;
}

const API_BASE_URL =
  normalizeApiBaseUrl(window.__MARKETLENS_CONFIG__?.apiBaseUrl) ??
  normalizeApiBaseUrl(import.meta.env.VITE_API_BASE_URL) ??
  "http://127.0.0.1:8000";

type ApiErrorDetail =
  | string
  | { code?: string; message?: string; msg?: string }
  | { msg?: string }[];

type CareerPlanApprovalEnvelope = {
  decision?: unknown;
  edited_actions?: unknown;
};

function isCareerPlanAction(value: unknown): value is CareerPlanAction {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }
  const action = value as Partial<CareerPlanAction>;
  return (
    typeof action.id === "string" &&
    typeof action.action_type === "string" &&
    typeof action.priority === "string" &&
    typeof action.title === "string" &&
    typeof action.rationale === "string" &&
    typeof action.status === "string" &&
    Array.isArray(action.job_refs) &&
    Array.isArray(action.evidence_refs)
  );
}

function withApprovedEditsForDisplay(run: CareerPlanRun): CareerPlanRun {
  if (!hasCareerPlanProposal(run.proposal)) {
    return run;
  }

  const approval = run.approval as CareerPlanApprovalEnvelope;
  if (approval.decision !== "approved" || !Array.isArray(approval.edited_actions)) {
    return run;
  }

  const generatedActionIds = new Set(run.proposal.actions.map((action) => action.id));
  const approvedEdits = approval.edited_actions.filter(
    (action): action is CareerPlanAction => isCareerPlanAction(action) && generatedActionIds.has(action.id),
  );
  if (approvedEdits.length === 0) {
    return run;
  }

  const editsById = new Map(approvedEdits.map((action) => [action.id, action]));
  return {
    ...run,
    proposal: {
      ...run.proposal,
      actions: run.proposal.actions.map((action) => editsById.get(action.id) ?? action),
    },
  };
}

function errorDetail(body: { detail?: ApiErrorDetail }, response: Response): string {
  const detail = body.detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => item.msg).filter(Boolean);
    return messages.length > 0
      ? messages.join("; ")
      : `${response.status} ${response.statusText}`;
  }
  if (detail && typeof detail === "object") {
    const message = detail.message ?? detail.msg;
    if (message) {
      return detail.code ? `${message} (${detail.code})` : message;
    }
  }
  return `${response.status} ${response.statusText}`;
}

async function authenticatedJson<T>(
  token: string,
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      message = errorDetail((await response.json()) as { detail?: ApiErrorDetail }, response);
    } catch {
      // Preserve the status-based message when the error response is not JSON.
    }
    throw new Error(`Career Plan request failed: ${message}`);
  }

  return response.json() as Promise<T>;
}

export async function listCareerPlans(token: string): Promise<CareerPlanRunSummary[]> {
  return authenticatedJson<CareerPlanRunSummary[]>(token, "/career-plans");
}

export async function getCareerPlan(token: string, runId: number): Promise<CareerPlanRun> {
  const run = await authenticatedJson<CareerPlanRun>(token, `/career-plans/${runId}`);
  return withApprovedEditsForDisplay(run);
}

export async function createCareerPlan(
  token: string,
  request: CareerPlanCreateRequest,
): Promise<CareerPlanRun> {
  const run = await authenticatedJson<CareerPlanRun>(token, "/career-plans", {
    method: "POST",
    body: JSON.stringify(request),
  });
  notifyCareerPlansChanged();
  return withApprovedEditsForDisplay(run);
}

export async function executeCareerPlan(
  token: string,
  runId: number,
  request: CareerPlanExecuteRequest,
): Promise<CareerPlanRun> {
  const run = await authenticatedJson<CareerPlanRun>(token, `/career-plans/${runId}/execute`, {
    method: "POST",
    body: JSON.stringify(request),
  });
  notifyCareerPlansChanged();
  return withApprovedEditsForDisplay(run);
}

export async function cancelCareerPlan(token: string, runId: number): Promise<CareerPlanRun> {
  const run = await authenticatedJson<CareerPlanRun>(token, `/career-plans/${runId}/cancel`, {
    method: "POST",
  });
  notifyCareerPlansChanged();
  return withApprovedEditsForDisplay(run);
}

export async function decideCareerPlan(
  token: string,
  runId: number,
  request: CareerPlanDecisionRequest,
): Promise<CareerPlanRun> {
  const run = await authenticatedJson<CareerPlanRun>(token, `/career-plans/${runId}/decision`, {
    method: "POST",
    body: JSON.stringify(request),
  });
  notifyCareerPlansChanged();
  return withApprovedEditsForDisplay(run);
}

export async function explainCareerPlan(
  token: string,
  runId: number,
  request: CareerPlanExplanationRequest,
): Promise<CareerPlanExplanation> {
  return authenticatedJson<CareerPlanExplanation>(token, `/career-plans/${runId}/explain`, {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function deleteCareerPlan(token: string, runId: number): Promise<void> {
  await authenticatedJson<{ status: string }>(token, `/career-plans/${runId}`, {
    method: "DELETE",
  });
  notifyCareerPlansChanged();
}
