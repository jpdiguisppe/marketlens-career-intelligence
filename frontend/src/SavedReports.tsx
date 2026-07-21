import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/react";

import { createSavedReport, deleteSavedReport, getSavedReports } from "./api";
import type {
  SavedReport,
  SavedReportCreate,
  SavedReportJobContext,
  SavedReportSummary,
  SmartFitAnalysisResponse,
} from "./types";

const SAVED_REPORTS_CHANGED_EVENT = "marketlens:saved-reports-changed";

function formatLabel(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function reportSummaryFromAnalysis(
  analysis: SmartFitAnalysisResponse,
): SavedReportSummary {
  return {
    fit_summary: analysis.fit_summary,
    report_summary: analysis.report_summary,
    category_coverage: analysis.category_coverage,
    coaching_actions: analysis.coaching_actions.map((action) => ({
      action_type: action.action_type,
      priority: action.priority,
      title: action.title,
      skill: action.skill,
      category: action.category,
      advice: action.advice,
    })),
    gap_groups: analysis.gap_groups,
    strong_matches: analysis.strong_matches,
    related_matches: analysis.related_matches,
    important_gaps: analysis.important_gaps,
    recommendations: analysis.recommendations,
    limitations: analysis.limitations,
    analysis_engine: analysis.analysis_engine,
    model_assisted_status: analysis.model_assisted_status,
  };
}

function notifySavedReportsChanged(): void {
  window.dispatchEvent(new Event(SAVED_REPORTS_CHANGED_EVENT));
}

export function SaveSmartFitReportButton({
  analysis,
  job,
}: {
  analysis: SmartFitAnalysisResponse;
  job: SavedReportJobContext;
}) {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [status, setStatus] = useState<
    "idle" | "saving" | "saved" | "error"
  >("idle");

  useEffect(() => {
    setStatus("idle");
  }, [
    analysis,
    job.apply_url,
    job.company,
    job.location,
    job.source,
    job.source_job_id,
    job.title,
  ]);

  async function handleSave() {
    try {
      setStatus("saving");

      const token = await getToken();
      if (!token) {
        throw new Error("No Clerk session token was available.");
      }

      const payload: SavedReportCreate = {
        ...job,
        summary: reportSummaryFromAnalysis(analysis),
      };

      await createSavedReport(token, payload);
      setStatus("saved");
      notifySavedReportsChanged();
    } catch {
      setStatus("error");
    }
  }

  if (!isLoaded) {
    return (
      <button className="refresh-button saved-job-button" disabled>
        Loading…
      </button>
    );
  }

  if (!isSignedIn) {
    return (
      <button
        className="refresh-button saved-job-button secondary-action-button"
        disabled
      >
        Sign in to save report
      </button>
    );
  }

  return (
    <button
      className={`refresh-button saved-job-button ${
        status === "saved" ? "saved-action-button" : ""
      }`}
      disabled={status === "saving" || status === "saved"}
      type="button"
      onClick={() => void handleSave()}
    >
      {status === "saving"
        ? "Saving report…"
        : status === "saved"
          ? "Report saved"
          : status === "error"
            ? "Try saving report again"
            : "Save Smart Fit report"}
    </button>
  );
}

export function SavedReportsPanel() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [reports, setReports] = useState<SavedReport[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [deletingIds, setDeletingIds] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);

  const loadReports = useCallback(async () => {
    if (!isSignedIn) {
      setReports([]);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      const token = await getToken();
      if (!token) {
        throw new Error("No Clerk session token was available.");
      }

      setReports(await getSavedReports(token));
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Could not load saved reports.",
      );
    } finally {
      setIsLoading(false);
    }
  }, [getToken, isSignedIn]);

  useEffect(() => {
    if (!isLoaded) {
      return;
    }

    void loadReports();

    const handleChanged = () => void loadReports();
    window.addEventListener(SAVED_REPORTS_CHANGED_EVENT, handleChanged);

    return () => {
      window.removeEventListener(SAVED_REPORTS_CHANGED_EVENT, handleChanged);
    };
  }, [isLoaded, loadReports]);

  async function handleDelete(reportId: number) {
    try {
      setDeletingIds((ids) => [...ids, reportId]);
      setError(null);

      const token = await getToken();
      if (!token) {
        throw new Error("No Clerk session token was available.");
      }

      await deleteSavedReport(token, reportId);
      setReports((current) =>
        current.filter((report) => report.id !== reportId),
      );
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : "Could not delete that report.",
      );
    } finally {
      setDeletingIds((ids) => ids.filter((id) => id !== reportId));
    }
  }

  if (!isLoaded) {
    return null;
  }

  if (!isSignedIn) {
    return (
      <section className="report-card saved-reports-panel">
        <p className="eyebrow inline-eyebrow">Private workspace</p>
        <h3>Your saved Smart Fit reports</h3>
        <p className="helper-text">
          Sign in to save analysis summaries privately. Raw résumé text is not
          stored with these reports.
        </p>
      </section>
    );
  }

  return (
    <section className="report-card saved-reports-panel">
      <div className="gap-group-header">
        <div>
          <p className="eyebrow inline-eyebrow">Private workspace</p>
          <h3>Your saved Smart Fit reports</h3>
        </div>
        <span className="status-badge status-demonstrated">
          {reports.length} saved
        </span>
      </div>

      <p className="helper-text">
        Saved reports contain the fit summary, gaps, and coaching actions—not
        the raw résumé or full job description.
      </p>

      {error && (
        <div className="error-box compact-error">
          <strong>Saved-reports error</strong>
          <p>{error}</p>
        </div>
      )}

      {isLoading ? (
        <p className="helper-text">Loading your saved reports…</p>
      ) : reports.length === 0 ? (
        <div className="empty-state saved-jobs-empty-state">
          <h3>No saved reports yet</h3>
          <p>Run Smart Fit, then save the result from the report area.</p>
        </div>
      ) : (
        <div className="action-list saved-reports-list">
          {reports.map((report) => (
            <article className="action-row" key={report.id}>
              <span className="priority-badge priority-high">
                {report.summary.fit_summary.score}%
              </span>

              <div>
                <div className="gap-group-header">
                  <div>
                    <h4>
                      {report.company
                        ? `${report.company} — ${report.title}`
                        : report.title}
                    </h4>
                    <p>
                      {formatLabel(report.summary.fit_summary.band)} ·{" "}
                      {report.summary.fit_summary.headline}
                    </p>
                  </div>

                  <button
                    className="refresh-button saved-job-button delete-action-button"
                    disabled={deletingIds.includes(report.id)}
                    type="button"
                    onClick={() => void handleDelete(report.id)}
                  >
                    {deletingIds.includes(report.id) ? "Deleting…" : "Delete"}
                  </button>
                </div>

                <p className="helper-text saved-date">
                  Saved {new Date(report.created_at).toLocaleDateString()}
                  {report.location ? ` · ${report.location}` : ""}
                  {report.apply_url && (
                    <>
                      {" · "}
                      <a
                        href={report.apply_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open posting
                      </a>
                    </>
                  )}
                </p>

                <details className="details-panel saved-report-details">
                  <summary>Open saved report</summary>

                  <div className="smart-section">
                    <h4>Coach summary</h4>
                    <ul className="summary-list">
                      {report.summary.report_summary.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="analysis-grid">
                    <div className="analysis-card">
                      <h3>Strong matches</h3>
                      <p>
                        {report.summary.strong_matches
                          .slice(0, 6)
                          .join(", ") || "No strong matches recorded."}
                      </p>
                    </div>
                    <div className="analysis-card">
                      <h3>Important gaps</h3>
                      <p>
                        {report.summary.important_gaps
                          .slice(0, 6)
                          .join(", ") || "No important gaps recorded."}
                      </p>
                    </div>
                  </div>

                  {report.summary.coaching_actions.length > 0 && (
                    <div className="smart-section">
                      <h4>Best next actions</h4>
                      <div className="action-list">
                        {report.summary.coaching_actions
                          .slice(0, 3)
                          .map((action) => (
                            <article
                              className="action-row"
                              key={`${action.action_type}-${action.title}`}
                            >
                              <span
                                className={`priority-badge priority-${action.priority.toLowerCase()}`}
                              >
                                {action.priority}
                              </span>
                              <div>
                                <h4>{action.title}</h4>
                                <p>{action.advice}</p>
                              </div>
                            </article>
                          ))}
                      </div>
                    </div>
                  )}
                </details>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
