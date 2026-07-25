import { useEffect, useState } from "react";

import { SafeExternalLink } from "./SafeExternalLink";
import type { ExternalSearchLink, SourceCoverage } from "./types";
import "./JobSearchDiscoveryPanel.css";

type DiscoveryTab = "external" | "details";

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
  const [activeTab, setActiveTab] = useState<DiscoveryTab>("external");

  useEffect(() => {
    if (hasSearched) {
      setActiveTab(resultCount === 0 ? "external" : "details");
    }
  }, [hasSearched, resultCount]);

  if (!hasSearched) {
    return null;
  }

  const fetchedCount = sourceCoverage.reduce((total, source) => total + source.fetched_count, 0);
  const matchedCount = sourceCoverage.reduce((total, source) => total + source.matched_count, 0);

  const externalPanel = (
    <div className="search-discovery-panel-content">
      <p className="helper-text">
        Open a pre-filled search, copy a relevant posting, then paste its description into manual Smart Fit below. MarketLens does not collect or scrape these result pages.
      </p>
      <div className="external-search-link-grid">
        {externalSearchLinks.map((link) => (
          <article className="external-search-link-card" key={link.label}>
            <SafeExternalLink url={link.url}>{link.label}</SafeExternalLink>
            <p>{link.note}</p>
          </article>
        ))}
      </div>
    </div>
  );

  const detailsPanel = (
    <div className="search-discovery-panel-content">
      <div className="search-coverage-summary">
        <div>
          <strong>{fetchedCount.toLocaleString()}</strong>
          <span>postings checked</span>
        </div>
        <div>
          <strong>{matchedCount.toLocaleString()}</strong>
          <span>provider matches</span>
        </div>
        <div>
          <strong>{resultCount.toLocaleString()}</strong>
          <span>results shown</span>
        </div>
      </div>
      <p className="helper-text">
        MarketLens searched only its configured public sources. LinkedIn, Indeed, Handshake, and Workday were not queried or scraped.
      </p>

      {searchSuggestions.length > 0 && (
        <div className="search-refinement-list">
          <strong>Ways to widen or refine this search</strong>
          <ul className="summary-list">
            {searchSuggestions.map((suggestion) => <li key={suggestion}>{suggestion}</li>)}
          </ul>
        </div>
      )}

      <details className="details-panel source-coverage-details">
        <summary>View source-by-source coverage</summary>
        <div className="source-coverage-list">
          {sourceCoverage.map((source) => (
            <article className="source-coverage-row" key={`${source.provider}-${source.label}`}>
              <div className="source-coverage-row-header">
                <div>
                  <h4>{source.label}</h4>
                  <p>{source.fetched_count.toLocaleString()} fetched · {source.matched_count.toLocaleString()} matched</p>
                </div>
                <span className="status-badge status-mentioned">{source.status}</span>
              </div>
              {source.notes.length > 0 && (
                <ul className="summary-list">
                  {source.notes.map((note) => <li key={note}>{note}</li>)}
                </ul>
              )}
            </article>
          ))}
        </div>
      </details>
    </div>
  );

  if (resultCount > 0) {
    return (
      <details className="details-panel search-discovery-collapsible smart-section">
        <summary>View search coverage and external options</summary>
        <div className="search-discovery-collapsible-content">
          <section>
            <p className="eyebrow inline-eyebrow">Search details</p>
            {detailsPanel}
          </section>
          {externalSearchLinks.length > 0 && (
            <section>
              <p className="eyebrow inline-eyebrow">Continue externally</p>
              {externalPanel}
            </section>
          )}
        </div>
      </details>
    );
  }

  return (
    <section className="search-discovery-tabs smart-section" aria-label="No-result search options">
      <div className="search-discovery-tab-list" role="tablist" aria-label="Search follow-up options">
        <button
          className={`search-discovery-tab${activeTab === "external" ? " active" : ""}`}
          type="button"
          role="tab"
          aria-selected={activeTab === "external"}
          aria-controls="search-discovery-external-panel"
          id="search-discovery-external-tab"
          onClick={() => setActiveTab("external")}
        >
          <span>Search elsewhere</span>
          <small>Open external job searches</small>
        </button>
        <button
          className={`search-discovery-tab${activeTab === "details" ? " active" : ""}`}
          type="button"
          role="tab"
          aria-selected={activeTab === "details"}
          aria-controls="search-discovery-details-panel"
          id="search-discovery-details-tab"
          onClick={() => setActiveTab("details")}
        >
          <span>Why no results?</span>
          <small>Review coverage and suggestions</small>
        </button>
      </div>

      <div
        id="search-discovery-external-panel"
        role="tabpanel"
        aria-labelledby="search-discovery-external-tab"
        hidden={activeTab !== "external"}
      >
        {externalSearchLinks.length > 0 ? externalPanel : (
          <p className="helper-text">No external continuation links are available for this search.</p>
        )}
      </div>

      <div
        id="search-discovery-details-panel"
        role="tabpanel"
        aria-labelledby="search-discovery-details-tab"
        hidden={activeTab !== "details"}
      >
        {detailsPanel}
      </div>
    </section>
  );
}
