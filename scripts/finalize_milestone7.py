from __future__ import annotations

from pathlib import Path

README_PATH = Path("README.md")
COMPLETION_PATH = Path("docs/milestone-7-completion.md")


def replace_once(content: str, old: str, new: str) -> str:
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one README match, found {count}: {old[:100]!r}")
    return content.replace(old, new, 1)


readme = README_PATH.read_text(encoding="utf-8")

readme = replace_once(
    readme,
    "- **Quality coverage:** Backend tests cover API behavior, job search filtering, Smart Fit analysis, role-aware behavior, and evaluation cases.",
    "- **Quality coverage:** Backend tests cover API behavior, job search filtering, Smart Fit analysis, and a 74-case offline recall/precision benchmark with critical safety guardrails.",
)
readme = replace_once(
    readme,
    "- **Milestone 7 plan:** [Job-source coverage roadmap](docs/milestone-7-source-coverage-plan.md)",
    "- **Milestone 7 completion:** [Production-verified job-source coverage record](docs/milestone-7-completion.md)",
)
readme = replace_once(
    readme,
    "- [`docs/milestone-6-completion.md`](docs/milestone-6-completion.md)\n## Current Demo Capabilities",
    "- [`docs/milestone-6-completion.md`](docs/milestone-6-completion.md)\n- [`docs/milestone-7-completion.md`](docs/milestone-7-completion.md)\n## Current Demo Capabilities",
)
readme = replace_once(
    readme,
    "- search across multiple role families and filter by experience level and location\n- inspect source coverage notes, warnings, and fallback links",
    "- search with separate job-function, industry, experience-level, and location intent\n- inspect provider-by-provider coverage, routing notes, warnings, suggestions, and responsible external fallback links",
)
readme = replace_once(
    readme,
    "MarketLens does **not** claim to search all of LinkedIn, Indeed, Handshake, Workday, company career pages, or school career portals. When no results are found, the API returns source-coverage metadata, human-readable search notes, and fallback search links so the user can continue outside the configured API-friendly sources and paste those jobs back into Smart Fit.",
    "MarketLens does **not** claim to search all of LinkedIn, Indeed, Handshake, Workday, company career pages, or school career portals. After a search, the product separates sources it actually queried from external continuation links, returns provider-by-provider coverage and routing notes, and guides users to paste outside postings back into Smart Fit.",
)
readme = replace_once(
    readme,
    "software, finance, data, cybersecurity, product, marketing, operations, healthcare, design",
    "technology, software, finance, data, cybersecurity, product, marketing, operations, healthcare, design, legal, compliance, policy, legal_operations, contracts",
)
readme = replace_once(
    readme,
    "marketing intern\nsoftware engineer intern\nbackend developer",
    "marketing intern\nsoftware engineer intern\nbackend developer\nsports marketing internship\nhealthcare compliance analyst entry level\nlegal internship\nlaw student judicial internship",
)
readme = replace_once(
    readme,
    "- `level=intern` only returns internship/co-op-looking roles.\n- `level=entry`, `level=mid`, and `level=senior` filter by experience signal.",
    "- `level=intern` recognizes internships, co-ops, fellowships, apprenticeships, student programs, and guarded seasonal early-career titles.\n- `level=entry` recognizes new-grad, recent-graduate, Engineer I/Analyst I, rotational-program, low-experience, and no-experience-required signals.\n- `level=mid` and `level=senior` filter by title and experience signals while protecting early-career searches from experienced-role false positives.",
)
readme = replace_once(
    readme,
    "- online job search with level and optional location filters\n- searched-job cards with source, company, location, link, and extracted skills",
    "- online job search with separate function, industry, level, and optional location intent\n- provider-by-provider searched/fetched/matched coverage, routing notes, suggestions, and external continuation links\n- searched-job cards with source, company, location, link, and extracted skills",
)
readme = replace_once(
    readme,
    "- backend evaluation cases for Smart Fit analysis\n- frontend production build validation",
    "- backend evaluation cases for Smart Fit analysis\n- deterministic 74-case job-search benchmark covering intent, recall, precision, negative rejection, source routing, and critical credential/industry guardrails\n- frontend production build validation",
)
readme = replace_once(
    readme,
    "Run the frontend production build:\n\n```bash\ncd frontend\nnpm install\nnpm run build\n```",
    "Run the formal job-search evaluation:\n\n```bash\ncd backend\npython scripts/run_job_search_evaluation.py\n```\n\nRun the frontend production build:\n\n```bash\ncd frontend\nnpm install\nnpm run build\n```",
)

old_milestone = """### Milestone 7 — Better Job Source Coverage: in progress

The next major limitation is recall: precise filtering cannot return roles that are absent from the configured sources.

Planned work:

- model search intent as separate job-function, industry, experience-level, and location dimensions
- build a reusable industry taxonomy
- create a configurable organization/source registry with coverage metadata
- expand legitimate public Greenhouse and Lever boards plus suitable public APIs
- improve internship and entry-level coverage
- improve sports, entertainment, healthcare, finance, education, nonprofit, media, and other non-software coverage
- improve user-facing source coverage explanations
- provide responsible user-assisted workflows for Workday, Handshake, LinkedIn, Indeed, and other closed sources without scraping them
- add recall and precision regression tests across industries

See [`docs/milestone-7-source-coverage-plan.md`](docs/milestone-7-source-coverage-plan.md) and [issue #21](https://github.com/jpdiguisppe/marketlens-career-intelligence/issues/21).
"""
new_milestone = """### Milestone 7 — Better Job Source Coverage: complete

- separate job-function, industry, experience-level, and location intent
- reusable industry taxonomy plus a typed, allowlisted Greenhouse/Lever source registry
- primary and industry-only source pools with bounded intent-aware routing
- broader sports, nonprofit, healthcare, education, media, legal, public-interest, policy, and financial-services coverage
- stronger internship, co-op, fellowship, apprenticeship, seasonal, rotational, and new-grad recall
- credential-aware separation of undergraduate legal, law-student, and licensed-attorney roles
- transparent provider coverage, routing notes, suggestions, and responsible LinkedIn/Indeed/Handshake/Workday continuation links without scraping
- deterministic 74-case recall/precision/routing benchmark with enforced thresholds and critical guardrails
- live Railway smoke test covering the deployed frontend bundle, API health, model status, intent dimensions, source reporting, credential behavior, and external-link safety

See [`docs/milestone-7-completion.md`](docs/milestone-7-completion.md), [`docs/milestone-7-recall-precision-evaluation.md`](docs/milestone-7-recall-precision-evaluation.md), and [`docs/milestone-7-source-coverage-plan.md`](docs/milestone-7-source-coverage-plan.md).
"""
readme = replace_once(readme, old_milestone, new_milestone)
README_PATH.write_text(readme, encoding="utf-8")

completion = """# Milestone 7 — Better Job Source Coverage: Complete

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
"""
COMPLETION_PATH.write_text(completion, encoding="utf-8")

for temporary_path in (
    Path("scripts/smoke_milestone7_production.py"),
    Path(".github/workflows/milestone-7-production-smoke.yml"),
    Path("scripts/finalize_milestone7.py"),
    Path(".github/workflows/finalize-milestone7.yml"),
):
    temporary_path.unlink(missing_ok=True)
