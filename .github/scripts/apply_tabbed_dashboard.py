from pathlib import Path


APP_PATH = Path("frontend/src/App.tsx")
STYLES_PATH = Path("frontend/src/styles.css")
SAVED_REPORTS_PATH = Path("frontend/src/SavedReports.tsx")
DOC_PATH = Path("docs/milestone-6-tabbed-dashboard.md")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"Expected exactly one {label} block, found {text.count(old)}.")
    return text.replace(old, new, 1)


app = APP_PATH.read_text()
app = replace_once(
    app,
    'type SkillEntry = [string, number];\n',
    'type SkillEntry = [string, number];\n\n'
    'type AppSection = "smart-fit" | "saved-jobs" | "saved-reports" | "market-data";\n',
    "AppSection insertion",
)

app = replace_once(
    app,
    '''      <div className="private-workspace-grid">\n        <SavedJobsPanel />\n        <SavedReportsPanel />\n      </div>\n\n''',
    '',
    "embedded private workspace",
)

app = replace_once(
    app,
    '''function App() {\n  const [dashboardData, setDashboardData] = useState<DashboardData>(emptyDashboardData);''',
    '''function App() {\n  const [activeSection, setActiveSection] = useState<AppSection>("smart-fit");\n  const [dashboardData, setDashboardData] = useState<DashboardData>(emptyDashboardData);''',
    "active section state",
)

old_dashboard = '''      <section className="dashboard-grid">\n        <CustomAnalysisPanel />\n        <SampleDatasetSummary\n          jobs={dashboardData.jobs}\n          uniqueSkillCount={uniqueSkillCount}\n          topSkillName={getTopSkillName(dashboardData.topSkills)}\n          isLoading={isLoading}\n          onRefresh={loadDashboardData}\n        />\n        <ResumeAnalyzer hasJobs={dashboardData.jobs.length > 0} roleCategories={roleCategories} />\n        <SkillList title="Sample Top Skills Overall" skills={dashboardData.topSkills} />\n        <GroupedSkillPanel title="Sample Skills by Company" groups={dashboardData.skillsByCompany} />\n        <GroupedSkillPanel title="Sample Skills by Role Category" groups={dashboardData.skillsByRole} />\n        <JobTable jobs={dashboardData.jobs} />\n      </section>'''

new_dashboard = '''      <nav className="app-tabs" aria-label="MarketLens sections">\n        <button\n          className={`app-tab ${activeSection === "smart-fit" ? "active" : ""}`}\n          type="button"\n          aria-current={activeSection === "smart-fit" ? "page" : undefined}\n          onClick={() => setActiveSection("smart-fit")}\n        >\n          <span>Smart Fit</span>\n          <small>Search and analyze</small>\n        </button>\n        <button\n          className={`app-tab ${activeSection === "saved-jobs" ? "active" : ""}`}\n          type="button"\n          aria-current={activeSection === "saved-jobs" ? "page" : undefined}\n          onClick={() => setActiveSection("saved-jobs")}\n        >\n          <span>Saved Jobs</span>\n          <small>Your bookmarks</small>\n        </button>\n        <button\n          className={`app-tab ${activeSection === "saved-reports" ? "active" : ""}`}\n          type="button"\n          aria-current={activeSection === "saved-reports" ? "page" : undefined}\n          onClick={() => setActiveSection("saved-reports")}\n        >\n          <span>Saved Reports</span>\n          <small>Your fit history</small>\n        </button>\n        <button\n          className={`app-tab ${activeSection === "market-data" ? "active" : ""}`}\n          type="button"\n          aria-current={activeSection === "market-data" ? "page" : undefined}\n          onClick={() => setActiveSection("market-data")}\n        >\n          <span>Market Data</span>\n          <small>Sample trends</small>\n        </button>\n      </nav>\n\n      <section\n        className="app-tab-panel"\n        aria-label="Smart Fit workspace"\n        hidden={activeSection !== "smart-fit"}\n      >\n        <div className="tab-panel-header">\n          <div>\n            <p className="eyebrow inline-eyebrow">Analyze</p>\n            <h2>Search, compare, and improve your fit</h2>\n            <p>Upload one résumé, then analyze searched jobs or pasted descriptions without losing your work when you switch sections.</p>\n          </div>\n        </div>\n        <section className="dashboard-grid">\n          <CustomAnalysisPanel />\n        </section>\n      </section>\n\n      <section\n        className="app-tab-panel"\n        aria-label="Saved jobs workspace"\n        hidden={activeSection !== "saved-jobs"}\n      >\n        <div className="tab-panel-header">\n          <div>\n            <p className="eyebrow inline-eyebrow">Private workspace</p>\n            <h2>Saved jobs</h2>\n            <p>Keep the roles you may apply to in one focused list instead of mixing them into the analysis form.</p>\n          </div>\n        </div>\n        <div className="saved-workspace-page">\n          <SavedJobsPanel />\n        </div>\n      </section>\n\n      <section\n        className="app-tab-panel"\n        aria-label="Saved Smart Fit reports workspace"\n        hidden={activeSection !== "saved-reports"}\n      >\n        <div className="tab-panel-header">\n          <div>\n            <p className="eyebrow inline-eyebrow">Private workspace</p>\n            <h2>Saved Smart Fit reports</h2>\n            <p>Revisit fit scores, evidence, gaps, and coaching actions without storing your raw résumé text.</p>\n          </div>\n        </div>\n        <div className="saved-workspace-page">\n          <SavedReportsPanel />\n        </div>\n      </section>\n\n      <section\n        className="app-tab-panel"\n        aria-label="Sample market data"\n        hidden={activeSection !== "market-data"}\n      >\n        <div className="tab-panel-header">\n          <div>\n            <p className="eyebrow inline-eyebrow">Explore</p>\n            <h2>Sample market data</h2>\n            <p>Review the demonstration dataset, skill frequencies, and the secondary sample-dataset comparison tool.</p>\n          </div>\n        </div>\n        <section className="dashboard-grid">\n          <SampleDatasetSummary\n            jobs={dashboardData.jobs}\n            uniqueSkillCount={uniqueSkillCount}\n            topSkillName={getTopSkillName(dashboardData.topSkills)}\n            isLoading={isLoading}\n            onRefresh={loadDashboardData}\n          />\n          <ResumeAnalyzer hasJobs={dashboardData.jobs.length > 0} roleCategories={roleCategories} />\n          <SkillList title="Sample Top Skills Overall" skills={dashboardData.topSkills} />\n          <GroupedSkillPanel title="Sample Skills by Company" groups={dashboardData.skillsByCompany} />\n          <GroupedSkillPanel title="Sample Skills by Role Category" groups={dashboardData.skillsByRole} />\n          <JobTable jobs={dashboardData.jobs} />\n        </section>\n      </section>'''

app = replace_once(app, old_dashboard, new_dashboard, "main dashboard layout")
APP_PATH.write_text(app)

styles = STYLES_PATH.read_text()
styles = styles.replace(
    "/* Clerk authentication controls — temporary placement until navigation tabs are added. */",
    "/* Clerk authentication controls. */",
)

old_workspace_styles = '''.private-workspace-grid {\n  display: grid;\n  grid-template-columns: repeat(2, minmax(0, 1fr));\n  gap: 1rem;\n  margin-bottom: 1rem;\n}\n\n.saved-report-toolbar {\n  justify-content: flex-end;\n  margin: 1rem 0;\n}\n\n.saved-report-details {\n  margin-top: 0.75rem;\n}\n\n@media (max-width: 900px) {\n  .private-workspace-grid {\n    grid-template-columns: 1fr;\n  }\n}\n'''

new_workspace_styles = '''.app-tabs {\n  display: grid;\n  grid-template-columns: repeat(4, minmax(0, 1fr));\n  gap: 10px;\n  margin-bottom: 22px;\n  border: 1px solid rgba(148, 163, 184, 0.28);\n  border-radius: 24px;\n  padding: 8px;\n  background: rgba(255, 255, 255, 0.8);\n  box-shadow: 0 16px 44px rgba(15, 23, 42, 0.08);\n  backdrop-filter: blur(14px);\n}\n\n.app-tab {\n  border: 1px solid transparent;\n  border-radius: 18px;\n  padding: 13px 15px;\n  color: #475569;\n  background: transparent;\n  cursor: pointer;\n  text-align: left;\n  transition: transform 160ms ease, border-color 160ms ease, background 160ms ease, color 160ms ease;\n}\n\n.app-tab:hover {\n  border-color: #bfdbfe;\n  background: #eff6ff;\n  transform: translateY(-1px);\n}\n\n.app-tab.active {\n  border-color: #0f172a;\n  color: white;\n  background: #0f172a;\n  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.2);\n}\n\n.app-tab span,\n.app-tab small {\n  display: block;\n}\n\n.app-tab span {\n  font-weight: 850;\n}\n\n.app-tab small {\n  margin-top: 4px;\n  color: #64748b;\n  font-size: 0.76rem;\n  font-weight: 700;\n}\n\n.app-tab.active small {\n  color: #cbd5e1;\n}\n\n.app-tab-panel {\n  display: grid;\n  gap: 18px;\n}\n\n.app-tab-panel[hidden] {\n  display: none;\n}\n\n.tab-panel-header {\n  display: flex;\n  align-items: flex-end;\n  justify-content: space-between;\n  gap: 20px;\n  border: 1px solid rgba(148, 163, 184, 0.22);\n  border-radius: 22px;\n  padding: 20px 22px;\n  background: rgba(248, 250, 252, 0.82);\n}\n\n.tab-panel-header h2 {\n  margin-bottom: 7px;\n  color: #0f172a;\n  font-size: clamp(1.35rem, 2vw, 1.8rem);\n}\n\n.tab-panel-header p:last-child {\n  max-width: 760px;\n  margin-bottom: 0;\n  color: #64748b;\n  line-height: 1.55;\n}\n\n.saved-workspace-page {\n  display: grid;\n}\n\n.saved-workspace-page .saved-jobs-panel,\n.saved-workspace-page .saved-reports-panel {\n  margin-bottom: 0;\n}\n\n.saved-report-toolbar {\n  justify-content: flex-end;\n  margin: 1rem 0;\n}\n\n.saved-report-details {\n  margin-top: 0.75rem;\n}\n\n@media (max-width: 900px) {\n  .app-tabs {\n    grid-template-columns: repeat(2, minmax(0, 1fr));\n  }\n}\n\n@media (max-width: 560px) {\n  .app-tabs {\n    grid-template-columns: 1fr;\n  }\n\n  .app-tab {\n    text-align: center;\n  }\n\n  .tab-panel-header {\n    padding: 18px;\n  }\n}\n'''

styles = replace_once(styles, old_workspace_styles, new_workspace_styles, "workspace styles")
STYLES_PATH.write_text(styles)

saved_reports = SAVED_REPORTS_PATH.read_text()
if "\x08" in saved_reports:
    saved_reports = saved_reports.replace("\x08", "\\b")
SAVED_REPORTS_PATH.write_text(saved_reports)

DOC_PATH.write_text(
    '''# Milestone 6 — Tabbed Dashboard\n\nThe MarketLens frontend is organized into four focused sections instead of one long page:\n\n- **Smart Fit** — resume upload, online job search, manual job input, ranking, and report saving\n- **Saved Jobs** — private bookmarked postings\n- **Saved Reports** — private Smart Fit history\n- **Market Data** — sample dataset summary, skill trends, and sample comparison\n\n## Behavior rules\n\n- Switching sections does not unmount Smart Fit, so uploaded resume text, searched jobs, selections, and current analysis remain available.\n- Saved jobs and saved reports retain their existing Clerk-backed private ownership and deletion behavior.\n- Market-data API loading remains independent from public Smart Fit analysis.\n- The layout collapses to two tab columns on tablets and one column on narrow mobile screens.\n\n## Smoke test\n\n1. Open Smart Fit and upload or paste a resume.\n2. Search for jobs, select one, and run Smart Fit.\n3. Switch to Saved Jobs and back to Smart Fit; confirm the current analysis is still visible.\n4. Save the report, open Saved Reports, and confirm it appears.\n5. Open Market Data and verify the sample cards, charts, and postings table render.\n6. Resize to a narrow viewport and confirm the tab controls stack cleanly.\n'''
)
