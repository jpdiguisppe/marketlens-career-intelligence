import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import {
  analyzeResume,
  analyzeSmartFit,
  getJobPostings,
  getTopSkills,
  getTopSkillsByCompany,
  getTopSkillsByRole,
} from "./api";
import type {
  GroupedSkillCounts,
  JobPosting,
  ResumeAnalysisResponse,
  SkillCounts,
  SmartFitAnalysisResponse,
} from "./types";

type DashboardData = {
  jobs: JobPosting[];
  topSkills: SkillCounts;
  skillsByCompany: GroupedSkillCounts;
  skillsByRole: GroupedSkillCounts;
};

type SkillEntry = [string, number];

const emptyDashboardData: DashboardData = {
  jobs: [],
  topSkills: {},
  skillsByCompany: {},
  skillsByRole: {},
};

function sortSkillCounts(skillCounts: SkillCounts): SkillEntry[] {
  return Object.entries(skillCounts).sort((a, b) => b[1] - a[1]);
}

function countUniqueSkills(jobs: JobPosting[]): number {
  const uniqueSkills = new Set<string>();

  jobs.forEach((job) => {
    job.extracted_skills.forEach((skill) => uniqueSkills.add(skill));
  });

  return uniqueSkills.size;
}

function getTopSkillName(topSkills: SkillCounts): string {
  const topSkill = sortSkillCounts(topSkills)[0];
  return topSkill ? topSkill[0] : "None yet";
}

function splitPastedJobDescriptions(text: string): string[] {
  return text
    .split(/\n\s*-{3,}\s*\n/g)
    .map((description) => description.trim())
    .filter(Boolean);
}

function formatLabel(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function SkillPills({ skills, emptyText }: { skills: string[]; emptyText: string }) {
  if (skills.length === 0) {
    return <p className="empty-text">{emptyText}</p>;
  }

  return (
    <div className="pill-row">
      {skills.map((skill) => (
        <span className="skill-pill" key={skill}>
          {skill}
        </span>
      ))}
    </div>
  );
}

function SkillList({ title, skills }: { title: string; skills: SkillCounts }) {
  const sortedSkills = sortSkillCounts(skills);
  const maxCount = sortedSkills[0]?.[1] ?? 1;

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>{title}</h2>
      </div>

      {sortedSkills.length === 0 ? (
        <p className="empty-text">No skill data yet.</p>
      ) : (
        <div className="skill-list">
          {sortedSkills.map(([skill, count]) => (
            <div className="skill-row" key={skill}>
              <div className="skill-row-top">
                <span>{skill}</span>
                <strong>{count}</strong>
              </div>
              <div className="bar-track">
                <div
                  className="bar-fill"
                  style={{ width: `${Math.max((count / maxCount) * 100, 8)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function GroupedSkillPanel({ title, groups }: { title: string; groups: GroupedSkillCounts }) {
  const groupEntries = Object.entries(groups).sort(([a], [b]) => a.localeCompare(b));

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>{title}</h2>
      </div>

      {groupEntries.length === 0 ? (
        <p className="empty-text">No grouped skill data yet.</p>
      ) : (
        <div className="group-grid">
          {groupEntries.map(([groupName, skillCounts]) => (
            <div className="group-card" key={groupName}>
              <h3>{groupName}</h3>
              <div className="pill-row">
                {sortSkillCounts(skillCounts)
                  .slice(0, 6)
                  .map(([skill, count]) => (
                    <span className="skill-pill" key={skill}>
                      {skill} <strong>{count}</strong>
                    </span>
                  ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function AnalysisResults({
  analysis,
  comparisonText,
}: {
  analysis: ResumeAnalysisResponse;
  comparisonText: string;
}) {
  return (
    <div className="analysis-results">
      <div className="score-card">
        <span>Match Score</span>
        <strong>{analysis.match_percentage}%</strong>
        <p>{comparisonText}</p>
      </div>

      <div className="analysis-grid">
        <div className="analysis-card">
          <h3>Matched Skills</h3>
          <SkillPills skills={analysis.matched_skills} emptyText="No matched skills found yet." />
        </div>

        <div className="analysis-card">
          <h3>Missing Skills</h3>
          <SkillPills skills={analysis.missing_skills} emptyText="No missing target skills found." />
        </div>

        <div className="analysis-card">
          <h3>Resume Skills Found</h3>
          <SkillPills skills={analysis.resume_skills} emptyText="No known skills found in resume text." />
        </div>

        <div className="analysis-card priority-card">
          <h3>Learning Priorities</h3>
          <SkillPills skills={analysis.learning_priorities} emptyText="No learning priorities yet." />
        </div>
      </div>
    </div>
  );
}

function SmartFitResults({
  analysis,
  comparisonText,
}: {
  analysis: SmartFitAnalysisResponse;
  comparisonText: string;
}) {
  const highSignalRequirements = analysis.requirement_assessments
    .filter((assessment) => assessment.weight >= 0.5)
    .slice(0, 6);

  return (
    <div className="analysis-results smart-fit-results">
      <div className="score-card smart-score-card">
        <span>Smart Fit Score</span>
        <strong>{analysis.fit_summary.score}%</strong>
        <p>{analysis.fit_summary.headline}</p>
        <small>
          {formatLabel(analysis.fit_summary.band)} · Confidence {Math.round(analysis.fit_summary.confidence * 100)}% · {comparisonText}
        </small>
      </div>

      {analysis.document_quality.warnings.length > 0 && (
        <div className="notice-box smart-warning-box">
          <strong>Document quality notes</strong>
          <ul>
            {analysis.document_quality.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="analysis-grid">
        <div className="analysis-card">
          <h3>Strong Evidence</h3>
          <SkillPills skills={analysis.strong_matches} emptyText="No strong matches found yet." />
        </div>

        <div className="analysis-card priority-card">
          <h3>Under-Sold Experience</h3>
          <SkillPills skills={analysis.under_sold_experience} emptyText="No under-sold skills found." />
        </div>

        <div className="analysis-card">
          <h3>Important Gaps</h3>
          <SkillPills skills={analysis.important_gaps} emptyText="No high-priority skill gaps found." />
        </div>

        <div className="analysis-card">
          <h3>Lower-Priority Noise</h3>
          <SkillPills skills={analysis.lower_priority_items} emptyText="No lower-priority missing skills found." />
        </div>
      </div>

      <div className="smart-section">
        <h3>Category Coverage</h3>
        <div className="category-grid">
          {analysis.category_coverage.map((coverage) => (
            <div className="category-card" key={coverage.category}>
              <div className="category-card-header">
                <strong>{formatLabel(coverage.category)}</strong>
                <span>{coverage.score}%</span>
              </div>
              <div className="bar-track">
                <div className="bar-fill" style={{ width: `${Math.max(coverage.score, 6)}%` }} />
              </div>
              <p>{coverage.summary}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="smart-section">
        <h3>Coaching Actions</h3>
        <div className="coaching-grid">
          {analysis.coaching_actions.map((action) => (
            <article className="coaching-card" key={`${action.action_type}-${action.title}-${action.skill ?? "none"}`}>
              <div className="coaching-card-header">
                <span className={`priority-badge priority-${action.priority.toLowerCase()}`}>
                  {action.priority}
                </span>
                <span>{formatLabel(action.action_type)}</span>
              </div>
              <h4>{action.title}</h4>
              <p>{action.advice}</p>
              {action.source_evidence.length > 0 && (
                <blockquote>{action.source_evidence[0]}</blockquote>
              )}
            </article>
          ))}
        </div>
      </div>

      {analysis.hard_requirements.length > 0 && (
        <div className="smart-section">
          <h3>Hard Requirement Checks</h3>
          <div className="requirement-list">
            {analysis.hard_requirements.map((requirement) => (
              <div className="requirement-row" key={`${requirement.category}-${requirement.source_text}`}>
                <span className={`status-badge status-${requirement.status}`}>
                  {formatLabel(requirement.status)}
                </span>
                <div>
                  <strong>{formatLabel(requirement.category)}</strong>
                  <p>{requirement.requirement}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="smart-section">
        <h3>Evidence-Backed Requirement Readout</h3>
        <div className="requirement-list">
          {highSignalRequirements.map((assessment) => (
            <div className="requirement-row" key={`${assessment.skill}-${assessment.requirement_type}`}>
              <span className={`status-badge status-${assessment.status}`}>
                {formatLabel(assessment.status)}
              </span>
              <div>
                <strong>{assessment.skill}</strong>
                <p>{assessment.explanation}</p>
                {assessment.resume_evidence[0] && <blockquote>{assessment.resume_evidence[0]}</blockquote>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function CustomAnalysisPanel() {
  const [resumeText, setResumeText] = useState("");
  const [jobDescriptionsText, setJobDescriptionsText] = useState("");
  const [analysis, setAnalysis] = useState<SmartFitAnalysisResponse | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const jobDescriptions = splitPastedJobDescriptions(jobDescriptionsText);

    if (!resumeText.trim()) {
      setAnalysisError("Paste resume text before running the analysis.");
      return;
    }

    if (jobDescriptions.length === 0) {
      setAnalysisError("Paste at least one job description before running the analysis.");
      return;
    }

    try {
      setIsAnalyzing(true);
      setAnalysisError(null);

      const result = await analyzeSmartFit({
        resume_text: resumeText,
        job_description: jobDescriptions.join("\n\n---\n\n"),
      });

      setAnalysis(result);
    } catch (error) {
      setAnalysis(null);
      setAnalysisError(
        error instanceof Error
          ? error.message
          : "Something went wrong while analyzing the pasted job descriptions.",
      );
    } finally {
      setIsAnalyzing(false);
    }
  }

  return (
    <section className="panel panel-wide custom-analysis-panel">
      <div className="panel-header align-start">
        <div>
          <p className="eyebrow inline-eyebrow">Start here</p>
          <h2>Analyze a Resume Against Real Job Descriptions</h2>
          <p className="panel-subtitle">
            Paste resume-style text and job description text to get a non-saved Smart Fit report.
            Text is sent to the backend for analysis, but it is not saved to the shared database.
          </p>
        </div>
      </div>

      <form className="resume-form" onSubmit={handleSubmit}>
        <div className="form-grid">
          <label className="form-control" htmlFor="custom-resume-text">
            <span>Resume text</span>
            <textarea
              id="custom-resume-text"
              className="resume-textarea"
              placeholder="Paste resume bullets, project descriptions, coursework, and skills here. Do not include sensitive personal information."
              value={resumeText}
              onChange={(event) => setResumeText(event.target.value)}
            />
          </label>

          <label className="form-control" htmlFor="custom-job-descriptions">
            <span>Job description text</span>
            <textarea
              id="custom-job-descriptions"
              className="resume-textarea"
              placeholder="Paste a job description here. To compare multiple postings as one target profile, separate each one with a line containing ---"
              value={jobDescriptionsText}
              onChange={(event) => setJobDescriptionsText(event.target.value)}
            />
          </label>
        </div>

        <div className="form-footer">
          <p className="helper-text">
            Smart Fit checks evidence, requirement priority, category coverage, and coaching actions.
            Avoid sensitive personal information.
          </p>
          <button className="refresh-button analyze-button" disabled={isAnalyzing} type="submit">
            {isAnalyzing ? "Analyzing..." : "Analyze fit"}
          </button>
        </div>
      </form>

      {analysisError && (
        <div className="error-box compact-error">
          <strong>Could not analyze pasted jobs.</strong>
          <p>{analysisError}</p>
        </div>
      )}

      {analysis && (
        <SmartFitResults
          analysis={analysis}
          comparisonText="Nothing was saved to the shared database."
        />
      )}
    </section>
  );
}

function ResumeAnalyzer({
  hasJobs,
  roleCategories,
}: {
  hasJobs: boolean;
  roleCategories: string[];
}) {
  const [resumeText, setResumeText] = useState("");
  const [targetRoleCategory, setTargetRoleCategory] = useState("");
  const [analysis, setAnalysis] = useState<ResumeAnalysisResponse | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!resumeText.trim()) {
      setAnalysisError("Paste resume text before running the analysis.");
      return;
    }

    try {
      setIsAnalyzing(true);
      setAnalysisError(null);

      const result = await analyzeResume({
        resume_text: resumeText,
        target_role_category: targetRoleCategory || null,
      });

      setAnalysis(result);
    } catch (error) {
      setAnalysis(null);
      setAnalysisError(
        error instanceof Error
          ? error.message
          : "Something went wrong while analyzing the resume.",
      );
    } finally {
      setIsAnalyzing(false);
    }
  }

  const comparisonText = analysis
    ? `Compared against ${analysis.postings_analyzed} sample posting${
        analysis.postings_analyzed === 1 ? "" : "s"
      }${analysis.target_role_category ? ` in ${analysis.target_role_category}` : " across all roles"}.`
    : "";

  return (
    <section className="panel panel-wide resume-panel">
      <div className="panel-header align-start">
        <div>
          <h2>Compare Against the Sample Dataset</h2>
          <p className="panel-subtitle">
            This secondary tool compares resume text against the saved sample postings below.
            Use the custom Smart Fit analysis above for your own job descriptions.
          </p>
        </div>
      </div>

      <form className="resume-form" onSubmit={handleSubmit}>
        <label className="form-label" htmlFor="resume-text">
          Resume text
        </label>
        <textarea
          id="resume-text"
          className="resume-textarea"
          placeholder="Paste resume bullets, project descriptions, coursework, and skills here..."
          value={resumeText}
          onChange={(event) => setResumeText(event.target.value)}
        />

        <div className="form-row">
          <label className="form-control" htmlFor="target-role-category">
            <span>Sample role category</span>
            <select
              id="target-role-category"
              className="select-input"
              value={targetRoleCategory}
              onChange={(event) => setTargetRoleCategory(event.target.value)}
            >
              <option value="">All sample postings</option>
              {roleCategories.map((roleCategory) => (
                <option key={roleCategory} value={roleCategory}>
                  {roleCategory}
                </option>
              ))}
            </select>
          </label>

          <button
            className="refresh-button analyze-button"
            disabled={isAnalyzing || !hasJobs}
            type="submit"
          >
            {isAnalyzing ? "Analyzing..." : "Analyze sample dataset"}
          </button>
        </div>
      </form>

      {!hasJobs && (
        <div className="notice-box">
          Sample postings are not loaded yet. Use the custom analysis above to compare pasted postings without saving anything.
        </div>
      )}

      {analysisError && (
        <div className="error-box compact-error">
          <strong>Could not analyze resume.</strong>
          <p>{analysisError}</p>
        </div>
      )}

      {analysis && <AnalysisResults analysis={analysis} comparisonText={comparisonText} />}
    </section>
  );
}

function SampleDatasetSummary({
  jobs,
  uniqueSkillCount,
  topSkillName,
  isLoading,
  onRefresh,
}: {
  jobs: JobPosting[];
  uniqueSkillCount: number;
  topSkillName: string;
  isLoading: boolean;
  onRefresh: () => void;
}) {
  return (
    <section className="panel panel-wide sample-data-panel">
      <div className="panel-header align-start">
        <div>
          <p className="eyebrow inline-eyebrow">Sample data</p>
          <h2>Sample Market Snapshot</h2>
          <p className="panel-subtitle">
            These numbers come from saved sample postings used to demonstrate market-trend views.
            They are not created by public custom-analysis users.
          </p>
        </div>
        <button className="refresh-button" onClick={onRefresh} disabled={isLoading}>
          {isLoading ? "Loading..." : "Refresh sample data"}
        </button>
      </div>

      <div className="stats-grid sample-stats-grid">
        <div className="stat-card">
          <span>Sample Postings</span>
          <strong>{jobs.length}</strong>
        </div>
        <div className="stat-card">
          <span>Sample Unique Skills</span>
          <strong>{uniqueSkillCount}</strong>
        </div>
        <div className="stat-card">
          <span>Sample Top Skill</span>
          <strong>{topSkillName}</strong>
        </div>
      </div>
    </section>
  );
}

function JobTable({ jobs }: { jobs: JobPosting[] }) {
  return (
    <section className="panel panel-wide">
      <div className="panel-header">
        <h2>Sample Saved Job Postings</h2>
        <span>{jobs.length} sample postings</span>
      </div>

      {jobs.length === 0 ? (
        <div className="empty-state">
          <h3>No sample postings loaded</h3>
          <p>
            The public app can still run custom analysis with pasted job descriptions. Admins can load saved sample postings through the protected API.
          </p>
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Company</th>
                <th>Title</th>
                <th>Role</th>
                <th>Level</th>
                <th>Skills</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id}>
                  <td>{job.company}</td>
                  <td>{job.title}</td>
                  <td>{job.role_category ?? "—"}</td>
                  <td>{job.experience_level ?? "—"}</td>
                  <td>
                    <div className="pill-row compact">
                      {job.extracted_skills.slice(0, 5).map((skill) => (
                        <span className="skill-pill" key={skill}>
                          {skill}
                        </span>
                      ))}
                      {job.extracted_skills.length > 5 && (
                        <span className="more-pill">+{job.extracted_skills.length - 5}</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function App() {
  const [dashboardData, setDashboardData] = useState<DashboardData>(emptyDashboardData);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const uniqueSkillCount = useMemo(
    () => countUniqueSkills(dashboardData.jobs),
    [dashboardData.jobs],
  );

  const roleCategories = useMemo(() => {
    const categories = new Set<string>();

    dashboardData.jobs.forEach((job) => {
      if (job.role_category) {
        categories.add(job.role_category);
      }
    });

    return Array.from(categories).sort((a, b) => a.localeCompare(b));
  }, [dashboardData.jobs]);

  async function loadDashboardData() {
    try {
      setIsLoading(true);
      setErrorMessage(null);

      const [jobs, topSkills, skillsByCompany, skillsByRole] = await Promise.all([
        getJobPostings(),
        getTopSkills(),
        getTopSkillsByCompany(),
        getTopSkillsByRole(),
      ]);

      setDashboardData({
        jobs,
        topSkills,
        skillsByCompany,
        skillsByRole,
      });
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Something went wrong while loading sample market data.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboardData();
  }, []);

  return (
    <main className="app-shell">
      <section className="hero">
        <div>
          <p className="eyebrow">MarketLens Career Intelligence</p>
          <h1>Analyze Your Fit for Real Jobs</h1>
          <p className="hero-copy">
            Compare resume evidence against real job descriptions, identify important gaps,
            and turn noisy postings into a focused learning plan.
          </p>
        </div>
      </section>

      {errorMessage && (
        <section className="error-box">
          <strong>Could not load sample market data.</strong>
          <p>{errorMessage}</p>
          <p>You can still use custom analysis if the API is reachable.</p>
        </section>
      )}

      <section className="dashboard-grid">
        <CustomAnalysisPanel />
        <SampleDatasetSummary
          jobs={dashboardData.jobs}
          uniqueSkillCount={uniqueSkillCount}
          topSkillName={getTopSkillName(dashboardData.topSkills)}
          isLoading={isLoading}
          onRefresh={loadDashboardData}
        />
        <ResumeAnalyzer hasJobs={dashboardData.jobs.length > 0} roleCategories={roleCategories} />
        <SkillList title="Sample Top Skills Overall" skills={dashboardData.topSkills} />
        <GroupedSkillPanel title="Sample Skills by Company" groups={dashboardData.skillsByCompany} />
        <GroupedSkillPanel title="Sample Skills by Role Category" groups={dashboardData.skillsByRole} />
        <JobTable jobs={dashboardData.jobs} />
      </section>
    </main>
  );
}

export default App;
