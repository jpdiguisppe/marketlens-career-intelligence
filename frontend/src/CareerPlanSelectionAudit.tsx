import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@clerk/react";

import {
  CAREER_PLANS_CHANGED_EVENT,
  getCareerPlan,
  listCareerPlans,
} from "./careerPlansApi";
import type {
  CareerPlanRun,
  CareerPlanRunSummary,
  CareerPlanStep,
} from "./careerPlanTypes";
import { SafeExternalLink } from "./SafeExternalLink";
import "./careerPlanSelectionAudit.css";

type SearchCandidate = {
  job_ref: string;
  search_rank: number;
  source: string;
  source_job_id: string;
  company: string;
  title: string;
  location: string | null;
  apply_url: string | null;
  updated_at: string | null;
  extracted_skills: string[];
};

type CandidateExclusion = {
  job_ref: string;
  search_rank: number;
  company: string;
  title: string;
  reason_code: string;
};

type SourceCoverage = {
  provider: string;
  label: string;
  status: string;
  fetched_count: number;
  matched_count: number;
  notes: string[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function parseSearchCandidate(value: unknown): SearchCandidate | null {
  if (!isRecord(value)) return null;
  const jobRef = asString(value.job_ref);
  const company = asString(value.company);
  const title = asString(value.title);
  if (!jobRef || !company || !title) return null;
  return {
    job_ref: jobRef,
    search_rank: asNumber(value.search_rank),
    source: asString(value.source, "unknown"),
    source_job_id: asString(value.source_job_id),
    company,
    title,
    location: typeof value.location === "string" ? value.location : null,
    apply_url: typeof value.apply_url === "string" ? value.apply_url : null,
    updated_at: typeof value.updated_at === "string" ? value.updated_at : null,
    extracted_skills: asStringArray(value.extracted_skills),
  };
}

function parseExclusion(value: unknown): CandidateExclusion | null {
  if (!isRecord(value)) return null;
  const jobRef = asString(value.job_ref);
  const company = asString(value.company);
  const title = asString(value.title);
  const reasonCode = asString(value.reason_code);
  if (!jobRef || !company || !title || !reasonCode) return null;
  return {
    job_ref: jobRef,
    search_rank: asNumber(value.search_rank),
    company,
    title,
    reason_code: reasonCode,
  };
}

function parseCoverage(value: unknown): SourceCoverage | null {
  if (!isRecord(value)) return null;
  const provider = asString(value.provider);
  if (!provider) return null;
  return {
    provider,
    label: asString(value.label, provider),
    status: asString(value.status, "unknown"),
    fetched_count: asNumber(value.fetched_count),
    matched_count: asNumber(value.matched_count),
    notes: asStringArray(value.notes),
  };
}

function latestSelectionStep(run: CareerPlanRun): CareerPlanStep | null {
  return [...run.steps]
    .filter((step) => step.step_name === "select_candidates")
    .sort((left, right) => right.attempt - left.attempt || right.id - left.id)[0] ?? null;
}

function formatLabel(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function CareerPlanSelectionAudit() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [plans, setPlans] = useState<CareerPlanRunSummary[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [run, setRun] = useState<CareerPlanRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const requireToken = useCallback(async () => {
    const token = await getToken();
    if (!token) throw new Error("No Clerk session token was available.");
    return token;
  }, [getToken]);

  const openRun = useCallback(async (runId: number, token?: string) => {
    const resolvedToken = token ?? await requireToken();
    const selectedRun = await getCareerPlan(resolvedToken, runId);
    setSelectedRunId(runId);
    setRun(selectedRun);
  }, [requireToken]);

  const refresh = useCallback(async () => {
    if (!isSignedIn) {
      setPlans([]);
      setRun(null);
      setSelectedRunId(null);
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const token = await requireToken();
      const history = await listCareerPlans(token);
      setPlans(history);
      const preferredRunId = selectedRunId && history.some((item) => item.id === selectedRunId)
        ? selectedRunId
        : history[0]?.id ?? null;
      if (preferredRunId) {
        await openRun(preferredRunId, token);
      } else {
        setRun(null);
        setSelectedRunId(null);
      }
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "Could not load candidate-selection evidence.");
    } finally {
      setLoading(false);
    }
  }, [isSignedIn, openRun, requireToken, selectedRunId]);

  useEffect(() => {
    if (!isLoaded) return;
    void refresh();
  }, [isLoaded, refresh]);

  useEffect(() => {
    const handleChanged = () => void refresh();
    window.addEventListener(CAREER_PLANS_CHANGED_EVENT, handleChanged);
    return () => window.removeEventListener(CAREER_PLANS_CHANGED_EVENT, handleChanged);
  }, [refresh]);

  const selectionStep = run ? latestSelectionStep(run) : null;
  const selectionSummary = selectionStep?.safe_output_summary ?? {};
  const selectedCandidates = useMemo(
    () => (Array.isArray(selectionSummary.selected) ? selectionSummary.selected : [])
      .map(parseSearchCandidate)
      .filter((item): item is SearchCandidate => item !== null),
    [selectionSummary],
  );
  const exclusions = useMemo(
    () => (Array.isArray(selectionSummary.excluded) ? selectionSummary.excluded : [])
      .map(parseExclusion)
      .filter((item): item is CandidateExclusion => item !== null),
    [selectionSummary],
  );
  const consideredCandidates = useMemo(
    () => (run && Array.isArray(run.search_summary.candidates) ? run.search_summary.candidates : [])
      .map(parseSearchCandidate)
      .filter((item): item is SearchCandidate => item !== null),
    [run],
  );
  const sourceCoverage = useMemo(
    () => (run && Array.isArray(run.search_summary.source_coverage) ? run.search_summary.source_coverage : [])
      .map(parseCoverage)
      .filter((item): item is SourceCoverage => item !== null),
    [run],
  );

  if (!isLoaded || !isSignedIn) return null;

  return (
    <section className="career-selection-shell" aria-label="Career Plan candidate selection audit">
      <div className="career-selection-card">
        <div className="career-selection-header">
          <div>
            <p className="eyebrow inline-eyebrow">Deterministic selection audit</p>
            <h2>Inspect every candidate decision before approval</h2>
            <p>
              This panel reads the saved search and <code>select_candidates</code> step summaries.
              It contains safe metadata and deterministic reason codes—not résumé text or job-description text.
            </p>
          </div>
          <button className="career-plan-icon-button" type="button" onClick={() => void refresh()} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh audit"}
          </button>
        </div>

        {error && (
          <div className="error-box compact-error" role="alert">
            <strong>Selection audit error</strong>
            <p>{error}</p>
          </div>
        )}

        <label className="career-selection-plan-picker">
          <span>Saved Career Plan</span>
          <select
            value={selectedRunId ?? ""}
            disabled={loading || plans.length === 0}
            onChange={(event) => {
              const nextId = Number(event.target.value);
              if (Number.isInteger(nextId) && nextId > 0) {
                setLoading(true);
                setError(null);
                void openRun(nextId)
                  .catch((openError) => setError(openError instanceof Error ? openError.message : "Could not open that plan."))
                  .finally(() => setLoading(false));
              }
            }}
          >
            {plans.length === 0 && <option value="">No saved plans</option>}
            {plans.map((plan) => (
              <option value={plan.id} key={plan.id}>
                #{plan.id} · {plan.goal.target_occupation} · {formatLabel(plan.status)}
              </option>
            ))}
          </select>
        </label>

        {!run ? (
          <div className="empty-state career-selection-empty">
            <h3>No plan selected</h3>
            <p>Create and run a Career Plan to produce deterministic selection evidence.</p>
          </div>
        ) : !selectionStep ? (
          <div className="empty-state career-selection-empty">
            <h3>Selection step not completed yet</h3>
            <p>This run is {formatLabel(run.status)}. Refresh after candidate selection commits its safe summary.</p>
          </div>
        ) : (
          <>
            <div className="career-selection-summary-grid">
              <div><span>Considered</span><strong>{consideredCandidates.length}</strong></div>
              <div><span>Selected</span><strong>{selectedCandidates.length}</strong></div>
              <div><span>Excluded</span><strong>{exclusions.length}</strong></div>
              <div><span>Attempt</span><strong>{selectionStep.attempt}</strong></div>
            </div>

            <div className="career-selection-context">
              <span><strong>Query:</strong> {asString(run.search_summary.query, run.goal.target_occupation)}</span>
              <span><strong>Location:</strong> {asString(run.search_summary.location, run.goal.location ?? "Any")}</span>
              <span><strong>Updated:</strong> {formatDate(run.updated_at)}</span>
            </div>

            {sourceCoverage.length > 0 && (
              <details className="career-selection-coverage">
                <summary>Search-provider coverage ({sourceCoverage.length})</summary>
                <div className="career-selection-coverage-grid">
                  {sourceCoverage.map((coverage) => (
                    <article key={coverage.provider}>
                      <div>
                        <strong>{coverage.label}</strong>
                        <span className={`career-selection-coverage-status status-${coverage.status}`}>{formatLabel(coverage.status)}</span>
                      </div>
                      <p>{coverage.fetched_count} fetched · {coverage.matched_count} matched</p>
                      {coverage.notes.length > 0 && <small>{coverage.notes.join(" · ")}</small>}
                    </article>
                  ))}
                </div>
              </details>
            )}

            <div className="career-selection-columns">
              <section>
                <div className="career-selection-section-title">
                  <div><p className="eyebrow inline-eyebrow">Analyzed next</p><h3>Selected candidates</h3></div>
                  <span>{selectedCandidates.length}</span>
                </div>
                {selectedCandidates.length === 0 ? (
                  <p className="career-plan-muted">No candidates were selected for Smart Fit.</p>
                ) : (
                  <div className="career-selection-list">
                    {selectedCandidates.map((candidate) => (
                      <article className="career-selection-item selected" key={candidate.job_ref}>
                        <div className="career-selection-item-heading">
                          <span className="career-selection-rank">#{candidate.search_rank}</span>
                          <span className="career-selection-reason selected">Selected deterministically</span>
                        </div>
                        <h4>{candidate.title}</h4>
                        <p>{candidate.company} · {candidate.location ?? "Location not listed"}</p>
                        <small>{formatLabel(candidate.source)} · {candidate.job_ref}</small>
                        {candidate.extracted_skills.length > 0 && (
                          <div className="career-selection-skills">
                            {candidate.extracted_skills.slice(0, 8).map((skill) => <span key={skill}>{skill}</span>)}
                          </div>
                        )}
                        {candidate.apply_url && <SafeExternalLink url={candidate.apply_url}>Open posting</SafeExternalLink>}
                      </article>
                    ))}
                  </div>
                )}
              </section>

              <section>
                <div className="career-selection-section-title">
                  <div><p className="eyebrow inline-eyebrow">Not analyzed</p><h3>Excluded candidates</h3></div>
                  <span>{exclusions.length}</span>
                </div>
                {exclusions.length === 0 ? (
                  <p className="career-plan-muted">No searched candidates were excluded.</p>
                ) : (
                  <div className="career-selection-list">
                    {exclusions.map((candidate) => (
                      <article className="career-selection-item excluded" key={`${candidate.job_ref}-${candidate.reason_code}`}>
                        <div className="career-selection-item-heading">
                          <span className="career-selection-rank">#{candidate.search_rank}</span>
                          <span className="career-selection-reason excluded">{formatLabel(candidate.reason_code)}</span>
                        </div>
                        <h4>{candidate.title}</h4>
                        <p>{candidate.company}</p>
                        <small>{candidate.job_ref}</small>
                        <p className="career-selection-reason-copy">
                          {candidate.reason_code === "duplicate_posting"
                            ? "This posting duplicated a source-and-job identifier already considered."
                            : candidate.reason_code === "outside_analysis_limit"
                              ? "This posting remained outside the bounded analysis count after search-order and company-diversity selection."
                              : `MarketLens excluded this posting using deterministic reason code ${candidate.reason_code}.`}
                        </p>
                      </article>
                    ))}
                  </div>
                )}
              </section>
            </div>

            <details className="career-selection-considered">
              <summary>All considered search candidates ({consideredCandidates.length})</summary>
              <ol>
                {consideredCandidates.map((candidate) => (
                  <li key={candidate.job_ref}>
                    <span>#{candidate.search_rank}</span>
                    <strong>{candidate.company} — {candidate.title}</strong>
                    <small>{candidate.job_ref}</small>
                  </li>
                ))}
              </ol>
            </details>
          </>
        )}
      </div>
    </section>
  );
}
