# Milestone 7 — Better Job Source Coverage: Complete

Milestone 7 is complete as of **July 24, 2026**. The production smoke test verified the Railway deployment built from `main` commit `083b9b780e66f42b9d515e5085db2ef7fb00c072` after the formal evaluation suite was merged.

## What shipped

### Search intent and matching

- Independent job-function, industry, experience-level, and location dimensions.
- A reusable industry taxonomy instead of sports-only one-off behavior.
- Strict role-family matching where description-only evidence would otherwise create false positives.
- Cross-industry legal, compliance, policy, legal-operations, and contracts intent.
- Broader internship, co-op, fellowship, apprenticeship, student-program, seasonal, rotational, new-grad, low-experience, and numbered-title recall.
- Senior-title and high-experience protections for internship and entry-level searches.

### Source coverage and routing

- A typed, static Greenhouse/Lever source registry that doubles as an outbound allowlist.
- Primary sources for broad searches and industry-only sources activated only for matching industries.
- Intent-aware source scoring using exact or adjacent industry, job function, early-career relevance, and location metadata.
- Bounded provider routing with Greenhouse/Lever diversity and a per-search request budget.
- Broader registered coverage for sports, nonprofit, healthcare, education, media, legal services, public interest, public policy, corporate legal, and financial services.
- Exact sports/nonprofit boards including The Athletic, Feld Entertainment, and Stand Together.
- Additional boards including ACLU, Avalere Health, WEBTOON/Wattpad, The Dispatch, Kiddom, and Strada Education Foundation.

### Legal credential safety

Law-related postings are classified as:

- undergraduate-accessible
- law-student-only
- licensed/JD-or-bar-required
- unknown

Undergraduate legal searches exclude known law-student and licensed roles. Law-student searches can target summer associates, law clerks, judicial internships/externships, and JD-candidate roles. Attorney/counsel searches target licensed roles. Generic legal searches remain broad when the user did not specify a credential level.

### Closed-source continuation UX

MarketLens does not crawl or claim to search LinkedIn, Indeed, Handshake, or Workday result pages. The deployed interface now shows:

- what MarketLens actually searched
- provider-by-provider fetched and matched counts
- routing notes, warnings, and query suggestions
- HTTPS Google Jobs, Indeed, LinkedIn Jobs, Workday/company-career-site, and Handshake continuation links
- a workflow for copying an outside posting into manual Smart Fit

The Workday path uses Google discovery queries restricted to indexed `myworkdayjobs.com` and `myworkdaysite.com` pages rather than scraping Workday tenants.

## Formal evaluation baseline

The deterministic offline benchmark contains **74 cases**:

- 20 intent cases
- 45 candidate cases: 22 relevant postings and 23 deliberate false positives
- 9 source-routing cases
- 13 critical safety guardrails

The enforced thresholds are:

- 100% intent accuracy
- at least 95% candidate accuracy
- at least 95% recall
- at least 95% precision
- at least 95% negative rejection
- 100% routing accuracy
- 100% critical-case pass rate

All 74 cases pass. Run the benchmark from `backend` with:

```bash
python scripts/run_job_search_evaluation.py
```

The benchmark also exposed and drove a real product fix: explicit cross-industry compliance queries now take canonical compliance intent precedence over older healthcare or finance compatibility classification.

## Production smoke test

A GitHub Actions smoke test called the live Railway frontend and backend directly.

### Deployment health

- Backend `/health`: HTTP 200 with `{"status":"ok"}`.
- Frontend root: HTTP 200 with a valid React root.
- Deployed frontend JavaScript contained both `What MarketLens actually searched` and `Continue externally`.
- `/analysis/model-status` returned a valid safe status response. Model assistance was not configured in production at test time, so the deterministic path remains the available analysis path.

### Live search scenarios

| Query | Expected intent | Production result |
| --- | --- | --- |
| `sports marketing internship` | marketing + sports + intern | Passed; routing included The Athletic and Feld Entertainment |
| `healthcare compliance analyst entry level` | compliance + healthcare + entry | Passed; routing included Avalere Health and Benchling |
| `legal internship` | legal + legal services + intern | Passed; routing included ACLU and The Dispatch; undergraduate credential guard executed |
| `law student judicial internship` | legal + no forced industry + intern | Passed; generic law-student language did not incorrectly force legal-services industry |

For all four searches:

- the response schema included source coverage, warnings, suggestions, and external links
- provider fetched/matched counts were non-negative and present
- searched-provider lists did not claim LinkedIn, Indeed, Handshake, or Workday
- external continuation links were HTTPS
- all five expected continuation options were present for internship/entry searches

The public sources returned zero matching Philadelphia-area postings during this specific production run. That is not represented as success inventory. MarketLens returned clear no-result warnings and external continuation workflows, demonstrating the intended honest behavior when current public ATS inventory is thin.

## Validation record

Before completion:

- complete backend test suite passed
- 74-case job-search benchmark passed
- frontend production build passed
- backend Docker image passed
- frontend Docker image passed
- live Railway frontend/backend smoke test passed

## Remaining limitations

- Public ATS inventory changes continuously, and registered organizations may have no relevant openings at a given time.
- MarketLens does not provide exhaustive coverage of LinkedIn, Indeed, Handshake, Workday, school portals, or every company career site.
- The configured source registry is deliberately bounded; new legitimate sources can be added in later maintenance work.
- Instance-local rate limits are useful application safeguards but are not a substitute for edge-level or shared multi-instance abuse controls.
- Model-assisted analysis remains optional and was not configured in production during this smoke test.
- Saved searches, job alerts, collections, and standalone saved records for manually pasted jobs remain deferred optional additions.

## Next milestone

Milestone 8 remains **Optional AI-Assisted Analysis**: stronger semantic requirement parsing, better evidence matching, more personalized coaching explanations, and evaluation/cost/latency controls while preserving deterministic fallback and backend-only provider keys.
