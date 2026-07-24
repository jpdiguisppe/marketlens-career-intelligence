# Milestone 7 — Internship and Entry-Level Recall

This phase broadens early-career matching while retaining strict title, occupation, and experience safeguards.

## Added recall signals

Internship searches now recognize co-ops, cooperative education, apprenticeships, fellowships, summer-associate programs, student-trainee roles, graduate internships, industrial placements, and seasonal programs backed by student-eligibility language.

Entry-level searches now recognize recent-graduate and early-talent language, Engineer/Analyst I titles, rotational and graduate programs, campus/university hiring language, explicit no-experience-required postings, and descriptions requiring no more than three years of experience.

Remote-provider search passes now include co-op, apprenticeship, fellowship, new-grad, rotational-program, and numbered entry-level variants.

## Precision boundaries

- A description that merely says an employee will mentor interns does not make an experienced role an internship.
- Seasonal titles require student or program evidence rather than the word `summer` alone.
- Senior and mid-level titles remain excluded from internship and entry-level searches.
- A posting requiring four or more years of experience is not treated as entry-level even when the description uses entry-level branding.
- Generic rotational/program titles must contain description evidence for the requested job function.
- Established finance titles such as `Investment Banking Summer Analyst` remain valid internship matches.

## Validation

The focused regression suite covers level inference, seasonal and structured programs, low-experience descriptions, occupation evidence, experienced-role rejection, established Summer Analyst behavior, and expanded remote-provider query terms. The complete backend suite passed before the clean implementation commit was created.

Credential-aware legal filtering remains the next separate legal-specific phase; this work only improves general early-career level recognition and recall.
