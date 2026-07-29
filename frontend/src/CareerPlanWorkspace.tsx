import { useCallback, useEffect, useMemo, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { SignInButton, useAuth } from "@clerk/react";

import { extractResumeFileText, getModelAssistedStatus } from "./api";
import {
  cancelCareerPlan,
  createCareerPlan,
  decideCareerPlan,
  deleteCareerPlan,
  executeCareerPlan,
  explainCareerPlan,
  getCareerPlan,
  listCareerPlans,
} from "./careerPlansApi";
import type {
  CareerPlanAction,
  CareerPlanExplanation,
  CareerPlanExplanationType,
  CareerPlanGoal,
  CareerPlanRun,
  CareerPlanRunStatus,
  CareerPlanRunSummary,
  CareerPlanStepName,
  CareerPlanStepStatus,
} from "./careerPlanTypes";
import { hasCareerPlanProposal } from "./careerPlanTypes";
import { SafeExternalLink } from "./SafeExternalLink";
import type { ModelAssistedStatusResponse } from "./types";
import "./careerPlanWorkspace.css";

const workflowSteps: { name: CareerPlanStepName; label: string; description: string }[] = [
  { name: "validate_input", label: "Validate goal", description: "Check the target, constraints, and bounded workflow inputs." },
  { name: "search_jobs", label: "Search jobs", description: "Call MarketLens's existing public job-search providers." },
  { name: "select_candidates", label: "Select candidates", description: "Choose a diverse, deterministic set of up to five jobs." },
  { name: "analyze_smart_fit", label: "Run Smart Fit", description: "Analyze each selected job with the existing grounded scoring system." },
  { name: "synthesize_deterministic_plan", label: "Build base plan", description: "Create the portfolio, repeated findings, and proposed actions." },
  { name: "enhance_plan_optional", label: "Optional AI organization", description: "Organize existing IDs and priorities without changing evidence or scores." },
  { name: "finalize_proposal", label: "Prepare review", description: "Save the proposal and pause for your approval." },
];

const initialGoal: CareerPlanGoal = {
  target_occupation: "Software Engineer",
  experience_level: "entry",
  industry: null,
  location: "Philadelphia, PA",
  work_mode: "any",
  portfolio_strategy: "balanced",
  max_jobs_to_analyze: 5,
  model_assisted_planning: false,
};

function formatLabel(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatDate(value: string | null): string {
  if (!value) {
    return "Not completed";
  }
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatCost(value: number | null): string {
  if (value === null) {
    return "Unavailable";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 4,
    maximumFractionDigits: 8,
  }).format(value);
}

function runStatusTone(status: CareerPlanRunStatus): string {
  if (status === "approved") return "positive";
  if (status === "awaiting_approval" || status === "running") return "active";
  if (status === "failed" || status === "rejected") return "negative";
  if (status === "cancelled") return "muted";
  return "neutral";
}

function stepStatusTone(status: CareerPlanStepStatus): string {
  if (status === "completed") return "positive";
  if (status === "running") return "active";
  if (status === "failed") return "negative";
  if (status === "cancelled" || status === "skipped") return "muted";
  return "neutral";
}

function latestStep(run: CareerPlanRun, stepName: CareerPlanStepName) {
  return [...run.steps]
    .filter((step) => step.step_name === stepName)
    .sort((a, b) => b.attempt - a.attempt || b.id - a.id)[0];
}

function idempotencyKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `career-plan-${crypto.randomUUID()}`;
  }
  return `career-plan-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function historyMatches(plan: CareerPlanRunSummary, query: string): boolean {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return true;
  return [
    plan.goal.target_occupation,
    plan.goal.industry ?? "",
    plan.goal.location ?? "",
    plan.goal.experience_level,
    plan.status,
  ].some((value) => value.toLowerCase().includes(normalized));
}

function EvidenceLinks({
  evidenceIds,
  run,
}: {
  evidenceIds: string[];
  run: CareerPlanRun;
}) {
  if (!hasCareerPlanProposal(run.proposal) || evidenceIds.length === 0) {
    return <p className="career-plan-muted">No additional evidence references were stored.</p>;
  }

  const evidenceMap = new Map(run.proposal.evidence_refs.map((item) => [item.id, item]));
  const evidence = evidenceIds.map((id) => evidenceMap.get(id)).filter(Boolean);

  if (evidence.length === 0) {
    return <p className="career-plan-muted">Evidence IDs are available, but no matching safe summaries were found.</p>;
  }

  return (
    <ul className="career-plan-evidence-list">
      {evidence.map((item) => item && (
        <li key={item.id}>
          <strong>{item.capability ?? formatLabel(item.kind)}</strong>
          <span>{item.summary}</span>
          <small>
            {formatLabel(item.source_origin)}
            {item.assessment_status ? ` · ${formatLabel(item.assessment_status)}` : ""}
            {item.source_section ? ` · ${formatLabel(item.source_section)}` : ""}
          </small>
        </li>
      ))}
    </ul>
  );
}

function WorkflowTimeline({ run, executing }: { run: CareerPlanRun; executing: boolean }) {
  return (
    <section className="career-plan-card">
      <div className="career-plan-section-heading">
        <div>
          <p className="eyebrow inline-eyebrow">Agent trajectory</p>
          <h3>Seven-step workflow</h3>
        </div>
        <span className={`career-plan-status ${runStatusTone(run.status)}`}>
          {executing ? "Updating live" : formatLabel(run.status)}
        </span>
      </div>

      <ol className="career-plan-timeline" aria-label="Career Plan workflow progress">
        {workflowSteps.map((definition, index) => {
          const step = latestStep(run, definition.name);
          const status: CareerPlanStepStatus = step?.status ?? "pending";
          return (
            <li className={`career-plan-step ${stepStatusTone(status)}`} key={definition.name}>
              <span className="career-plan-step-number" aria-hidden="true">{index + 1}</span>
              <div>
                <div className="career-plan-step-title-row">
                  <strong>{definition.label}</strong>
                  <span className={`career-plan-status ${stepStatusTone(status)}`}>{formatLabel(status)}</span>
                </div>
                <p>{definition.description}</p>
                {step && (
                  <small>
                    Attempt {step.attempt} · {Math.round(step.latency_ms).toLocaleString()} ms
                    {step.safe_error_code ? ` · ${formatLabel(step.safe_error_code)}` : ""}
                  </small>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function ModelAssistanceCard({
  run,
  onExplain,
  explaining,
}: {
  run: CareerPlanRun;
  onExplain: () => void;
  explaining: boolean;
}) {
  if (!hasCareerPlanProposal(run.proposal)) return null;
  const assistance = run.proposal.model_assisted;

  return (
    <section className="career-plan-card career-plan-model-card">
      <div className="career-plan-section-heading">
        <div>
          <p className="eyebrow inline-eyebrow">Planning engine</p>
          <h3>Deterministic foundation, optional AI organization</h3>
        </div>
        <span className={`career-plan-status ${assistance?.status === "used" ? "active" : assistance?.status === "not_requested" ? "neutral" : "muted"}`}>
          {assistance ? formatLabel(assistance.status) : "Deterministic"}
        </span>
      </div>

      {assistance?.status === "used" ? (
        <>
          <p>{assistance.strategy_summary ?? "AI selected a bounded ordering from the saved deterministic plan."}</p>
          <div className="career-plan-metric-grid">
            <div><span>Theme</span><strong>{formatLabel(assistance.strategy_theme ?? "bounded_selection")}</strong></div>
            <div><span>Model</span><strong>{assistance.telemetry.model ?? "Configured provider"}</strong></div>
            <div><span>Latency</span><strong>{Math.round(assistance.telemetry.latency_ms).toLocaleString()} ms</strong></div>
            <div><span>Estimated cost</span><strong>{formatCost(assistance.telemetry.estimated_cost_usd)}</strong></div>
          </div>
          <p className="career-plan-boundary-note">
            The model selected only supplied IDs and enums. Scores, evidence, categories, hard requirements,
            actions, provenance, and approval state remain deterministic and unchanged.
          </p>
        </>
      ) : assistance?.status === "not_requested" ? (
        <p>The complete proposal was generated deterministically. Model assistance was not requested.</p>
      ) : (
        <p>
          Model assistance safely fell back with status <strong>{formatLabel(assistance?.telemetry.status_code ?? run.fallback_status)}</strong>.
          The complete deterministic plan remains available for review.
        </p>
      )}

      <button className="career-plan-link-button" type="button" onClick={onExplain} disabled={explaining}>
        {explaining ? "Explaining…" : "What did AI contribute?"}
      </button>
    </section>
  );
}

function PlanHistory({
  plans,
  selectedRunId,
  query,
  loading,
  onQueryChange,
  onSelect,
  onRefresh,
}: {
  plans: CareerPlanRunSummary[];
  selectedRunId: number | null;
  query: string;
  loading: boolean;
  onQueryChange: (value: string) => void;
  onSelect: (runId: number) => void;
  onRefresh: () => void;
}) {
  const filtered = plans.filter((plan) => historyMatches(plan, query));

  return (
    <section className="career-plan-card career-plan-history-card">
      <div className="career-plan-section-heading">
        <div>
          <p className="eyebrow inline-eyebrow">Private history</p>
          <h3>Saved plans</h3>
        </div>
        <button className="career-plan-icon-button" type="button" onClick={onRefresh} disabled={loading}>
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>
      <label className="career-plan-field">
        <span>Search plan history</span>
        <input
          type="search"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Role, location, industry, status"
        />
      </label>

      {filtered.length === 0 ? (
        <div className="empty-state career-plan-compact-empty">
          <h3>{plans.length === 0 ? "No Career Plans yet" : "No matching plans"}</h3>
          <p>{plans.length === 0 ? "Create your first bounded plan above." : "Try a broader search."}</p>
        </div>
      ) : (
        <div className="career-plan-history-list">
          {filtered.map((plan) => (
            <button
              className={`career-plan-history-item ${selectedRunId === plan.id ? "selected" : ""}`}
              type="button"
              key={plan.id}
              onClick={() => onSelect(plan.id)}
              aria-current={selectedRunId === plan.id ? "true" : undefined}
            >
              <span>
                <strong>{plan.goal.target_occupation}</strong>
                <small>{plan.goal.location ?? "Any location"} · {formatLabel(plan.goal.experience_level)}</small>
              </span>
              <span className={`career-plan-status ${runStatusTone(plan.status)}`}>{formatLabel(plan.status)}</span>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

export default function CareerPlanWorkspace() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [goal, setGoal] = useState<CareerPlanGoal>(initialGoal);
  const [resumeText, setResumeText] = useState("");
  const [resumeMessage, setResumeMessage] = useState<string | null>(null);
  const [plans, setPlans] = useState<CareerPlanRunSummary[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [selectedRun, setSelectedRun] = useState<CareerPlanRun | null>(null);
  const [historyQuery, setHistoryQuery] = useState("");
  const [modelStatus, setModelStatus] = useState<ModelAssistedStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [resumeUploading, setResumeUploading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [runLoading, setRunLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [deciding, setDeciding] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [explainingKey, setExplainingKey] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<CareerPlanExplanation | null>(null);
  const [editingActions, setEditingActions] = useState(false);
  const [editedActions, setEditedActions] = useState<CareerPlanAction[]>([]);

  const requireToken = useCallback(async () => {
    const token = await getToken();
    if (!token) throw new Error("No Clerk session token was available.");
    return token;
  }, [getToken]);

  const upsertRun = useCallback((run: CareerPlanRun) => {
    setSelectedRun(run);
    setSelectedRunId(run.id);
    setPlans((current) => {
      const withoutRun = current.filter((item) => item.id !== run.id);
      return [run, ...withoutRun].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
    });
  }, []);

  const loadHistory = useCallback(async () => {
    if (!isSignedIn) {
      setPlans([]);
      return;
    }
    try {
      setHistoryLoading(true);
      setError(null);
      const token = await requireToken();
      const history = await listCareerPlans(token);
      setPlans(history);
      if (selectedRunId && !history.some((item) => item.id === selectedRunId)) {
        setSelectedRunId(null);
        setSelectedRun(null);
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Could not load Career Plan history.");
    } finally {
      setHistoryLoading(false);
    }
  }, [isSignedIn, requireToken, selectedRunId]);

  const loadRun = useCallback(async (runId: number, quiet = false) => {
    try {
      if (!quiet) setRunLoading(true);
      const token = await requireToken();
      const run = await getCareerPlan(token, runId);
      upsertRun(run);
      return run;
    } catch (loadError) {
      if (!quiet) {
        setError(loadError instanceof Error ? loadError.message : "Could not open that Career Plan.");
      }
      return null;
    } finally {
      if (!quiet) setRunLoading(false);
    }
  }, [requireToken, upsertRun]);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      setPlans([]);
      setSelectedRun(null);
      setSelectedRunId(null);
      setError(null);
      return;
    }
    void loadHistory();
  }, [isLoaded, isSignedIn, loadHistory]);

  useEffect(() => {
    let cancelled = false;
    getModelAssistedStatus()
      .then((status) => {
        if (cancelled) return;
        setModelStatus(status);
        if (!status.enabled) {
          setGoal((current) => ({ ...current, model_assisted_planning: false }));
        }
      })
      .catch(() => {
        if (!cancelled) setModelStatus(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!executing || !selectedRunId || !isSignedIn) return;
    const interval = window.setInterval(() => {
      void loadRun(selectedRunId, true);
    }, 750);
    return () => window.clearInterval(interval);
  }, [executing, isSignedIn, loadRun, selectedRunId]);

  useEffect(() => {
    if (selectedRun && hasCareerPlanProposal(selectedRun.proposal)) {
      setEditedActions(selectedRun.proposal.actions);
    } else {
      setEditedActions([]);
    }
    setEditingActions(false);
    setExplanation(null);
  }, [selectedRun?.id, selectedRun?.run_version]);

  const proposal = selectedRun && hasCareerPlanProposal(selectedRun.proposal) ? selectedRun.proposal : null;
  const canRunSelected = selectedRun && ["draft", "failed", "cancelled"].includes(selectedRun.status);
  const canDecide = selectedRun?.status === "awaiting_approval" && proposal !== null;

  const modelNotesByJob = useMemo(() => {
    const notes = new Map<string, string>();
    proposal?.model_assisted?.job_notes.forEach((note) => notes.set(note.job_ref, note.summary));
    return notes;
  }, [proposal]);

  const modelNotesByAction = useMemo(() => {
    const notes = new Map<string, string>();
    proposal?.model_assisted?.action_notes.forEach((note) => notes.set(note.action_id, note.summary));
    return notes;
  }, [proposal]);

  async function handleResumeUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      setResumeUploading(true);
      setResumeMessage(null);
      const extraction = await extractResumeFileText(file);
      setResumeText(extraction.text);
      setResumeMessage(`Loaded ${extraction.filename} (${extraction.character_count.toLocaleString()} characters). ${extraction.warnings[0] ?? ""}`.trim());
    } catch (uploadError) {
      setResumeMessage(uploadError instanceof Error ? uploadError.message : "Could not extract text from that résumé file.");
    } finally {
      setResumeUploading(false);
      event.target.value = "";
    }
  }

  async function runExisting(run: CareerPlanRun) {
    if (resumeText.trim().length < 20) {
      setError("Paste or upload at least 20 characters of résumé text before running a Career Plan.");
      return;
    }
    try {
      setExecuting(true);
      setError(null);
      setSelectedRunId(run.id);
      const token = await requireToken();
      const completed = await executeCareerPlan(token, run.id, {
        resume_text: resumeText,
        expected_run_version: run.run_version,
      });
      upsertRun(completed);
    } catch (executeError) {
      setError(executeError instanceof Error ? executeError.message : "Could not execute the Career Plan.");
      await loadRun(run.id, true);
    } finally {
      setExecuting(false);
    }
  }

  async function handleCreateAndRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!goal.target_occupation.trim()) {
      setError("Enter a target occupation before creating a Career Plan.");
      return;
    }
    if (resumeText.trim().length < 20) {
      setError("Paste or upload at least 20 characters of résumé text before running a Career Plan.");
      return;
    }
    try {
      setRunLoading(true);
      setError(null);
      const token = await requireToken();
      const created = await createCareerPlan(token, {
        goal: {
          ...goal,
          target_occupation: goal.target_occupation.trim(),
          industry: goal.industry?.trim() || null,
          location: goal.location?.trim() || null,
        },
        idempotency_key: idempotencyKey(),
      });
      upsertRun(created);
      setRunLoading(false);
      await runExisting(created);
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Could not create the Career Plan.");
    } finally {
      setRunLoading(false);
    }
  }

  async function handleCancel() {
    if (!selectedRun) return;
    try {
      setCancelling(true);
      setError(null);
      const token = await requireToken();
      const cancelled = await cancelCareerPlan(token, selectedRun.id);
      upsertRun(cancelled);
    } catch (cancelError) {
      setError(cancelError instanceof Error ? cancelError.message : "Could not request cancellation.");
    } finally {
      setCancelling(false);
    }
  }

  async function handleDecision(decision: "approved" | "rejected") {
    if (!selectedRun) return;
    try {
      setDeciding(true);
      setError(null);
      const token = await requireToken();
      const decided = await decideCareerPlan(token, selectedRun.id, {
        decision,
        edited_actions: decision === "approved" && editingActions
          ? editedActions.map((action) => ({ ...action, status: "edited" }))
          : [],
      });
      upsertRun(decided);
    } catch (decisionError) {
      setError(decisionError instanceof Error ? decisionError.message : "Could not record that plan decision.");
    } finally {
      setDeciding(false);
    }
  }

  async function handleDelete() {
    if (!selectedRun) return;
    const confirmed = window.confirm(`Delete the saved Career Plan for ${selectedRun.goal.target_occupation}?`);
    if (!confirmed) return;
    try {
      setDeleting(true);
      setError(null);
      const token = await requireToken();
      await deleteCareerPlan(token, selectedRun.id);
      setPlans((current) => current.filter((item) => item.id !== selectedRun.id));
      setSelectedRun(null);
      setSelectedRunId(null);
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Could not delete that Career Plan.");
    } finally {
      setDeleting(false);
    }
  }

  async function handleExplain(type: CareerPlanExplanationType, referenceId?: string) {
    if (!selectedRun) return;
    const key = `${type}:${referenceId ?? ""}`;
    try {
      setExplainingKey(key);
      setError(null);
      const token = await requireToken();
      const result = await explainCareerPlan(token, selectedRun.id, {
        explanation_type: type,
        reference_id: referenceId ?? null,
      });
      setExplanation(result);
    } catch (explainError) {
      setError(explainError instanceof Error ? explainError.message : "Could not explain that saved plan item.");
    } finally {
      setExplainingKey(null);
    }
  }

  function updateAction(actionId: string, patch: Partial<CareerPlanAction>) {
    setEditedActions((current) => current.map((action) => action.id === actionId ? { ...action, ...patch } : action));
  }

  if (!isLoaded) {
    return <section className="career-plan-auth-state"><p>Loading your account…</p></section>;
  }

  if (!isSignedIn) {
    return (
      <main className="career-plan-shell">
        <section className="career-plan-auth-state">
          <p className="eyebrow">Private Career Planning Agent</p>
          <h1>Build a saved, evidence-grounded career plan</h1>
          <p>
            Sign in to create resumable planning runs, compare a bounded set of jobs, inspect every workflow step,
            and approve or edit the proposed actions. Raw résumé text is not stored in Career Plan records.
          </p>
          <SignInButton mode="modal">
            <button className="refresh-button" type="button">Sign in to Career Plans</button>
          </SignInButton>
        </section>
      </main>
    );
  }

  return (
    <main className="career-plan-shell">
      <section className="career-plan-hero">
        <div>
          <p className="eyebrow">MarketLens Career Planning Agent</p>
          <h1>Turn a career goal into a reviewable action plan</h1>
          <p>
            MarketLens searches and analyzes a bounded job set, identifies repeated strengths and gaps,
            proposes actions, and waits for your approval. Every scored conclusion stays grounded in the existing Smart Fit system.
          </p>
        </div>
        <div className="career-plan-privacy-card">
          <strong>Privacy boundary</strong>
          <span>Résumé text stays in this page's memory while you work.</span>
          <span>Career Plan records store only derived, user-owned evidence references and safe summaries.</span>
        </div>
      </section>

      {error && (
        <section className="error-box career-plan-error" role="alert">
          <strong>Career Plan error</strong>
          <p>{error}</p>
        </section>
      )}

      <div className="career-plan-layout">
        <aside className="career-plan-sidebar">
          <section className="career-plan-card career-plan-builder-card">
            <p className="eyebrow inline-eyebrow">New planning run</p>
            <h3>Define your goal</h3>
            <form className="career-plan-form" onSubmit={handleCreateAndRun}>
              <label className="career-plan-field">
                <span>Target occupation</span>
                <input
                  required
                  maxLength={100}
                  value={goal.target_occupation}
                  onChange={(event) => setGoal((current) => ({ ...current, target_occupation: event.target.value }))}
                  placeholder="Software Engineer"
                />
              </label>

              <div className="career-plan-form-grid">
                <label className="career-plan-field">
                  <span>Experience level</span>
                  <select value={goal.experience_level} onChange={(event) => setGoal((current) => ({ ...current, experience_level: event.target.value as CareerPlanGoal["experience_level"] }))}>
                    <option value="any">Any</option>
                    <option value="intern">Internship</option>
                    <option value="entry">Entry level</option>
                    <option value="mid">Mid level</option>
                    <option value="senior">Senior</option>
                  </select>
                </label>
                <label className="career-plan-field">
                  <span>Work mode</span>
                  <select value={goal.work_mode} onChange={(event) => setGoal((current) => ({ ...current, work_mode: event.target.value as CareerPlanGoal["work_mode"] }))}>
                    <option value="any">Any</option>
                    <option value="onsite">On-site</option>
                    <option value="hybrid">Hybrid</option>
                    <option value="remote">Remote</option>
                  </select>
                </label>
              </div>

              <label className="career-plan-field">
                <span>Location</span>
                <input value={goal.location ?? ""} onChange={(event) => setGoal((current) => ({ ...current, location: event.target.value }))} placeholder="Philadelphia, PA" />
              </label>
              <label className="career-plan-field">
                <span>Industry (optional)</span>
                <input value={goal.industry ?? ""} onChange={(event) => setGoal((current) => ({ ...current, industry: event.target.value }))} placeholder="Healthcare, finance, technology" />
              </label>

              <div className="career-plan-form-grid">
                <label className="career-plan-field">
                  <span>Portfolio strategy</span>
                  <select value={goal.portfolio_strategy} onChange={(event) => setGoal((current) => ({ ...current, portfolio_strategy: event.target.value as CareerPlanGoal["portfolio_strategy"] }))}>
                    <option value="conservative">Conservative</option>
                    <option value="balanced">Balanced</option>
                    <option value="ambitious">Ambitious</option>
                  </select>
                </label>
                <label className="career-plan-field">
                  <span>Jobs to analyze</span>
                  <select value={goal.max_jobs_to_analyze} onChange={(event) => setGoal((current) => ({ ...current, max_jobs_to_analyze: Number(event.target.value) }))}>
                    {[1, 2, 3, 4, 5].map((count) => <option value={count} key={count}>{count}</option>)}
                  </select>
                </label>
              </div>

              <label className="career-plan-checkbox">
                <input
                  type="checkbox"
                  checked={goal.model_assisted_planning}
                  disabled={modelStatus?.enabled !== true}
                  onChange={(event) => setGoal((current) => ({ ...current, model_assisted_planning: event.target.checked }))}
                />
                <span>
                  <strong>Use bounded AI organization</strong>
                  <small>
                    {modelStatus?.enabled
                      ? "AI may order existing jobs and actions, but cannot change evidence or scores."
                      : "Provider assistance is unavailable; deterministic planning remains fully functional."}
                  </small>
                </span>
              </label>

              <label className="career-plan-field">
                <span>Résumé text</span>
                <textarea
                  value={resumeText}
                  onChange={(event) => setResumeText(event.target.value)}
                  placeholder="Paste your résumé text here, or upload a PDF, DOCX, or TXT file below."
                  rows={9}
                  maxLength={25000}
                />
              </label>
              <label className="career-plan-upload">
                <span>{resumeUploading ? "Extracting résumé…" : "Upload résumé file"}</span>
                <input type="file" accept=".pdf,.docx,.txt" onChange={handleResumeUpload} disabled={resumeUploading} />
              </label>
              {resumeMessage && <p className="career-plan-helper" aria-live="polite">{resumeMessage}</p>}
              <p className="career-plan-helper">{resumeText.length.toLocaleString()} / 25,000 characters · not saved in browser storage</p>

              <button className="refresh-button career-plan-primary-button" type="submit" disabled={runLoading || executing || resumeUploading}>
                {runLoading ? "Creating…" : executing ? "Running plan…" : "Create and run Career Plan"}
              </button>
            </form>
          </section>

          <PlanHistory
            plans={plans}
            selectedRunId={selectedRunId}
            query={historyQuery}
            loading={historyLoading}
            onQueryChange={setHistoryQuery}
            onSelect={(runId) => {
              setSelectedRunId(runId);
              void loadRun(runId);
            }}
            onRefresh={() => void loadHistory()}
          />
        </aside>

        <section className="career-plan-main" aria-live="polite">
          {runLoading && !selectedRun ? (
            <section className="career-plan-card"><p>Loading Career Plan…</p></section>
          ) : !selectedRun ? (
            <section className="career-plan-card career-plan-empty-workspace">
              <p className="eyebrow inline-eyebrow">Ready</p>
              <h2>Create a plan or reopen one from history</h2>
              <p>
                Your Career Plan will show all seven workflow steps, the opportunity portfolio,
                repeated strengths and gaps, proposed actions, model fallback status, and an explicit approval gate.
              </p>
            </section>
          ) : (
            <>
              <section className="career-plan-card career-plan-run-header">
                <div>
                  <p className="eyebrow inline-eyebrow">Career Plan #{selectedRun.id}</p>
                  <h2>{selectedRun.goal.target_occupation}</h2>
                  <p>
                    {selectedRun.goal.location ?? "Any location"} · {formatLabel(selectedRun.goal.experience_level)} · {formatLabel(selectedRun.goal.portfolio_strategy)} strategy
                  </p>
                  <small>Updated {formatDate(selectedRun.updated_at)} · Run version {selectedRun.run_version} · Attempt {selectedRun.attempt_count}</small>
                </div>
                <div className="career-plan-run-actions">
                  <span className={`career-plan-status large ${runStatusTone(selectedRun.status)}`}>{formatLabel(selectedRun.status)}</span>
                  <button className="career-plan-icon-button" type="button" onClick={() => void loadRun(selectedRun.id)} disabled={runLoading}>Refresh</button>
                  <button className="career-plan-icon-button danger" type="button" onClick={handleDelete} disabled={deleting || executing}>{deleting ? "Deleting…" : "Delete"}</button>
                </div>
              </section>

              {(executing || selectedRun.status === "running") && (
                <section className="career-plan-running-banner">
                  <div>
                    <strong>Career Planning workflow is active</strong>
                    <span>The timeline refreshes from the server while each bounded step commits its status.</span>
                  </div>
                  <button className="career-plan-danger-button" type="button" onClick={handleCancel} disabled={cancelling}>
                    {cancelling ? "Requesting cancellation…" : "Cancel safely"}
                  </button>
                </section>
              )}

              {canRunSelected && (
                <section className="career-plan-card career-plan-retry-card">
                  <div>
                    <strong>{selectedRun.status === "draft" ? "This draft is ready to run." : "This run can be safely retried."}</strong>
                    <p>
                      {selectedRun.resume_required_to_resume
                        ? "Paste or upload your résumé again because raw résumé text is intentionally not stored."
                        : "The current in-memory résumé can be used for this run."}
                    </p>
                  </div>
                  <button className="refresh-button" type="button" onClick={() => void runExisting(selectedRun)} disabled={executing || resumeText.trim().length < 20}>
                    {executing ? "Running…" : selectedRun.status === "draft" ? "Run this draft" : "Retry this plan"}
                  </button>
                </section>
              )}

              <WorkflowTimeline run={selectedRun} executing={executing} />

              {selectedRun.safe_error_code && (
                <section className="error-box career-plan-error">
                  <strong>Safe workflow error</strong>
                  <p>{formatLabel(selectedRun.safe_error_code)}</p>
                </section>
              )}

              {proposal && (
                <>
                  <ModelAssistanceCard
                    run={selectedRun}
                    onExplain={() => void handleExplain("model_assistance")}
                    explaining={explainingKey === "model_assistance:"}
                  />

                  {(proposal.warnings.length > 0 || proposal.limitations.length > 0) && (
                    <section className="career-plan-card">
                      <div className="career-plan-section-heading">
                        <div><p className="eyebrow inline-eyebrow">Read before deciding</p><h3>Warnings and limitations</h3></div>
                        <span className="career-plan-status muted">{proposal.warnings.length + proposal.limitations.length} notes</span>
                      </div>
                      <ul className="career-plan-note-list">
                        {proposal.warnings.map((warning) => <li key={`warning-${warning}`}><strong>Warning:</strong> {warning}</li>)}
                        {proposal.limitations.map((limitation) => <li key={`limitation-${limitation}`}>{limitation}</li>)}
                      </ul>
                    </section>
                  )}

                  <section className="career-plan-card">
                    <div className="career-plan-section-heading">
                      <div>
                        <p className="eyebrow inline-eyebrow">Opportunity portfolio</p>
                        <h3>{proposal.portfolio.length} analyzed opportunities</h3>
                      </div>
                      <span className="career-plan-status neutral">Strategy, not hiring probability</span>
                    </div>

                    {proposal.portfolio.length === 0 ? (
                      <div className="empty-state career-plan-compact-empty"><h3>No matching jobs returned</h3><p>The saved plan remains complete and explains the search limitations.</p></div>
                    ) : (
                      <div className="career-plan-portfolio-grid">
                        {proposal.portfolio.map((entry) => (
                          <article className={`career-plan-opportunity category-${entry.category}`} key={entry.job_ref}>
                            <div className="career-plan-opportunity-header">
                              <span className="career-plan-rank">#{entry.rank}</span>
                              <span className={`career-plan-category ${entry.category}`}>{formatLabel(entry.category)}</span>
                            </div>
                            <h4>{entry.title}</h4>
                            <p>{entry.company} · {entry.location ?? "Location not listed"}</p>
                            <div className="career-plan-score-line">
                              <strong>{entry.fit_score}%</strong>
                              <span>{formatLabel(entry.fit_band)} · {Math.round(entry.confidence * 100)}% confidence</span>
                            </div>
                            {modelNotesByJob.get(entry.job_ref) && <p className="career-plan-model-note">AI organization: {modelNotesByJob.get(entry.job_ref)}</p>}
                            {entry.hard_requirement_flags.length > 0 && (
                              <div className="career-plan-warning-list">
                                {entry.hard_requirement_flags.map((flag) => <span key={flag}>{formatLabel(flag)}</span>)}
                              </div>
                            )}
                            <details className="career-plan-evidence-details">
                              <summary>Evidence and gaps</summary>
                              <EvidenceLinks evidenceIds={[...entry.evidence_refs, ...entry.gap_refs]} run={selectedRun} />
                            </details>
                            <div className="career-plan-card-actions">
                              <button className="career-plan-link-button" type="button" onClick={() => void handleExplain("why_job", entry.job_ref)} disabled={explainingKey === `why_job:${entry.job_ref}`}>
                                {explainingKey === `why_job:${entry.job_ref}` ? "Explaining…" : "Why this category?"}
                              </button>
                              {entry.safe_apply_url && <SafeExternalLink url={entry.safe_apply_url}>Open posting</SafeExternalLink>}
                            </div>
                          </article>
                        ))}
                      </div>
                    )}
                  </section>

                  <section className="career-plan-findings-grid">
                    <article className="career-plan-card">
                      <div className="career-plan-section-heading"><div><p className="eyebrow inline-eyebrow">Repeated evidence</p><h3>Strengths</h3></div><span className="career-plan-status positive">{proposal.recurring_strengths.length}</span></div>
                      {proposal.recurring_strengths.length === 0 ? <p className="career-plan-muted">No strength repeated across at least two analyzed jobs.</p> : (
                        <div className="career-plan-finding-list">
                          {proposal.recurring_strengths.map((finding) => (
                            <article key={finding.capability}>
                              <strong>{finding.capability}</strong>
                              <p>{finding.summary}</p>
                              <small>{finding.job_count} jobs · {finding.job_refs.join(", ")}</small>
                            </article>
                          ))}
                        </div>
                      )}
                    </article>
                    <article className="career-plan-card">
                      <div className="career-plan-section-heading"><div><p className="eyebrow inline-eyebrow">Repeated gaps</p><h3>Gap-to-proof priorities</h3></div><span className="career-plan-status negative">{proposal.recurring_gaps.length}</span></div>
                      {proposal.recurring_gaps.length === 0 ? <p className="career-plan-muted">No gap repeated across at least two analyzed jobs.</p> : (
                        <div className="career-plan-finding-list">
                          {proposal.recurring_gaps.map((finding) => (
                            <article key={finding.capability}>
                              <div className="career-plan-step-title-row"><strong>{finding.capability}</strong><span className={`career-plan-status ${finding.priority === "high" ? "negative" : "muted"}`}>{formatLabel(finding.priority ?? "unranked")}</span></div>
                              <p>{finding.summary}</p>
                              <button className="career-plan-link-button" type="button" onClick={() => void handleExplain("why_gap", finding.capability)} disabled={explainingKey === `why_gap:${finding.capability}`}>
                                {explainingKey === `why_gap:${finding.capability}` ? "Explaining…" : "Why is this a gap?"}
                              </button>
                            </article>
                          ))}
                        </div>
                      )}
                    </article>
                  </section>

                  <section className="career-plan-card">
                    <div className="career-plan-section-heading">
                      <div><p className="eyebrow inline-eyebrow">Proposed plan</p><h3>Prioritized actions</h3></div>
                      {canDecide && (
                        <button className="career-plan-icon-button" type="button" onClick={() => setEditingActions((current) => !current)}>
                          {editingActions ? "Use original actions" : "Edit before approval"}
                        </button>
                      )}
                    </div>

                    <div className="career-plan-action-list">
                      {(editingActions ? editedActions : proposal.actions).map((action) => (
                        <article className="career-plan-action" key={action.id}>
                          <div className="career-plan-action-meta">
                            <span className={`career-plan-status ${action.priority === "high" ? "negative" : action.priority === "medium" ? "active" : "neutral"}`}>{formatLabel(action.priority)}</span>
                            <span>{formatLabel(action.action_type)}</span>
                          </div>
                          {editingActions ? (
                            <div className="career-plan-edit-grid">
                              <label className="career-plan-field"><span>Title</span><input maxLength={255} value={action.title} onChange={(event) => updateAction(action.id, { title: event.target.value })} /></label>
                              <label className="career-plan-field"><span>Priority</span><select value={action.priority} onChange={(event) => updateAction(action.id, { priority: event.target.value })}><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></label>
                              <label className="career-plan-field career-plan-edit-rationale"><span>Rationale</span><textarea maxLength={2000} rows={4} value={action.rationale} onChange={(event) => updateAction(action.id, { rationale: event.target.value })} /></label>
                            </div>
                          ) : (
                            <>
                              <h4>{action.title}</h4>
                              <p>{action.rationale}</p>
                              {modelNotesByAction.get(action.id) && <p className="career-plan-model-note">AI organization: {modelNotesByAction.get(action.id)}</p>}
                              <details className="career-plan-evidence-details"><summary>Evidence basis</summary><EvidenceLinks evidenceIds={action.evidence_refs} run={selectedRun} /></details>
                              <button className="career-plan-link-button" type="button" onClick={() => void handleExplain("why_action", action.id)} disabled={explainingKey === `why_action:${action.id}`}>
                                {explainingKey === `why_action:${action.id}` ? "Explaining…" : "Why this action?"}
                              </button>
                            </>
                          )}
                        </article>
                      ))}
                    </div>
                  </section>

                  {explanation && (
                    <section className="career-plan-card career-plan-explanation" tabIndex={-1}>
                      <div className="career-plan-section-heading">
                        <div><p className="eyebrow inline-eyebrow">Grounded explanation</p><h3>{formatLabel(explanation.explanation_type)}</h3></div>
                        <button className="career-plan-icon-button" type="button" onClick={() => setExplanation(null)}>Close</button>
                      </div>
                      <p>{explanation.answer}</p>
                      <small>Engine: {formatLabel(explanation.engine)} · Based on run version {explanation.based_on_run_version}</small>
                      {explanation.evidence_refs.length > 0 && <EvidenceLinks evidenceIds={explanation.evidence_refs} run={selectedRun} />}
                    </section>
                  )}

                  {canDecide && (
                    <section className="career-plan-card career-plan-decision-card">
                      <div>
                        <p className="eyebrow inline-eyebrow">Human approval required</p>
                        <h3>Decide what becomes your saved plan</h3>
                        <p>
                          Approval saves your decision and any edits. It does not submit applications, contact recruiters,
                          change external profiles, or purchase anything.
                        </p>
                      </div>
                      <div className="career-plan-decision-actions">
                        <button className="career-plan-danger-button" type="button" disabled={deciding} onClick={() => void handleDecision("rejected")}>{deciding ? "Saving…" : "Reject proposal"}</button>
                        <button className="refresh-button" type="button" disabled={deciding} onClick={() => void handleDecision("approved")}>{deciding ? "Saving…" : editingActions ? "Approve edited plan" : "Approve plan"}</button>
                      </div>
                    </section>
                  )}

                  {["approved", "rejected"].includes(selectedRun.status) && (
                    <section className={`career-plan-card career-plan-final-decision ${selectedRun.status}`}>
                      <p className="eyebrow inline-eyebrow">Decision recorded</p>
                      <h3>{selectedRun.status === "approved" ? "Plan approved" : "Proposal rejected"}</h3>
                      <p>
                        {selectedRun.status === "approved"
                          ? "Your approved plan is saved privately. External actions still remain under your control."
                          : "The proposal remains available in history as a rejected run for audit and comparison."}
                      </p>
                    </section>
                  )}
                </>
              )}

              {selectedRun.audit_events.length > 0 && (
                <details className="career-plan-card career-plan-audit">
                  <summary>Safe workflow audit trail ({selectedRun.audit_events.length} events)</summary>
                  <ol>
                    {selectedRun.audit_events.slice(-12).reverse().map((event) => (
                      <li key={event.id}><strong>{formatLabel(event.event_type)}</strong><span>{formatDate(event.created_at)}</span></li>
                    ))}
                  </ol>
                </details>
              )}
            </>
          )}
        </section>
      </div>
    </main>
  );
}
