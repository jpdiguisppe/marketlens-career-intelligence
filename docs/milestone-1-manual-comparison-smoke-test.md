# Milestone 1 Manual Comparison Smoke Test

Use this checklist before moving on to online job search integrations.

## Goal

Milestone 1 is complete when MarketLens can run the manual comparison workflow end to end:

```text
Upload or paste resume
Paste one or more job descriptions
Separate multiple jobs with ---
Detect the job count before analysis
Analyze each job independently through the backend batch endpoint
Rank jobs against the resume
Explain why the ranking happened
Switch between detailed Smart Fit reports for each ranked job
```

## Local quality checks

From the project root:

```bash
cd backend
source .venv/bin/activate
python -m pytest

cd ../frontend
npm run build
```

Expected result:

```text
Backend tests pass.
Frontend production build succeeds.
```

## Manual frontend smoke test

Open the deployed frontend or local Vite app.

1. Upload a DOCX or text-based PDF resume.
2. Confirm the resume text box is populated.
3. Paste two job descriptions into the job description box.
4. Put a line containing only `---` between the two jobs.
5. Confirm the helper text says `2 job descriptions detected and ready to rank.`
6. Click the ranking/analyze button.
7. Confirm a `Job fit ranking` section appears.
8. Confirm each ranked job shows:
   - score
   - fit band
   - top matches
   - top gaps
   - `Show details` button
9. Click `Show details` for the lower-ranked job.
10. Confirm the detailed Smart Fit report changes to that selected job.
11. Confirm the `Why this ranking?` section explains the top job, score gap, and runner-up gap reasons.

## Test data

Use this block in the job description box:

```text
Software Engineering Intern

Responsibilities
Assist engineers with software development tasks for internal applications.
Write, debug, and maintain code in Java, Python, C, or SQL.
Help troubleshoot software issues and document technical findings.
Work with databases and operating systems concepts from coursework.
Communicate progress clearly with technical and non-technical teammates.

Required Qualifications
Currently pursuing a Bachelor's degree in Computer Science or related field.
Coursework or project experience with Java, Python, C, SQL, databases, or operating systems.
Comfort using Microsoft Office or Google Workspace.
Strong problem-solving and communication skills.

Preferred Qualifications
IT support or troubleshooting experience.
Interest in AI products, software prototyping, or technical documentation.

---

Backend Software Engineer Intern

Responsibilities
Build REST API endpoints for a cloud-based web application.
Work with Python, FastAPI, PostgreSQL, Docker, and Git.
Write automated tests and improve backend reliability.
Collaborate with frontend engineers and product managers.
Deploy and monitor backend services in a cloud environment.

Required Qualifications
Experience with Python.
Experience with SQL or relational databases.
Experience using Git or GitHub.
Familiarity with REST APIs and backend web development.

Preferred Qualifications
Docker or containerization experience.
FastAPI, Flask, or Django experience.
Cloud deployment experience with AWS, Azure, or similar platforms.
Testing or CI/CD experience.
```

## Expected behavior

The first job should usually rank above the second when using a basic CS/student resume that lists coursework, Java, Python, C, SQL, Microsoft/Google tools, AI interest, and IT troubleshooting, but does not yet show strong proof of REST APIs, FastAPI, Docker, Git/GitHub, cloud, testing, or CI/CD.

## Not part of Milestone 1

These stay parked until Milestone 1 is verified:

- online job search integrations
- user accounts
- saved reports
- live model-provider setup
- resume rewrite generator
- UI polish beyond workflow clarity
