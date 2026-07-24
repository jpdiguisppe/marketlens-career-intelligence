import { SafeExternalLink } from "./SafeExternalLink";
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
