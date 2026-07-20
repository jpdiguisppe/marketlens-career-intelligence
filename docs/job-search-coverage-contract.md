# Job Search Coverage Contract

MarketLens job search is designed for broad career use, not only software roles.

## Matching behavior

- Known role families use curated title and query mappings.
- Careers outside the curated taxonomy use normalized occupation terms, common field-to-title aliases, and conservative title matching.
- Degree/field wording such as `mechanical engineering`, `teaching`, `nursing`, or `psychology` can match job-title wording such as `Mechanical Engineer`, `Teacher`, `Registered Nurse`, or `Psychologist`.
- Unrelated job titles must still be rejected.

## Source behavior

MarketLens searches configured API-friendly public sources. Correct query matching does not guarantee that those sources currently contain a posting for every occupation or location.

When no matching posting is returned, MarketLens must:

1. state that source coverage is limited rather than implying no jobs exist;
2. provide external search links;
3. preserve manual pasted-job Smart Fit analysis;
4. expose source coverage details so gaps can be diagnosed.

## Regression expectation

Every search-intent change should include positive and negative examples spanning multiple career areas. Current regression coverage includes healthcare/nursing, engineering, education, law, science, architecture, journalism, social work, skilled trades, and culinary work.
