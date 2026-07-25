# Search Correctness Hardening

Issue [#39](https://github.com/jpdiguisppe/marketlens-career-intelligence/issues/39) blocks Milestone 8 until MarketLens search behavior is reliable across occupations, levels, locations, and sectors.

## Search contract

MarketLens now separates four concerns that previously leaked into one another:

1. **Occupation relevance** — specific occupations require title-level evidence for the requested work. A shared generic word such as `engineer`, `analyst`, `assistant`, `technician`, or `manager` is not enough.
2. **Career level** — internship, entry, mid, and senior filters are evaluated independently from occupation relevance, including apprenticeships, trainee roles, numbered levels, written experience requirements, and non-senior uses of `Staff`.
3. **Location** — an explicit city search includes recognized metro-area locations but excludes remote-only roles. Remote work must be requested deliberately.
4. **Source coverage** — provider routing can expand the public employer boards searched, but provider breadth never overrides occupation, level, or location filters.

## Occupation matching

Known role families retain their tuned recall behavior for broad searches such as software, data, marketing, operations, finance, healthcare, and legal work.

Queries outside that taxonomy use an occupation signature composed of:

- normalized occupation phrases and curated aliases;
- occupation head groups such as engineer, scientist, teacher, nurse, therapist, technician, attorney, designer, and skilled-trade titles;
- meaningful modifiers such as electrical, elementary, laboratory, physical, graphic, or social;
- conservative morphology for related occupation words.

Exact and near-exact occupation titles receive ranking bonuses. Candidates with conflicting occupations are rejected instead of being admitted because the description happens to contain a query word.

The original regression is now critical benchmark coverage:

- query: `Electrical Engineer`
- level: `Entry level`
- location: `Philadelphia`
- accepted: Philadelphia-area electrical-engineering titles
- rejected: analytics engineers, marketing assistants, remote-only U.S. roles, California roles, and other locations

## Location behavior

Explicit local searches are strict. They do not silently include U.S.-remote roles.

Recognized metro areas currently include Philadelphia, New York City, Washington DC, San Francisco, Boston, Chicago, Seattle, and Los Angeles. Metro aliases are intentionally explicit to avoid ambiguous abbreviations.

The Philadelphia metro mapping includes locations such as King of Prussia, Conshohocken, Malvern, Wayne, Radnor, Exton, West Chester, Newtown Square, Fort Washington, Horsham, Blue Bell, Plymouth Meeting, Audubon, Camden, Cherry Hill, Mount Laurel, and Wilmington.

## Cross-sector public source expansion

MarketLens retains the existing Greenhouse, Lever, Remote OK, and Remotive integrations and adds an optional SmartRecruiters public Posting API integration.

SmartRecruiters is treated as a collection of named public employer boards, not as a universal job-board search. A bounded, intent-selected subset is queried for each search, and the exact employers searched appear in source coverage reporting.

The curated source set broadens representation across:

- education and nonprofit work;
- laboratory science, life sciences, and research;
- engineering and manufacturing;
- healthcare and allied health;
- environmental services and utilities;
- media, communications, and creative work;
- government and public service;
- real estate, facilities, operations, and technical work;
- business, finance, data, and technology.

Source requests and posting-detail requests are bounded, cached, and concurrent so broader coverage does not create unbounded latency. Provider failures degrade to the remaining providers and external continuation links.

## Evaluation matrix

The deterministic benchmark now evaluates combined behavior rather than scoring occupation relevance without location:

- 20 intent cases
- 273 candidate cases
- 17 location cases
- 20 ranking cases
- 9 routing cases
- 55 critical cases

Candidate coverage contains positive and negative examples across nine required categories:

1. healthcare
2. education and liberal arts
3. science and research
4. engineering and the built environment
5. business, finance, and operations
6. legal and public service
7. trades, construction, and logistics
8. creative and communications
9. service, hospitality, transportation, and agriculture

Run the benchmark from `backend`:

```bash
python scripts/run_job_search_evaluation.py
```

Run the full backend suite:

```bash
python -m pytest
```

## Completion standard

Issue #39 is not complete merely because the deterministic benchmark passes. Before the issue is closed and Milestone 8 resumes, the pull request must also pass:

- the complete backend test suite;
- the frontend TypeScript/Vite build;
- backend and frontend Docker builds;
- live public-provider smoke tests across representative sectors;
- product-level validation of strict role, level, and location behavior.

Zero results are acceptable when the currently searched public employers do not have a valid match. Irrelevant results are not used to fill the page.
