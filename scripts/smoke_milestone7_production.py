from __future__ import annotations

import json
import os
import re
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

BACKEND_URL = os.getenv(
    "MARKETLENS_BACKEND_URL",
    "https://marketlens-career-intelligence-production.up.railway.app",
).rstrip("/")
FRONTEND_URL = os.getenv(
    "MARKETLENS_FRONTEND_URL",
    "https://marketlens-career-intelligence-production-8a34.up.railway.app",
).rstrip("/")

REQUEST_TIMEOUT_SECONDS = 150
DEPLOYMENT_ATTEMPTS = 15
DEPLOYMENT_RETRY_SECONDS = 20


def _request_text(url: str, *, timeout: int = REQUEST_TIMEOUT_SECONDS) -> tuple[int, str]:
    request = Request(
        url,
        headers={
            "User-Agent": "MarketLens-Milestone-7-Smoke-Test/1.0",
            "Accept": "application/json,text/html,*/*",
            "Cache-Control": "no-cache",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AssertionError(f"HTTP {exc.code} from {url}: {body[:500]}") from exc
    except (URLError, TimeoutError) as exc:
        raise AssertionError(f"Request failed for {url}: {exc}") from exc


def _request_json(path: str, params: dict[str, str | int] | None = None) -> dict[str, Any]:
    url = f"{BACKEND_URL}{path}"
    if params:
        url = f"{url}?{urlencode(params)}"
    status, body = _request_text(url)
    assert status == 200, f"Expected HTTP 200 from {url}, got {status}"
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Expected JSON from {url}, got: {body[:500]}") from exc
    assert isinstance(payload, dict), f"Expected object JSON from {url}"
    return payload


def _frontend_bundle_markers() -> dict[str, Any]:
    cache_buster = int(time.time())
    status, html = _request_text(f"{FRONTEND_URL}/?milestone7_smoke={cache_buster}")
    assert status == 200, f"Frontend returned HTTP {status}"
    assert 'id="root"' in html or "id='root'" in html, "Frontend HTML is missing the React root"

    script_sources = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
    assert script_sources, "Frontend HTML did not expose a JavaScript bundle"

    bundle_texts: list[str] = []
    fetched_assets: list[str] = []
    for source in script_sources:
        asset_url = urljoin(f"{FRONTEND_URL}/", source)
        asset_status, asset_text = _request_text(asset_url)
        if asset_status == 200:
            fetched_assets.append(asset_url)
            bundle_texts.append(asset_text)

    combined = "\n".join(bundle_texts)
    required_markers = [
        "What MarketLens actually searched",
        "Continue externally",
    ]
    missing_markers = [marker for marker in required_markers if marker not in combined]
    assert not missing_markers, (
        "Deployed frontend bundle is missing Milestone 7 discovery UX markers: "
        + ", ".join(missing_markers)
    )

    return {
        "status": status,
        "script_assets_checked": fetched_assets,
        "markers_found": required_markers,
    }


def _wait_for_deployment() -> dict[str, Any]:
    failures: list[str] = []
    for attempt in range(1, DEPLOYMENT_ATTEMPTS + 1):
        try:
            health = _request_json("/health")
            assert health == {"status": "ok"}, f"Unexpected health payload: {health}"
            frontend = _frontend_bundle_markers()
            return {"attempt": attempt, "health": health, "frontend": frontend}
        except AssertionError as exc:
            failures.append(f"attempt {attempt}: {exc}")
            if attempt < DEPLOYMENT_ATTEMPTS:
                time.sleep(DEPLOYMENT_RETRY_SECONDS)

    raise AssertionError("Production did not reach the expected deployment state:\n" + "\n".join(failures[-5:]))


def _assert_search_contract(payload: dict[str, Any]) -> None:
    required_keys = {
        "query",
        "location",
        "level",
        "role_family",
        "industry",
        "providers_searched",
        "result_count",
        "results",
        "warnings",
        "source_coverage",
        "search_suggestions",
        "external_search_links",
    }
    assert required_keys.issubset(payload), f"Search response missing keys: {sorted(required_keys - payload.keys())}"
    assert payload["result_count"] == len(payload["results"])
    assert isinstance(payload["source_coverage"], list) and payload["source_coverage"], "Source coverage is missing"
    assert isinstance(payload["external_search_links"], list) and payload["external_search_links"], "External links are missing"

    closed_sources = {"linkedin", "indeed", "handshake", "workday"}
    searched = " ".join(str(provider).lower() for provider in payload["providers_searched"])
    assert not any(source in searched for source in closed_sources), (
        "Closed platforms were incorrectly reported as searched providers: " + searched
    )

    for result in payload["results"]:
        assert str(result.get("apply_url", "")).startswith("https://"), "Result apply URL is not HTTPS"

    for coverage in payload["source_coverage"]:
        assert {"provider", "label", "status", "fetched_count", "matched_count", "notes"}.issubset(coverage)
        assert coverage["fetched_count"] >= 0
        assert coverage["matched_count"] >= 0

    for link in payload["external_search_links"]:
        assert str(link.get("url", "")).startswith("https://"), "External search link is not HTTPS"
        assert link.get("label") and link.get("note")


def _run_search(
    *,
    query: str,
    location: str,
    level: str,
    expected_role_family: str,
    expected_industry: str | None,
) -> dict[str, Any]:
    payload = _request_json(
        "/jobs/search",
        {
            "query": query,
            "location": location,
            "level": level,
            "limit": 5,
        },
    )
    _assert_search_contract(payload)
    assert payload["level"] == level, f"Wrong level for {query!r}: {payload['level']}"
    assert payload["role_family"] == expected_role_family, (
        f"Wrong role family for {query!r}: {payload['role_family']}"
    )
    assert payload["industry"] == expected_industry, (
        f"Wrong industry for {query!r}: {payload['industry']}"
    )

    labels = {link["label"] for link in payload["external_search_links"]}
    expected_labels = {
        "Google Jobs search",
        "Indeed search",
        "LinkedIn Jobs search",
        "Workday / company career-site search",
        "Handshake search",
    }
    assert expected_labels.issubset(labels), f"Missing fallback links for {query!r}: {sorted(expected_labels - labels)}"

    workday_link = next(
        link for link in payload["external_search_links"]
        if link["label"] == "Workday / company career-site search"
    )
    assert "myworkdayjobs" in workday_link["url"] or "myworkdaysite" in workday_link["url"]

    return {
        "query": payload["query"],
        "location": payload["location"],
        "level": payload["level"],
        "role_family": payload["role_family"],
        "industry": payload["industry"],
        "result_count": payload["result_count"],
        "providers_searched": payload["providers_searched"],
        "coverage": [
            {
                "provider": item["provider"],
                "status": item["status"],
                "fetched_count": item["fetched_count"],
                "matched_count": item["matched_count"],
            }
            for item in payload["source_coverage"]
        ],
        "external_link_labels": sorted(labels),
        "warnings": payload["warnings"],
        "result_titles": [result["title"] for result in payload["results"]],
    }


def main() -> int:
    report: dict[str, Any] = {
        "backend_url": BACKEND_URL,
        "frontend_url": FRONTEND_URL,
        "deployment": _wait_for_deployment(),
    }

    model_status = _request_json("/analysis/model-status")
    assert {"enabled", "status", "required_backend_settings", "safety_notes"}.issubset(model_status)
    report["model_status"] = {
        "enabled": model_status["enabled"],
        "status": model_status["status"],
        "safety_note_count": len(model_status["safety_notes"]),
    }

    searches = [
        _run_search(
            query="sports marketing internship",
            location="Philadelphia",
            level="intern",
            expected_role_family="marketing",
            expected_industry="sports",
        ),
        _run_search(
            query="healthcare compliance analyst entry level",
            location="Philadelphia",
            level="entry",
            expected_role_family="compliance",
            expected_industry="healthcare",
        ),
        _run_search(
            query="legal internship",
            location="Philadelphia",
            level="intern",
            expected_role_family="legal",
            expected_industry="legal_services",
        ),
        _run_search(
            query="law student judicial internship",
            location="Philadelphia",
            level="intern",
            expected_role_family="legal",
            expected_industry=None,
        ),
    ]

    banned_undergrad_titles = ("attorney", "counsel", "summer associate", "law clerk")
    legal_undergrad = searches[2]
    for title in legal_undergrad["result_titles"]:
        assert not any(term in title.lower() for term in banned_undergrad_titles), (
            f"Undergraduate legal search admitted credential-mismatched title: {title}"
        )

    report["searches"] = searches
    report["status"] = "passed"
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"MILESTONE 7 PRODUCTION SMOKE TEST FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
