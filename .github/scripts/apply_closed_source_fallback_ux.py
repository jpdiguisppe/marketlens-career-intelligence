from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Could not find expected {label} block")
    return text.replace(old, new, 1)


job_search_path = Path("backend/app/job_search.py")
job_search = job_search_path.read_text()
old_links = '''def _external_search_links(query: str, location: str | None, level: JobLevel) -> list[ExternalSearchLink]:
    external_query = _external_search_query(query, location, level)
    query_param = quote_plus(external_query)
    location_param = quote_plus(location or "United States")

    links = [
        ExternalSearchLink(
            label="Google Jobs search",
            url=f"https://www.google.com/search?q={quote_plus(external_query + ' jobs')}",
            note="Broad fallback when API-friendly sources are thin.",
        ),
        ExternalSearchLink(
            label="Indeed search",
            url=f"https://www.indeed.com/jobs?q={query_param}&l={location_param}",
            note="Useful for local, finance, accounting, healthcare, and operations roles.",
        ),
        ExternalSearchLink(
            label="LinkedIn Jobs search",
            url=f"https://www.linkedin.com/jobs/search/?keywords={query_param}&location={location_param}",
            note="Useful for professional internships and company-posted roles.",
        ),
    ]

    if level == "intern":
        links.append(
            ExternalSearchLink(
                label="Handshake search",
                url=f"https://app.joinhandshake.com/stu/postings?query={query_param}",
                note="Often stronger for campus internships, but usually requires a school login.",
            )
        )

    return links
'''
new_links = '''def _external_search_links(query: str, location: str | None, level: JobLevel) -> list[ExternalSearchLink]:
    external_query = _external_search_query(query, location, level)
    query_param = quote_plus(external_query)
    location_param = quote_plus(location or "United States")
    workday_query = quote_plus(
        f'(site:myworkdayjobs.com OR site:myworkdaysite.com) "{external_query}"'
    )

    links = [
        ExternalSearchLink(
            label="Google Jobs search",
            url=f"https://www.google.com/search?q={quote_plus(external_query + ' jobs')}",
            note="Broad external discovery link. MarketLens does not import or verify these results.",
        ),
        ExternalSearchLink(
            label="Indeed search",
            url=f"https://www.indeed.com/jobs?q={query_param}&l={location_param}",
            note="Useful for local and non-technical roles. Opens Indeed separately; MarketLens does not scrape it.",
        ),
        ExternalSearchLink(
            label="LinkedIn Jobs search",
            url=f"https://www.linkedin.com/jobs/search/?keywords={query_param}&location={location_param}",
            note="Useful for professional and company-posted roles. Login may be required.",
        ),
        ExternalSearchLink(
            label="Workday / company career-site search",
            url=f"https://www.google.com/search?q={workday_query}",
            note="Searches Google for indexed Workday postings without scraping Workday search pages.",
        ),
    ]

    if level in {"intern", "entry"}:
        links.append(
            ExternalSearchLink(
                label="Handshake search",
                url=f"https://app.joinhandshake.com/stu/postings?query={query_param}",
                note="Often stronger for campus internships and new-grad roles; usually requires a school login.",
            )
        )

    return links
'''
job_search = replace_once(job_search, old_links, new_links, "external search links")
job_search_path.write_text(job_search)

component_path = Path("frontend/src/JobSearchDiscoveryPanel.tsx")
component_path.write_text('''import { SafeExternalLink } from "./SafeExternalLink";
import type { ExternalSearchLink, SourceCoverage } from "./types";

export function JobSearchDiscoveryPanel({
  hasSearched,
  resultCount,
  sourceCoverage,
  searchSuggestions,
  externalSearchLinks,
}: {
  hasSearched: boolean;
  resultCount: number;
  sourceCoverage: SourceCoverage[];
  searchSuggestions: string[];
  externalSearchLinks: ExternalSearchLink[];
}) {
  if (!hasSearched) {
    return null;
  }

  const fetchedCount = sourceCoverage.reduce((total, source) => total + source.fetched_count, 0);
  const matchedCount = sourceCoverage.reduce((total, source) => total + source.matched_count, 0);

  return (
    <div className="smart-section">
      <section className="report-card">
        <div className="gap-group-header">
          <div>
            <p className="eyebrow inline-eyebrow">Search transparency</p>
            <h3>What MarketLens actually searched</h3>
          </div>
          <span className="status-badge status-mentioned">{resultCount} shown</span>
        </div>
        <p className="helper-text">
          MarketLens evaluated {fetchedCount.toLocaleString()} postings from its configured public sources and found {matchedCount.toLocaleString()} provider matches before ranking and deduplication. LinkedIn, Indeed, Handshake, and Workday were not queried or scraped.
        </p>
        <details open={resultCount === 0}>
          <summary>See source-by-source coverage</summary>
          <div className="action-list smart-section">
            {sourceCoverage.map((source) => (
              <article className="action-row" key={`${source.provider}-${source.label}`}>
                <span className="status-badge status-mentioned">{source.status}</span>
                <div>
                  <h4>{source.label}</h4>
                  <p>{source.fetched_count.toLocaleString()} fetched · {source.matched_count.toLocaleString()} matched</p>
                  {source.notes.length > 0 && (
                    <ul className="summary-list">
                      {source.notes.map((note) => <li key={note}>{note}</li>)}
                    </ul>
                  )}
                </div>
              </article>
            ))}
          </div>
        </details>
      </section>

      {searchSuggestions.length > 0 && (
        <div className="notice-box smart-warning-box">
          <strong>Ways to widen or refine this search</strong>
          <ul>
            {searchSuggestions.map((suggestion) => <li key={suggestion}>{suggestion}</li>)}
          </ul>
        </div>
      )}

      {externalSearchLinks.length > 0 && (
        <section className="report-card">
          <div className="gap-group-header">
            <div>
              <p className="eyebrow inline-eyebrow">Continue externally</p>
              <h3>Search closed platforms without pretending MarketLens searched them</h3>
            </div>
          </div>
          <p className="helper-text">
            These buttons open pre-filled searches on external sites. MarketLens does not collect those result pages. Open a relevant posting, copy its description, then paste it into manual Smart Fit below.
          </p>
          <div className="action-list smart-section">
            {externalSearchLinks.map((link) => (
              <article className="action-row" key={link.label}>
                <span className="status-badge status-mentioned">external</span>
                <div>
                  <h4><SafeExternalLink url={link.url}>{link.label}</SafeExternalLink></h4>
                  <p>{link.note}</p>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
''')

app_path = Path("frontend/src/App.tsx")
app = app_path.read_text()
app = replace_once(
    app,
    'import { SafeExternalLink } from "./SafeExternalLink";\n',
    'import { SafeExternalLink } from "./SafeExternalLink";\nimport { JobSearchDiscoveryPanel } from "./JobSearchDiscoveryPanel";\n',
    "JobSearchDiscoveryPanel import",
)
app = replace_once(
    app,
    '  ExternalJobPosting,\n',
    '  ExternalJobPosting,\n  ExternalSearchLink,\n',
    "ExternalSearchLink type import",
)
app = replace_once(
    app,
    '  SmartFitBatchResult,\n',
    '  SmartFitBatchResult,\n  SourceCoverage,\n',
    "SourceCoverage type import",
)
app = replace_once(
    app,
    '  const [jobSearchWarnings, setJobSearchWarnings] = useState<string[]>([]);\n  const [jobSearchError, setJobSearchError] = useState<string | null>(null);\n',
    '  const [jobSearchWarnings, setJobSearchWarnings] = useState<string[]>([]);\n  const [jobSearchCoverage, setJobSearchCoverage] = useState<SourceCoverage[]>([]);\n  const [jobSearchSuggestions, setJobSearchSuggestions] = useState<string[]>([]);\n  const [jobSearchLinks, setJobSearchLinks] = useState<ExternalSearchLink[]>([]);\n  const [hasCompletedJobSearch, setHasCompletedJobSearch] = useState(false);\n  const [jobSearchError, setJobSearchError] = useState<string | null>(null);\n',
    "job search discovery state",
)
app = replace_once(
    app,
    '      setJobSearchWarnings([]);\n      setSelectedExternalJobIds([]);\n',
    '      setJobSearchWarnings([]);\n      setJobSearchCoverage([]);\n      setJobSearchSuggestions([]);\n      setJobSearchLinks([]);\n      setHasCompletedJobSearch(false);\n      setSelectedExternalJobIds([]);\n',
    "job search start reset",
)
app = replace_once(
    app,
    '      setJobSearchResults(searchResult.results);\n      setJobSearchWarnings(searchResult.warnings);\n',
    '      setJobSearchResults(searchResult.results);\n      setJobSearchWarnings(searchResult.warnings);\n      setJobSearchCoverage(searchResult.source_coverage);\n      setJobSearchSuggestions(searchResult.search_suggestions);\n      setJobSearchLinks(searchResult.external_search_links);\n      setHasCompletedJobSearch(true);\n',
    "job search response state",
)
app = replace_once(
    app,
    '      setJobSearchResults([]);\n      setJobSearchWarnings([]);\n      setJobSearchError(\n',
    '      setJobSearchResults([]);\n      setJobSearchWarnings([]);\n      setJobSearchCoverage([]);\n      setJobSearchSuggestions([]);\n      setJobSearchLinks([]);\n      setHasCompletedJobSearch(false);\n      setJobSearchError(\n',
    "job search failure reset",
)
app = replace_once(
    app,
    '''        {jobSearchResults.length > 0 && (
          <div className="action-list smart-section">
            {jobSearchResults.map((job) => (
              <ExternalJobCard
                key={job.id}
                job={job}
                isSelected={selectedExternalJobIds.includes(job.id)}
                onToggle={() => toggleExternalJob(job.id)}
              />
            ))}
          </div>
        )}

        <div className="form-footer">
''',
    '''        {jobSearchResults.length > 0 && (
          <div className="action-list smart-section">
            {jobSearchResults.map((job) => (
              <ExternalJobCard
                key={job.id}
                job={job}
                isSelected={selectedExternalJobIds.includes(job.id)}
                onToggle={() => toggleExternalJob(job.id)}
              />
            ))}
          </div>
        )}

        <JobSearchDiscoveryPanel
          hasSearched={hasCompletedJobSearch}
          resultCount={jobSearchResults.length}
          sourceCoverage={jobSearchCoverage}
          searchSuggestions={jobSearchSuggestions}
          externalSearchLinks={jobSearchLinks}
        />

        <div className="form-footer">
''',
    "job search discovery panel rendering",
)
app_path.write_text(app)

test_path = Path("backend/tests/test_closed_source_fallbacks.py")
test_path.write_text('''from urllib.parse import parse_qs, unquote_plus, urlparse

from app.job_search import _external_search_links, _external_search_query


def _labels(query: str, level: str) -> set[str]:
    return {link.label for link in _external_search_links(query, "Philadelphia", level)}


def test_external_links_cover_closed_sources_without_claiming_they_were_searched() -> None:
    links = _external_search_links("software engineer", "Philadelphia", "entry")
    labels = {link.label for link in links}

    assert labels == {
        "Google Jobs search",
        "Indeed search",
        "LinkedIn Jobs search",
        "Workday / company career-site search",
        "Handshake search",
    }
    assert all(link.url.startswith("https://") for link in links)
    assert all("MarketLens" in link.note or "Login" in link.note or "requires" in link.note for link in links)


def test_handshake_is_available_for_intern_and_entry_searches_only() -> None:
    assert "Handshake search" in _labels("software engineer", "intern")
    assert "Handshake search" in _labels("software engineer", "entry")
    assert "Handshake search" not in _labels("software engineer", "mid")
    assert "Handshake search" not in _labels("software engineer", "senior")


def test_workday_fallback_uses_google_discovery_instead_of_scraping_workday() -> None:
    workday_link = next(
        link
        for link in _external_search_links("healthcare compliance analyst", "Philadelphia", "entry")
        if link.label == "Workday / company career-site search"
    )
    parsed = urlparse(workday_link.url)
    query = unquote_plus(parse_qs(parsed.query)["q"][0])

    assert parsed.scheme == "https"
    assert parsed.netloc == "www.google.com"
    assert "site:myworkdayjobs.com" in query
    assert "site:myworkdaysite.com" in query
    assert "healthcare compliance analyst" in query
    assert "Philadelphia" in query


def test_external_query_adds_level_and_location_once() -> None:
    assert _external_search_query("software engineer", "Philadelphia", "entry") == (
        "software engineer entry level Philadelphia"
    )
    assert _external_search_query("entry level software engineer", "Philadelphia", "entry") == (
        "entry level software engineer Philadelphia"
    )
    assert _external_search_query("legal internship", "Remote", "intern") == (
        "legal internship remote"
    )
''')

doc_path = Path("docs/milestone-7-closed-source-fallback-ux.md")
doc_path.write_text('''# Milestone 7 — Closed-Source Fallback UX

MarketLens searches only configured API-friendly public sources. LinkedIn, Indeed, Handshake, and Workday search pages are not scraped or represented as searched providers.

## User workflow

After every completed search, the Smart Fit screen now shows:

1. **What MarketLens actually searched** — provider-by-provider fetched and matched counts plus routing/coverage notes.
2. **Ways to widen or refine the search** — the backend's existing query and location suggestions.
3. **Continue externally** — pre-filled outbound links for Google Jobs, Indeed, LinkedIn, Workday/company career sites, and Handshake for internship or entry-level searches.
4. **Bring the posting back** — users can copy an external job description and paste it into manual Smart Fit for the same deterministic or model-assisted analysis.

## Responsible source boundary

- External links are navigation aids, not imported search results.
- MarketLens does not bypass logins, crawl result pages, or imply source coverage it does not have.
- The Workday option uses a Google site-restricted discovery query for indexed postings rather than scraping Workday tenant search pages.
- Handshake is included for both internship and entry-level searches because campus systems frequently cover new-graduate roles as well as internships.
- All outbound URLs remain HTTPS and pass through the frontend's safe external-link component.
''')
