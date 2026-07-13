# Smart Fit Evaluation Set

MarketLens uses a deterministic analysis pipeline today: curated skill vocabulary, section parsing, requirement extraction, evidence scoring, hard-requirement checks, and coaching-action generation. It does not automatically learn from new examples yet.

The evaluation set is how we make that pipeline more reliable. Each realistic failure should become a small synthetic case that protects the product from regressing later.

## Privacy and copyright rules

Use only safe evaluation data:

- Use synthetic resumes, redacted resumes, or short representative snippets.
- Do not commit real names, email addresses, phone numbers, street addresses, school IDs, profile URLs, or other personal identifiers.
- Do not commit a full copied resume from a real person.
- Do not commit full copied job postings from job boards, company sites, PDFs, or emails.
- Do not use confidential internal job descriptions or private company documents.
- Keep job descriptions short and representative. Write them in your own words when possible.
- Mark every committed case with `"source": "synthetic"` unless a future policy explicitly supports another source type.

The goal is to cover patterns, not to preserve exact third-party text.

## What each case should test

A good evaluation case should answer at least one product question:

- Did MarketLens detect the important required skills?
- Did it avoid treating coursework or a skills list as strong applied evidence?
- Did it separate required/core skills from preferred or lower-priority skills?
- Did it catch hard constraints such as degree status, years of experience, citizenship, work authorization, clearance, or travel?
- Did the headline name the most useful gap rather than a weaker process keyword?
- Did coaching actions focus on resume rewrites, learning gaps, hard checks, and lower-priority noise in a useful order?

## Current evaluation coverage

The first evaluation set covers:

1. Backend API project vs backend internship.
2. Student/IT-support resume vs mid-level full-stack .NET role.
3. Backend-heavy resume vs frontend React role.
4. Docker/CI evidence vs cloud/devops role.
5. Technical match with citizenship and clearance constraints.
6. Academic AI/certification resume vs ML/data internship.
7. General IT support resume vs systems role.

## How to add a new case

1. Add one object to `backend/tests/fixtures/smart_fit_evaluation_cases.json`.
2. Keep the resume and job text short, synthetic, and sanitized.
3. Add only expectations that matter for that scenario.
4. Prefer behavior expectations over exact score expectations.
5. Run the backend tests.

Example expectation fields:

```json
{
  "allowed_bands": ["limited_alignment", "partial_alignment"],
  "expected_requirement_skills_include": ["React", "JavaScript"],
  "expected_important_gaps_include": ["React"],
  "expected_under_sold_include": ["SQL"],
  "expected_hard_requirements": {"years_experience": "unclear"},
  "headline_excludes": ["Agile"]
}
```

## Running the evaluation set

```bash
cd backend
source .venv/bin/activate
python -m pytest tests/test_smart_analysis_evaluation_cases.py
```

Or run the full backend suite:

```bash
python -m pytest
```

## Maintenance notes

When the ontology expands, some older scores may move downward because MarketLens recognizes more missing requirements. That is usually good if the job truly asks for those requirements. Update score/band expectations only after reviewing whether the new behavior is more truthful for the candidate.

Avoid making tests so strict that every wording improvement breaks them. The evaluation set should catch major product mistakes, not freeze every sentence forever.
