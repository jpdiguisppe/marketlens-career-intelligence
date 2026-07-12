# Custom Analysis Workflow

Custom Analysis is the first MarketLens feature designed around real public use instead of only a shared demo dataset.

## Purpose

A visitor can paste:

- resume-style text
- one or more job descriptions

MarketLens then extracts skills from both sides and returns:

- resume skills found
- target skills from the pasted job descriptions
- matched skills
- missing skills
- match percentage
- learning priorities

## Privacy Model

Custom Analysis does **not** save pasted job descriptions or resume-style text to the shared database.

This keeps the app useful for public visitors while avoiding the current risks of anonymous users modifying shared demo data.

## Backend Endpoint

```text
POST /analysis/custom
```

Request body:

```json
{
  "resume_text": "Python, SQL, Git, Agile, and REST API project experience.",
  "job_descriptions": [
    "Backend role requiring Python, SQL, REST APIs, Docker, and Agile experience."
  ]
}
```

The endpoint is public but rate-limited.

## Input Limits

Current limits:

- resume text: 10,000 characters
- each job description: 5,000 characters
- pasted job descriptions per request: 10

## Why This Comes Before Login

Full authentication and per-user saved data are still planned, but Custom Analysis gives real usefulness immediately:

- no account required
- no shared database writes
- no risk of anonymous users deleting or polluting saved demo data

The next major step after this is user accounts and user-owned saved postings.
