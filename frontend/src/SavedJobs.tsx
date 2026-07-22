import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/react";

import {
  createSavedJob,
  deleteSavedJob,
  getSavedJobs,
} from "./api";
import { SafeExternalLink } from "./SafeExternalLink";
import type {
  ExternalJobPosting,
  SavedJob,
  SavedJobCreate,
} from "./types";

const SAVED_JOBS_CHANGED_EVENT = "marketlens:saved-jobs-changed";

type SavedJobsCache = {
  userId: string;
  jobs: SavedJob[];
};

type SavedJobsRequest = {
  userId: string;
  promise: Promise<SavedJob[]>;
};

let savedJobsCache: SavedJobsCache | null = null;
let savedJobsRequest: SavedJobsRequest | null = null;

function savedJobKey(
  job: Pick<SavedJobCreate, "source" | "source_job_id">,
): string {
  return `${job.source}:${job.source_job_id ?? ""}`;
}

function isExternalJobSaved(
  jobs: SavedJob[],
  job: ExternalJobPosting,
): boolean {
  const externalJobKey = savedJobKey({
    source: job.source,
    source_job_id: job.id,
  });

  return jobs.some(
    (savedJob) => savedJobKey(savedJob) === externalJobKey,
  );
}

function updateSavedJobsCache(
  userId: string,
  jobs: SavedJob[],
): void {
  savedJobsCache = {
    userId,
    jobs,
  };
}

async function loadSavedJobsWithCache(
  token: string,
  userId: string,
  forceRefresh = false,
): Promise<SavedJob[]> {
  if (
    !forceRefresh &&
    savedJobsCache?.userId === userId
  ) {
    return savedJobsCache.jobs;
  }

  if (
    !forceRefresh &&
    savedJobsRequest?.userId === userId
  ) {
    return savedJobsRequest.promise;
  }

  const request = getSavedJobs(token)
    .then((jobs) => {
      updateSavedJobsCache(userId, jobs);
      return jobs;
    })
    .finally(() => {
      if (savedJobsRequest?.promise === request) {
        savedJobsRequest = null;
      }
    });

  savedJobsRequest = {
    userId,
    promise: request,
  };

  return request;
}

function notifySavedJobsChanged(): void {
  window.dispatchEvent(
    new Event(SAVED_JOBS_CHANGED_EVENT),
  );
}

export function SaveExternalJobButton({
  job,
}: {
  job: ExternalJobPosting;
}) {
  const {
    getToken,
    isLoaded,
    isSignedIn,
    userId,
  } = useAuth();

  const [status, setStatus] = useState<
    "idle" | "checking" | "saving" | "saved" | "error"
  >("idle");

  useEffect(() => {
    let cancelled = false;

    if (!isLoaded) {
      return;
    }

    if (!isSignedIn || !userId) {
      setStatus("idle");
      return;
    }

    async function checkSavedStatus() {
      try {
        setStatus("checking");

        const token = await getToken();
        if (!token) {
          throw new Error(
            "No Clerk session token was available.",
          );
        }

        const savedJobs = await loadSavedJobsWithCache(
          token,
          userId,
        );

        if (!cancelled) {
          setStatus(
            isExternalJobSaved(savedJobs, job)
              ? "saved"
              : "idle",
          );
        }
      } catch {
        if (!cancelled) {
          setStatus("error");
        }
      }
    }

    const handleSavedJobsChanged = () => {
      const cacheSnapshot = savedJobsCache;

      if (!cacheSnapshot || cacheSnapshot.userId !== userId) {
        return;
      }

      setStatus(
        isExternalJobSaved(cacheSnapshot.jobs, job)
          ? "saved"
          : "idle",
      );
    };

    void checkSavedStatus();

    window.addEventListener(
      SAVED_JOBS_CHANGED_EVENT,
      handleSavedJobsChanged,
    );

    return () => {
      cancelled = true;
      window.removeEventListener(
        SAVED_JOBS_CHANGED_EVENT,
        handleSavedJobsChanged,
      );
    };
  }, [
    getToken,
    isLoaded,
    isSignedIn,
    job,
    userId,
  ]);

  async function handleSave() {
    if (!userId) {
      return;
    }

    try {
      setStatus("saving");

      const token = await getToken();
      if (!token) {
        throw new Error(
          "No Clerk session token was available.",
        );
      }

      const savedJob = await createSavedJob(token, {
        source: job.source,
        source_job_id: job.id,
        company: job.company,
        title: job.title,
        location: job.location,
        description: job.description,
        apply_url: job.apply_url,
      });

      const cacheSnapshot = savedJobsCache;
      const currentJobs =
        cacheSnapshot && cacheSnapshot.userId === userId
          ? cacheSnapshot.jobs
          : [];

      const alreadyCached = currentJobs.some(
        (existingJob) => existingJob.id === savedJob.id,
      );

      updateSavedJobsCache(
        userId,
        alreadyCached
          ? currentJobs
          : [savedJob, ...currentJobs],
      );

      setStatus("saved");
      notifySavedJobsChanged();
    } catch {
      setStatus("error");
    }
  }

  if (!isLoaded) {
    return (
      <button
        className="refresh-button saved-job-button"
        disabled
        type="button"
      >
        Loading…
      </button>
    );
  }

  if (!isSignedIn) {
    return (
      <button
        className="refresh-button saved-job-button secondary-action-button"
        disabled
        type="button"
      >
        Sign in to save
      </button>
    );
  }

  return (
    <button
      className={`refresh-button saved-job-button ${
        status === "saved" ? "saved-action-button" : ""
      }`}
      disabled={
        status === "checking" ||
        status === "saving" ||
        status === "saved"
      }
      type="button"
      onClick={handleSave}
    >
      {status === "checking"
        ? "Checking…"
        : status === "saving"
          ? "Saving…"
          : status === "saved"
            ? "Saved"
            : status === "error"
              ? "Try saving again"
              : "Save job"}
    </button>
  );
}

export function SavedJobsPanel() {
  const {
    getToken,
    isLoaded,
    isSignedIn,
    userId,
  } = useAuth();

  const [savedJobs, setSavedJobs] = useState<SavedJob[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [deletingJobIds, setDeletingJobIds] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);

  const loadSavedJobs = useCallback(
    async (forceRefresh = false) => {
      if (!isSignedIn || !userId) {
        setSavedJobs([]);
        return;
      }

      try {
        setIsLoading(true);
        setError(null);

        const token = await getToken();
        if (!token) {
          throw new Error(
            "No Clerk session token was available.",
          );
        }

        const jobs = await loadSavedJobsWithCache(
          token,
          userId,
          forceRefresh,
        );

        setSavedJobs(jobs);
      } catch (loadError) {
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Could not load saved jobs.",
        );
      } finally {
        setIsLoading(false);
      }
    },
    [getToken, isSignedIn, userId],
  );

  useEffect(() => {
    if (!isLoaded) {
      return;
    }

    if (!isSignedIn || !userId) {
      savedJobsCache = null;
      savedJobsRequest = null;
      setSavedJobs([]);
      setError(null);
      return;
    }

    void loadSavedJobs();

    const handleSavedJobsChanged = () => {
      const cacheSnapshot = savedJobsCache;

      if (cacheSnapshot && cacheSnapshot.userId === userId) {
        setSavedJobs(cacheSnapshot.jobs);
        return;
      }

      void loadSavedJobs(true);
    };

    window.addEventListener(
      SAVED_JOBS_CHANGED_EVENT,
      handleSavedJobsChanged,
    );

    return () => {
      window.removeEventListener(
        SAVED_JOBS_CHANGED_EVENT,
        handleSavedJobsChanged,
      );
    };
  }, [
    isLoaded,
    isSignedIn,
    loadSavedJobs,
    userId,
  ]);

  async function handleDelete(savedJobId: number) {
    if (!userId) {
      return;
    }

    try {
      setDeletingJobIds((currentIds) => [
        ...currentIds,
        savedJobId,
      ]);
      setError(null);

      const token = await getToken();
      if (!token) {
        throw new Error(
          "No Clerk session token was available.",
        );
      }

      await deleteSavedJob(token, savedJobId);

      const updatedJobs = savedJobs.filter(
        (job) => job.id !== savedJobId,
      );

      updateSavedJobsCache(userId, updatedJobs);
      setSavedJobs(updatedJobs);
      notifySavedJobsChanged();
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : "Could not delete that saved job.",
      );
    } finally {
      setDeletingJobIds((currentIds) =>
        currentIds.filter((id) => id !== savedJobId),
      );
    }
  }

  if (!isLoaded) {
    return null;
  }

  if (!isSignedIn) {
    return (
      <section className="report-card saved-jobs-panel">
        <p className="eyebrow inline-eyebrow">
          Private workspace
        </p>
        <h3>Your saved jobs</h3>
        <p className="helper-text">
          Sign in to save job postings privately to your account.
        </p>
      </section>
    );
  }

  return (
    <section className="report-card saved-jobs-panel">
      <div className="gap-group-header">
        <div>
          <p className="eyebrow inline-eyebrow">
            Private workspace
          </p>
          <h3>Your saved jobs</h3>
        </div>

        <span className="status-badge status-demonstrated">
          {savedJobs.length} saved
        </span>
      </div>

      {error && (
        <div className="error-box compact-error">
          <strong>Saved-jobs error</strong>
          <p>{error}</p>
        </div>
      )}

      {isLoading ? (
        <p className="helper-text">
          Loading your saved jobs…
        </p>
      ) : savedJobs.length === 0 ? (
        <div className="empty-state saved-jobs-empty-state">
          <h3>No saved jobs yet</h3>
          <p>Use the Save job button on a searched posting.</p>
        </div>
      ) : (
        <div className="action-list saved-jobs-list">
          {savedJobs.map((job) => (
            <article className="action-row" key={job.id}>
              <span className="status-badge status-mentioned">
                {job.source}
              </span>

              <div>
                <div className="gap-group-header">
                  <h4>
                    {job.company} — {job.title}
                  </h4>

                  <button
                    className="refresh-button saved-job-button delete-action-button"
                    disabled={deletingJobIds.includes(job.id)}
                    type="button"
                    onClick={() => void handleDelete(job.id)}
                  >
                    {deletingJobIds.includes(job.id)
                      ? "Deleting…"
                      : "Delete"}
                  </button>
                </div>

                <p>
                  {job.location ?? "Location not listed"}
                  {job.apply_url && (
                    <>
                      {" · "}
                      <SafeExternalLink url={job.apply_url}>
                        Open posting
                      </SafeExternalLink>
                    </>
                  )}
                </p>

                <p className="helper-text saved-date">
                  Saved{" "}
                  {new Date(
                    job.created_at,
                  ).toLocaleDateString()}
                </p>

                <div className="pill-row compact">
                  {job.extracted_skills
                    .slice(0, 6)
                    .map((skill) => (
                      <span
                        className="skill-pill"
                        key={skill}
                      >
                        {skill}
                      </span>
                    ))}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
