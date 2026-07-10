import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import {
  analyzeResume,
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

  return (
    <section className="panel panel-wide resume-panel">
      <div className="panel-header align-start">
        <div>
          <h2>Resume Gap Analysis</h2>
          <p className="panel-subtitle">
            Paste resume text and compare it against the skills showing up in your saved job postings.
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
            <span>Target role category</span>
            <select
              id="target-role-category"
              className="select-input"
              value={targetRoleCategory}
              onChange={(event) => setTargetRoleCategory(event.target.value)}
            >
              <option value="">All saved postings</option>
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
            {isAnalyzing ? "Analyzing..." : "Analyze resume"}
          </button>
        </div>
      </form>

      {!hasJobs && (
        <div className="notice-box">
          Import or add job postings first so MarketLens has target skills to compare against.
        </div>
      )}

      {analysisError && (
        <div className="error-box compact-error">
          <strong>Could not analyze resume.</strong>
          <p>{analysisError}</p>
        </div>
      )}

      {analysis && (
        <div className="analysis-results">
          <div className="score-card">
            <span>Match Score</span>
            <strong>{analysis.match_percentage}%</strong>
            <p>
              Compared against {analysis.postings_analyzed} posting
              {analysis.postings_analyzed === 1 ? "" : "s"}
              {analysis.target_role_category ? ` in ${analysis.target_role_category}` : " across all roles"}.
            </p>
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
      )}
    </section>
  );
}

function JobTable({ jobs }: { jobs: JobPosting[] }) {
  return (
    <section className="panel panel-wide">
      <div className="panel-header">
        <h2>Saved Job Postings</h2>
        <span>{jobs.length} postings</span>
      </div>

      {jobs.length === 0 ? (
        <div className="empty-state">
          <h3>No job postings yet</h3>
          <p>
            Import the sample CSV from the FastAPI docs, then refresh this dashboard.
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
          : "Something went wrong while loading dashboard data.",
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
          <h1>Job Skill Dashboard</h1>
          <p className="hero-copy">
            Analyze saved job postings, identify repeated skills, and compare signals by
            company and role category.
          </p>
        </div>
        <button className="refresh-button" onClick={loadDashboardData} disabled={isLoading}>
          {isLoading ? "Loading..." : "Refresh dashboard"}
        </button>
      </section>

      {errorMessage && (
        <section className="error-box">
          <strong>Could not load backend data.</strong>
          <p>{errorMessage}</p>
          <p>Make sure FastAPI is running at http://127.0.0.1:8000.</p>
        </section>
      )}

      <section className="stats-grid">
        <div className="stat-card">
          <span>Saved Postings</span>
          <strong>{dashboardData.jobs.length}</strong>
        </div>
        <div className="stat-card">
          <span>Unique Skills</span>
          <strong>{uniqueSkillCount}</strong>
        </div>
        <div className="stat-card">
          <span>Top Skill</span>
          <strong>{getTopSkillName(dashboardData.topSkills)}</strong>
        </div>
      </section>

      <section className="dashboard-grid">
        <ResumeAnalyzer hasJobs={dashboardData.jobs.length > 0} roleCategories={roleCategories} />
        <SkillList title="Top Skills Overall" skills={dashboardData.topSkills} />
        <GroupedSkillPanel title="Skills by Company" groups={dashboardData.skillsByCompany} />
        <GroupedSkillPanel title="Skills by Role Category" groups={dashboardData.skillsByRole} />
        <JobTable jobs={dashboardData.jobs} />
      </section>
    </main>
  );
}

export default App;
