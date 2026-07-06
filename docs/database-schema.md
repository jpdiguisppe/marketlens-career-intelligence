# MarketLens Database Schema Plan

This document describes the planned database structure for MarketLens.

The MVP may start with in-memory storage so the backend can be built quickly. PostgreSQL will be added once the basic API works.

## Main Entities

MarketLens will store job postings, companies, role categories, skills, resumes, and extracted skill relationships.

## Tables

### companies

Stores companies connected to job postings.

| Column | Type | Notes |
| --- | --- | --- |
| id | integer | Primary key |
| name | text | Company name |
| industry | text | Optional industry/category |
| created_at | timestamp | Record creation time |

### roles

Stores broad role categories.

| Column | Type | Notes |
| --- | --- | --- |
| id | integer | Primary key |
| name | text | Example: Backend SWE, Systems Engineer, AI Engineer, Cloud Engineer |
| description | text | Optional role description |

### job_postings

Stores individual job postings.

| Column | Type | Notes |
| --- | --- | --- |
| id | integer | Primary key |
| company_id | integer | Foreign key to companies.id |
| role_id | integer | Foreign key to roles.id |
| title | text | Job title |
| location | text | Job location |
| experience_level | text | Internship, New Grad, Associate, Entry-Level |
| posting_url | text | Optional source URL |
| description | text | Full job description |
| posting_date | date | Optional date the posting was collected |
| created_at | timestamp | Record creation time |

### skills

Stores normalized skill names.

| Column | Type | Notes |
| --- | --- | --- |
| id | integer | Primary key |
| name | text | Normalized skill name, such as Python or Docker |
| category | text | Language, Framework, Database, Cloud, DevOps, Methodology, etc. |

### job_skills

Join table connecting job postings to extracted skills.

| Column | Type | Notes |
| --- | --- | --- |
| job_posting_id | integer | Foreign key to job_postings.id |
| skill_id | integer | Foreign key to skills.id |
| source_text | text | Optional phrase that triggered the match |
| confidence | decimal | Optional confidence score for AI/NLP extraction |

### resumes

Stores resume text for analysis.

| Column | Type | Notes |
| --- | --- | --- |
| id | integer | Primary key |
| name | text | Optional resume label |
| raw_text | text | Pasted resume text |
| created_at | timestamp | Record creation time |

### resume_skills

Join table connecting resumes to extracted skills.

| Column | Type | Notes |
| --- | --- | --- |
| resume_id | integer | Foreign key to resumes.id |
| skill_id | integer | Foreign key to skills.id |
| source_text | text | Optional phrase that triggered the match |

## MVP Data Flow

1. User adds a job posting.
2. Backend stores the posting.
3. Skill extractor scans the job description.
4. Extracted skills are normalized.
5. Job-skill relationships are stored.
6. Dashboard queries aggregate the job-skill data.
7. User pastes resume text.
8. Resume skills are extracted and compared against target postings.

## Initial Skill Categories

- Programming Languages
- Frameworks and Libraries
- Databases
- Cloud Platforms
- DevOps and Infrastructure
- Operating Systems
- Data and AI
- Security
- Testing
- Methodologies

## Early Skill Dictionary Examples

| Skill | Possible Matches |
| --- | --- |
| Python | python |
| Java | java |
| SQL | sql, relational database |
| PostgreSQL | postgres, postgresql |
| React | react, react.js, reactjs |
| FastAPI | fastapi |
| Docker | docker, containerization, containers |
| AWS | aws, amazon web services |
| Azure | azure, microsoft azure |
| Linux | linux, unix |
| Git | git, github, version control |
| CI/CD | ci/cd, continuous integration, continuous deployment, github actions |
| REST APIs | rest, restful api, api development |
| Agile | agile, scrum |
| Testing | unit testing, automated testing, test automation |

## Notes

The database schema may change as the project develops. The first working version should prioritize a simple API and clear data flow over perfect database design.
