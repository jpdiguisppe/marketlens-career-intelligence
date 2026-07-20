# MarketLens Portfolio Screenshot Guide

Use this guide to capture clean, safe screenshots for the README and portfolio materials.

## Privacy rule

Do **not** use a real resume, real phone number, real address, real email, API key, employer confidential data, or private job posting content in portfolio screenshots.

Use a short fake resume and public/demo job postings only. If a screenshot accidentally includes personal details, do not commit it.

## Recommended screenshots

### 1. Online job search results

Purpose: show that MarketLens can search configured public job sources and return normalized job cards.

Capture after:

```text
Search query: Data Analyst
Level: Entry or Any
Location: Remote or Philadelphia
```

Try to include:

- search form
- returned job cards
- source/search notes if visible
- compare-selected controls

Suggested filename:

```text
docs/assets/screenshots/online-job-search.png
```

### 2. Ranked Smart Fit comparison

Purpose: show the main product value: selecting multiple jobs, comparing them against a resume, and ranking fit.

Capture after selecting two or three jobs and clicking Compare selected.

Try to include:

- ranked jobs
- fit percentages
- fit bands
- Why this ranking? explanation

Suggested filename:

```text
docs/assets/screenshots/smart-fit-ranking.png
```

### 3. Detailed role-aware gap report

Purpose: show that MarketLens explains missing role-specific capabilities instead of only listing keyword overlap.

Capture after opening Show details for one ranked job.

Try to include:

- coach summary
- main gaps
- best next actions
- resume evidence labels
- category coverage

Suggested filename:

```text
docs/assets/screenshots/role-aware-gap-report.png
```

## Safe sample resume text

Use this instead of a real resume when creating portfolio screenshots:

```text
Alex Student
Computer Science Student

Education
B.S. Computer Science, Expected 2027

Projects
Market Dashboard — built a Python and SQL dashboard to analyze sample business metrics.
API Tracker — created a FastAPI backend with REST endpoints, SQLite storage, and basic tests.
ML Classifier — trained a simple scikit-learn model using Python and evaluated precision/recall.

Skills
Python, SQL, Java, C, FastAPI, React, Git, REST APIs, scikit-learn, Excel
```

## Safe pasted job example

Use this for manual Smart Fit screenshots if online results are thin:

```text
Analytics Engineer

Required Qualifications
Build and maintain data pipelines, data models, and reporting tables.
Use SQL and Python to transform data and support analytics workflows.
Work with stakeholders to define metrics, dashboards, and business reporting needs.
Experience with dbt, cloud data warehouses, and production data quality checks is preferred.
---
Insider Threat Analyst

Required Qualifications
Investigate security alerts, insider risk signals, fraud patterns, and suspicious user activity.
Use logs, detection tools, and case management systems to support incident response.
Partner with security operations, legal, and compliance teams.
Experience with threat investigation, SIEM tools, and security operations workflows is preferred.
```

## Screenshot quality checklist

Before committing screenshots:

```text
- No real personal information visible
- Browser zoom around 90% to 100%
- App is loaded from the live demo or clean local environment
- Screenshot focuses on one clear feature
- No terminal secrets or browser account details visible
- File size is reasonable for GitHub README use
```

## README usage

After screenshots are committed, link them from the README with short captions. Keep the README visual section brief so it stays easy to skim.
