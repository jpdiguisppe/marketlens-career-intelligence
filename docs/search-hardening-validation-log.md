# Search Hardening Validation Log

This log records the validation work for Issue #39 and PR #40.

## Deterministic benchmark

The expanded formal benchmark passes with:

- 20 intent cases
- 273 candidate cases
- 17 location cases
- 20 ranking cases
- 9 routing cases
- 55 critical cases
- 100% intent accuracy
- 100% candidate accuracy, precision, and recall
- 100% negative rejection
- 100% location accuracy
- 100% ranking accuracy
- 100% routing accuracy
- 100% critical-case pass rate

The benchmark cannot silently shrink back to a narrow role set. Tests enforce positive, negative, unique-query, and critical-case minimums across nine required sector groups.

## Integrated cross-sector matrices

The formal benchmark is supplemented by two integrated matrices:

- 27 occupation + entry-level + location candidate cases across nine sector groups
- 9 ranking cases that compare an exact local match, an exact remote match, and a wrong local occupation
- 14 mid/senior occupation + location cases across seven sector groups

The required sector groups are:

1. healthcare
2. education and liberal arts
3. science and research
4. engineering and the built environment
5. business, finance, and operations
6. legal and public service
7. trades, construction, and logistics
8. creative and communications
9. service, hospitality, transportation, and agriculture

## Complete hosted validation

The final branch passed:

- 290 backend tests
- frontend TypeScript/Vite production build
- backend Docker image build
- frontend Docker image build
- focused search-hardening diagnostics
- strict local live-provider smoke tests
- broadened U.S.-wide live-provider smoke tests

## Regressions discovered and fixed

The broader validation work found defects that the earlier benchmark did not cover:

1. `Technology Rotational Program` was rejected for `software engineer entry level` even when the description explicitly rotated through software-engineering and backend teams.
2. `Analytics Engineer` was rejected as a recognized data-family neighbor for `data analyst`.
3. Strict city filtering worked, but no-result text still incorrectly claimed that U.S.-remote roles had been included.
4. Occupational titles such as `Staff Reporter` could be treated as senior merely because they contained `Staff`.
5. `elementary school teacher` admitted middle-school titles because the school-level modifier was not preserved strongly enough.
6. `journalism` admitted a cinematic AI video editor because generic editor language outweighed the missing newsroom context.
7. SmartRecruiters detail retrieval could let later-rejected lead/senior titles crowd valid entry roles out of an eight-posting shortlist.
8. Specific entry-level occupation searches rejected plain titles with no stated experience requirement, even when no evidence contradicted entry-level eligibility.

The fixes preserve important boundaries:

- broad family searches such as `computer science` still require actual entry evidence;
- unlabeled entry compatibility applies only to specific occupation searches;
- explicit `I`, `junior`, and `entry-level` titles rank above unlabeled compatible titles;
- senior, numbered mid-level, managerial, qualitative-experience, and four-plus-year requirements remain rejected from entry searches;
- grade-level elementary aliases such as `3rd Grade Teacher` are supported without admitting middle-school roles;
- broad `teacher` and `video editor` searches remain broad;
- journalism requires newsroom/editorial/reporting evidence when an editor title is otherwise film- or video-oriented.

## Live public-provider validation

The strict live pass executed ten representative `entry` + `Philadelphia` searches across the required sectors.

Results:

- all 10 scenarios reached at least one successfully searched provider
- 34,020 provider postings were fetched across the ten independent searches before occupation, level, location, deduplication, and ranking filters
- no closed job board was reported as searched
- no remote-only posting leaked into an explicit Philadelphia search
- all returned application and continuation links were HTTPS
- current Philadelphia inventory remained sparse, but valid local results were returned when available
- `elementary school teacher` returned KIPP's `[2026-2027] Elementary School Social Studies Teacher` in Philadelphia
- `journalism` returned `Multi-Media Journalist, Telemundo T62 Filadelfia`

The broadened U.S.-wide pass used the same ten occupations with `level=any` and no location restriction.

Results:

- 9 of 10 searches returned at least one valid live posting
- 7 searches returned multiple candidates for ordering validation
- 55 valid results were returned in total
- all nine required sector groups were represented
- elementary results remained elementary/K-5 roles
- journalism results remained newsroom, reporter, assignment-editor, or editorial roles

The one current zero-result breadth scenario was `agronomist`. Syngenta Group was selected and queried as the verified agriculture source, but the current public inventory did not contain a valid matching U.S. posting during this run.

## Source coverage boundary

MarketLens now queries named public Greenhouse, Lever, and SmartRecruiters employer boards plus Remote OK and Remotive. SmartRecruiters is not treated as a universal job board. The source set includes verified boards across education, science, engineering, healthcare, public service, media, trades, agriculture, delivery/service work, business, and technology.

LinkedIn, Indeed, Handshake, Workday search pages, school portals, and every company career site are not scraped or falsely reported as searched. The product continues to expose responsible external continuation links and manual Smart Fit for postings outside the configured public sources.

## Completion conclusion

The old 74-case score was not sufficient evidence of broad correctness. Issue #39 is supported instead by enforced cross-sector breadth, integrated occupation + level + location cases, the complete application suite, container builds, and reviewed live-provider results. Milestone 8 may resume only after the merged change is also verified in the deployed Railway product.
