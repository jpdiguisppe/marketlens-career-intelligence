# MarketLens Project Plan

## Project Summary

MarketLens is a full-stack career intelligence platform that analyzes job postings and helps early-career candidates understand which skills, tools, and experiences are most relevant for their target roles.

The first version will focus on software engineering, AI-adjacent, cloud, systems, and infrastructure-related roles.

## Core Question

MarketLens is built around one practical question:

> What should I actually learn or build to become more competitive for the roles I want?

## Target Users

Initial target users:

- Computer science students
- Early-career software engineers
- Internship candidates
- New grad candidates
- Students deciding between backend, AI, systems, cloud, and data-focused paths

## MVP Scope

The MVP is a Job Skill Analyzer.

### Included in MVP

- Manual job posting entry
- CSV import for sample job postings
- Backend storage for job postings
- Skill extraction using a predefined skill dictionary
- Skill frequency analysis
- Company comparison
- Role-category comparison
- Resume text input
- Resume-to-market skill gap report

### Not Included in MVP

- Live scraping from LinkedIn or Indeed
- User authentication
- Paid job board integrations
- Advanced AI recommendations
- Fully automated resume parsing from PDF

These may be added later after the core product works.

## Example Use Case

A user wants to target backend, AI-adjacent, systems, or cloud roles near Philadelphia.

They upload job postings from companies such as UHS, Lockheed Martin, Leidos, Comcast, Cencora, Vanguard, SAP, Siemens Healthineers, and Toll Brothers.

MarketLens analyzes the postings and reports:

- Which skills appear most often
- Which companies emphasize which tools
- Which role categories mention cloud, Linux, APIs, testing, Docker, SQL, or AI-related skills
- Which skills the user already has on their resume
- Which missing skills should be prioritized next

## Phase Breakdown

### Phase 1: Foundation

Goal: Create a clean repository and working backend foundation.

Tasks:

- Create project structure
- Write README
- Write planning docs
- Set up FastAPI
- Add health-check endpoint
- Add requirements file

Success criteria:

- Backend runs locally
- `/health` endpoint returns a successful response
- Repo has clear documentation

### Phase 2: Job Posting API

Goal: Store and retrieve job postings.

Tasks:

- Define job posting model
- Add POST endpoint for creating postings
- Add GET endpoint for listing postings
- Add sample in-memory storage first
- Move to PostgreSQL later

Success criteria:

- User can add a posting through the API
- User can retrieve postings through the API

### Phase 3: Skill Extraction

Goal: Extract meaningful skills from job descriptions.

Tasks:

- Create skill dictionary
- Normalize related terms
- Detect skills in posting text
- Return extracted skills from API
- Store job-skill relationships later

Success criteria:

- System identifies common skills such as Python, SQL, React, Docker, AWS, Azure, Linux, REST APIs, CI/CD, Git, Agile, and testing

### Phase 4: Data Analysis

Goal: Turn extracted skills into useful insights.

Tasks:

- Count skill frequency
- Compare skills by company
- Compare skills by role category
- Return dashboard-ready API responses

Success criteria:

- API can answer questions like “What are the top skills for backend roles?” and “Which skills show up most often for Lockheed-style systems roles?”

### Phase 5: Frontend Dashboard

Goal: Make the insights visual and demo-friendly.

Tasks:

- Set up React + TypeScript frontend
- Add dashboard layout
- Add charts for skill frequency
- Add posting table
- Add company comparison view

Success criteria:

- User can view skill trends in a browser
- Project is visually demoable

### Phase 6: Resume Gap Analyzer

Goal: Compare a resume against job market data.

Tasks:

- Add resume text input
- Extract skills from resume text
- Compare resume skills to selected postings
- Return matched skills and missing skills
- Generate recommended learning priorities

Success criteria:

- User can paste a resume and receive a skill-gap report

### Phase 7: Polish

Goal: Make the project portfolio-ready.

Tasks:

- Add tests
- Add Docker setup
- Add GitHub Actions
- Add deployment
- Add screenshots
- Add demo write-up

Success criteria:

- Repo looks professional
- App can be demoed in an interview
- README clearly explains the problem, solution, stack, and architecture

## First Technical Milestone

The first coding milestone is:

> A working FastAPI backend with a `/health` endpoint and a `/job-postings` endpoint using temporary in-memory storage.

This gives the project an API foundation before adding PostgreSQL, NLP, or the frontend.
