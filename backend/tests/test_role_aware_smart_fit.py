from app.analysis.service import analyze_smart_fit

CS_RESUME = """
EDUCATION
Bachelor of Science in Computer Science expected May 2027.
Coursework includes Data Structures, Database Systems, Operating Systems, Probability, and Java, Python, C, and SQL programming.

PROJECTS
- Built a Python Flask weather app using API requests and error handling.
- Built an emotion classifier using Python, scikit-learn, TF-IDF, Logistic Regression, and SVM.
- Built a SQL internship tracker with normalized tables and joins.

SKILLS
Python, Java, C, SQL, Git, Flask, scikit-learn, machine learning.
"""

ANALYTICS_ENGINEER_JOB = """
Coinbase — Analytics Engineer

Required Qualifications
Build analytics models, data pipelines, and dashboards for product and risk teams.
Use Python and SQL to analyze datasets, validate metrics, and partner with engineering teams.
0-3 years of professional experience or relevant project experience in data analytics, computer science, or software engineering.
"""

INSIDER_THREAT_JOB = """
Coinbase — Insider Threat Analyst

About the Role
Ready to do the most impactful work of your career? We are uncompromising on our mission to increase economic freedom.
This role investigates insider threat events, security incidents, account misuse, and vulnerability response workflows.
Use machine learning alerts and behavioral signals to support cybersecurity investigations.
"""

BOILERPLATE_SOFTWARE_JOB = """
Software Engineer

About us
Our mission is to change the world. We value curiosity, ownership, and teamwork.
Benefits include health insurance, flexible time off, and career growth.

Responsibilities
You will build small Python services for internal teams.
"""

FINANCE_ANALYST_JOB = """
Financial Analyst

Required Qualifications
Build financial models, budgeting forecasts, variance analysis, executive reporting, and SQL dashboards.
Support accounting close, audit schedules, controls, and compliance reporting in Excel.
"""


def test_role_aware_smart_fit_prefers_data_role_over_cyber_role_for_cs_resume() -> None:
    analytics = analyze_smart_fit(
        resume_text=CS_RESUME,
        job_description=ANALYTICS_ENGINEER_JOB,
    )
    insider_threat = analyze_smart_fit(
        resume_text=CS_RESUME,
        job_description=INSIDER_THREAT_JOB,
    )

    assert analytics.fit_summary.score > insider_threat.fit_summary.score
    assert any("data role" in item.lower() or "data" in item.lower() for item in analytics.report_summary)
    assert any("cybersecurity/threat" in item.lower() for item in insider_threat.report_summary)
    assert "Role-aware scoring discounted" in insider_threat.fit_summary.headline
    assert any("role-adjusted resume-proof score" in item.lower() for item in insider_threat.report_summary)
    assert not any(item.startswith("Resume-proof score:") for item in insider_threat.report_summary)


def test_role_aware_smart_fit_surfaces_capability_gaps_beyond_exact_skills() -> None:
    analysis = analyze_smart_fit(
        resume_text=CS_RESUME,
        job_description=INSIDER_THREAT_JOB,
    )
    gap_titles = {group.title for group in analysis.gap_groups}
    coaching_titles = {action.title for action in analysis.coaching_actions}

    assert "Security operations and incident response" in gap_titles
    assert "Threat investigation and fraud analysis" in gap_titles
    assert "Security operations and incident response" in coaching_titles
    assert any("capability gap check" in item.lower() for item in analysis.report_summary)


def test_role_aware_smart_fit_applies_capability_gaps_to_non_cyber_domains() -> None:
    analysis = analyze_smart_fit(
        resume_text=CS_RESUME,
        job_description=FINANCE_ANALYST_JOB,
    )
    gap_titles = {group.title for group in analysis.gap_groups}

    assert "Financial modeling and analysis" in gap_titles
    assert "Accounting, audit, and tax workflows" in gap_titles
    assert "Risk, controls, and compliance reporting" in gap_titles
    assert any("finance" in item.lower() for item in analysis.report_summary)


def test_role_aware_smart_fit_marks_boilerplate_descriptions_lower_confidence() -> None:
    analysis = analyze_smart_fit(
        resume_text=CS_RESUME,
        job_description=BOILERPLATE_SOFTWARE_JOB,
    )

    assert analysis.fit_summary.confidence <= 0.66
    assert any("boilerplate-heavy" in warning.lower() for warning in analysis.document_quality.warnings)
    assert any("low-signal" in analysis.fit_summary.headline.lower() or "boilerplate" in item.lower() for item in analysis.report_summary)
    assert any("role-adjusted resume-proof score" in item.lower() for item in analysis.report_summary)
