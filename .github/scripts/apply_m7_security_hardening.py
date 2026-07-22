from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} match, found {count}")
    return text.replace(old, new, 1)


root = Path(".")
registry_path = root / "backend/app/job_source_registry.py"
search_path = root / "backend/app/job_search.py"
main_path = root / "backend/app/main.py"
saved_jobs_path = root / "backend/app/saved_jobs.py"
saved_reports_path = root / "backend/app/saved_reports.py"
app_path = root / "frontend/src/App.tsx"
frontend_saved_jobs_path = root / "frontend/src/SavedJobs.tsx"
frontend_saved_reports_path = root / "frontend/src/SavedReports.tsx"
registry_tests_path = root / "backend/tests/test_job_source_registry.py"
docs_path = root / "docs/milestone-7-source-registry.md"

external_urls_content = '''from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

MAX_EXTERNAL_URL_LENGTH = 2_048


def sanitize_external_https_url(value: str | None) -> str | None:
    """Return a safe HTTPS URL or None.

    External posting links are displayed to users but are never fetched by
    MarketLens. Reject credentials, local/private hosts, control characters,
    non-HTTPS schemes, and unusual ports before a link reaches the UI or DB.
    """

    if value is None:
        return None

    cleaned = value.strip()
    if not cleaned or len(cleaned) > MAX_EXTERNAL_URL_LENGTH:
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in cleaned):
        return None

    try:
        parsed = urlsplit(cleaned)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        return None

    if parsed.scheme.lower() != "https" or not hostname:
        return None
    if parsed.username or parsed.password:
        return None
    if port not in {None, 443}:
        return None

    normalized_hostname = hostname.rstrip(".").lower()
    if not normalized_hostname or len(normalized_hostname) > 253:
        return None
    if normalized_hostname == "localhost" or normalized_hostname.endswith(".localhost"):
        return None

    try:
        address = ipaddress.ip_address(normalized_hostname)
    except ValueError:
        address = None

    if address is not None and (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        return None

    return cleaned


def require_external_https_url(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None

    sanitized = sanitize_external_https_url(value)
    if sanitized is None:
        raise ValueError("External links must use a public HTTPS URL without embedded credentials.")
    return sanitized
'''
(root / "backend/app/external_urls.py").write_text(external_urls_content)

frontend_security_content = '''export function safeExternalHttpsUrl(
  value: string | null | undefined,
): string | null {
  if (!value) {
    return null;
  }

  try {
    const parsed = new URL(value);
    const hostname = parsed.hostname.toLowerCase().replace(/\\.$/, "");

    if (parsed.protocol !== "https:") {
      return null;
    }
    if (parsed.username || parsed.password) {
      return null;
    }
    if (parsed.port && parsed.port !== "443") {
      return null;
    }
    if (hostname === "localhost" || hostname.endsWith(".localhost")) {
      return null;
    }
    if (/^(127\\.|0\\.|10\\.|192\\.168\\.|169\\.254\\.)/.test(hostname)) {
      return null;
    }
    if (/^172\\.(1[6-9]|2\\d|3[01])\\./.test(hostname)) {
      return null;
    }
    if (hostname === "::1" || hostname.startsWith("fc") || hostname.startsWith("fd")) {
      return null;
    }

    return parsed.toString();
  } catch {
    return null;
  }
}
'''
(root / "frontend/src/security.ts").write_text(frontend_security_content)

safe_link_content = '''import type { ReactNode } from "react";

import { safeExternalHttpsUrl } from "./security";

export function SafeExternalLink({
  url,
  children,
}: {
  url: string | null | undefined;
  children: ReactNode;
}) {
  const safeUrl = safeExternalHttpsUrl(url);
  if (!safeUrl) {
    return null;
  }

  return (
    <a href={safeUrl} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  );
}
'''
(root / "frontend/src/SafeExternalLink.tsx").write_text(safe_link_content)

registry = registry_path.read_text()
registry = replace_once(
    registry,
    '''from dataclasses import dataclass
from typing import Literal
''',
    '''from dataclasses import dataclass
import re
from typing import Literal
''',
    "registry imports",
)
registry = replace_once(
    registry,
    '''DEFAULT_COVERAGE_NOTE = (
    "Official public ATS board. Available roles and locations change with the organization's current postings."
)
''',
    '''DEFAULT_COVERAGE_NOTE = (
    "Official public ATS board. Available roles and locations change with the organization's current postings."
)
SOURCE_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def normalize_source_identifier(identifier: str) -> str | None:
    normalized = identifier.strip().lower()
    if not SOURCE_IDENTIFIER_PATTERN.fullmatch(normalized):
        return None
    return normalized
''',
    "registry identifier constants",
)
registry = replace_once(
    registry,
    '''    return JobSourceRegistryEntry(
        provider=provider,
        identifier=identifier,
''',
    '''    normalized_identifier = normalize_source_identifier(identifier)
    if normalized_identifier is None:
        raise ValueError(f"Invalid {provider} source identifier: {identifier!r}")

    return JobSourceRegistryEntry(
        provider=provider,
        identifier=normalized_identifier,
''',
    "registry source construction",
)
registry = replace_once(
    registry,
    '''def find_source(
    identifier: str,
    provider: Provider | None = None,
) -> JobSourceRegistryEntry | None:
    normalized_identifier = identifier.strip().lower()
    for entry in SOURCE_REGISTRY:
        if entry.identifier == normalized_identifier and (
            provider is None or entry.provider == provider
        ):
            return entry
    return None


''',
    '''def find_source(
    identifier: str,
    provider: Provider | None = None,
) -> JobSourceRegistryEntry | None:
    normalized_identifier = normalize_source_identifier(identifier)
    if normalized_identifier is None:
        return None

    for entry in SOURCE_REGISTRY:
        if entry.identifier == normalized_identifier and (
            provider is None or entry.provider == provider
        ):
            return entry
    return None


def configured_source_identifiers(
    provider: Provider,
    raw_identifiers: str | None,
) -> tuple[str, ...]:
    """Resolve environment configuration through the registry allowlist.

    Invalid, disabled, duplicate, and unregistered identifiers are ignored.
    An empty or fully rejected configuration safely falls back to the enabled
    registry defaults rather than creating arbitrary outbound request targets.
    """

    defaults = default_source_identifiers(provider)
    if not raw_identifiers:
        return defaults

    selected: list[str] = []
    for raw_identifier in raw_identifiers.split(","):
        normalized = normalize_source_identifier(raw_identifier)
        if normalized is None or normalized in selected:
            continue
        entry = find_source(normalized, provider)
        if entry is not None and entry.enabled:
            selected.append(normalized)

    return tuple(selected) or defaults


''',
    "registry configured allowlist",
)
registry_path.write_text(registry)

search = search_path.read_text()
search = replace_once(
    search,
    '''import os
import re
import time
from dataclasses import dataclass, field
''',
    '''import os
import re
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
''',
    "job search imports",
)
search = replace_once(
    search,
    '''from app.job_source_registry import default_source_identifiers, organization_name
''',
    '''from app.external_urls import sanitize_external_https_url
from app.job_source_registry import (
    configured_source_identifiers,
    default_source_identifiers,
    organization_name,
)
''',
    "job search registry imports",
)
search = replace_once(
    search,
    '''REMOTEOK_CACHE_SECONDS = 15 * 60
REMOTIVE_CACHE_SECONDS = 6 * 60 * 60
''',
    '''REMOTEOK_CACHE_SECONDS = 15 * 60
REMOTIVE_CACHE_SECONDS = 6 * 60 * 60
DEFAULT_PROVIDER_CACHE_SECONDS = 5 * 60
DEFAULT_MAX_PROVIDER_REQUESTS_PER_SEARCH = 48
MIN_PROVIDER_REQUESTS_PER_SEARCH = 4
MAX_PROVIDER_REQUESTS_PER_SEARCH = 50
''',
    "provider safety constants",
)
search = replace_once(
    search,
    '''_REMOTEOK_CACHE: dict[str, Any] = {"expires_at": 0.0, "jobs": []}
_REMOTIVE_CACHE: dict[str, dict[str, Any]] = {}
''',
    '''_REMOTEOK_CACHE: dict[str, Any] = {"expires_at": 0.0, "jobs": []}
_REMOTIVE_CACHE: dict[str, dict[str, Any]] = {}
_ATS_PROVIDER_CACHE: dict[str, dict[str, Any]] = {}


class ProviderRequestBudgetExceeded(RuntimeError):
    pass


@dataclass
class _ProviderRequestBudget:
    remaining: int
    consumed: int = 0

    def consume(self) -> None:
        if self.remaining <= 0:
            raise ProviderRequestBudgetExceeded("Provider request budget exhausted.")
        self.remaining -= 1
        self.consumed += 1


_ACTIVE_PROVIDER_REQUEST_BUDGET: ContextVar[_ProviderRequestBudget | None] = ContextVar(
    "marketlens_provider_request_budget",
    default=None,
)
''',
    "provider cache and budget state",
)
search = replace_once(
    search,
    '''def _configured_greenhouse_boards() -> list[str]:
    raw_boards = os.getenv("JOB_SEARCH_GREENHOUSE_BOARDS")
    if raw_boards:
        boards = [board.strip() for board in raw_boards.split(",") if board.strip()]
        return boards or list(DEFAULT_GREENHOUSE_BOARDS)
    return list(DEFAULT_GREENHOUSE_BOARDS)


def _configured_lever_sites() -> list[str]:
    raw_sites = os.getenv("JOB_SEARCH_LEVER_SITES")
    if raw_sites:
        sites = [site.strip() for site in raw_sites.split(",") if site.strip()]
        return sites or list(DEFAULT_LEVER_SITES)
    return list(DEFAULT_LEVER_SITES)
''',
    '''def _configured_greenhouse_boards() -> list[str]:
    return list(
        configured_source_identifiers(
            "greenhouse",
            os.getenv("JOB_SEARCH_GREENHOUSE_BOARDS"),
        )
    )


def _configured_lever_sites() -> list[str]:
    return list(
        configured_source_identifiers(
            "lever",
            os.getenv("JOB_SEARCH_LEVER_SITES"),
        )
    )
''',
    "configured provider allowlist",
)
provider_helpers = '''

def _bounded_env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        parsed = int(raw_value)
    except ValueError:
        return default
    return max(minimum, min(parsed, maximum))


def _provider_request_limit() -> int:
    return _bounded_env_int(
        "JOB_SEARCH_MAX_PROVIDER_REQUESTS",
        DEFAULT_MAX_PROVIDER_REQUESTS_PER_SEARCH,
        MIN_PROVIDER_REQUESTS_PER_SEARCH,
        MAX_PROVIDER_REQUESTS_PER_SEARCH,
    )


def _provider_cache_seconds() -> int:
    return _bounded_env_int(
        "JOB_SEARCH_PROVIDER_CACHE_SECONDS",
        DEFAULT_PROVIDER_CACHE_SECONDS,
        60,
        3_600,
    )


def _consume_provider_request() -> None:
    budget = _ACTIVE_PROVIDER_REQUEST_BUDGET.get()
    if budget is not None:
        budget.consume()


def _cached_ats_jobs(cache_key: str) -> list[dict[str, Any]] | None:
    cached = _ATS_PROVIDER_CACHE.get(cache_key)
    if not cached or time.monotonic() >= float(cached.get("expires_at", 0.0)):
        return None
    jobs = cached.get("jobs")
    if not isinstance(jobs, list):
        return None
    return jobs


def _store_ats_jobs(cache_key: str, jobs: list[dict[str, Any]]) -> None:
    _ATS_PROVIDER_CACHE[cache_key] = {
        "expires_at": time.monotonic() + _provider_cache_seconds(),
        "jobs": jobs,
    }


def _build_provider_client() -> httpx.Client:
    # Provider APIs are already HTTPS. Do not follow an unexpected redirect to
    # a different host; a 3xx response is treated as a failed provider request.
    return httpx.Client(timeout=8.0, follow_redirects=False)
'''
search = replace_once(
    search,
    '''def clean_job_description(value: str | None) -> str:
''',
    provider_helpers + '''

def clean_job_description(value: str | None) -> str:
''',
    "provider safety helpers",
)
search = replace_once(
    search,
    '''    apply_url = str(raw_job.get("absolute_url") or "").strip()
    if not job_id or not title or not apply_url:
        return None
''',
    '''    apply_url = sanitize_external_https_url(str(raw_job.get("absolute_url") or ""))
    if not job_id or not title or apply_url is None:
        return None
''',
    "greenhouse URL validation",
)
search = replace_once(
    search,
    '''    apply_url = str(raw_job.get("hostedUrl") or raw_job.get("applyUrl") or "").strip()
    if not job_id or not title or not apply_url:
        return None
''',
    '''    apply_url = sanitize_external_https_url(
        str(raw_job.get("hostedUrl") or raw_job.get("applyUrl") or "")
    )
    if not job_id or not title or apply_url is None:
        return None
''',
    "lever URL validation",
)
search = replace_once(
    search,
    '''    apply_url = str(raw_job.get("url") or raw_job.get("apply_url") or "").strip()
    if not job_id or not title or not company or not apply_url:
        return None
''',
    '''    apply_url = sanitize_external_https_url(
        str(raw_job.get("url") or raw_job.get("apply_url") or "")
    )
    if not job_id or not title or not company or apply_url is None:
        return None
''',
    "remoteok URL validation",
)
search = replace_once(
    search,
    '''    apply_url = str(raw_job.get("url") or "").strip()
    if not job_id or not title or not company or not apply_url:
        return None
''',
    '''    apply_url = sanitize_external_https_url(str(raw_job.get("url") or ""))
    if not job_id or not title or not company or apply_url is None:
        return None
''',
    "remotive URL validation",
)
ats_fetch_helpers = '''

def _greenhouse_jobs_for_board(
    client: httpx.Client,
    board_token: str,
) -> list[dict[str, Any]]:
    cache_key = f"greenhouse:{board_token}"
    cached = _cached_ats_jobs(cache_key)
    if cached is not None:
        return cached

    _consume_provider_request()
    response = client.get(
        f"{GREENHOUSE_BASE_URL}/{board_token}/jobs",
        params={"content": "true"},
    )
    response.raise_for_status()
    payload = response.json()
    raw_jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    jobs = [job for job in raw_jobs if isinstance(job, dict)] if isinstance(raw_jobs, list) else []
    _store_ats_jobs(cache_key, jobs)
    return jobs


def _lever_jobs_for_site(
    client: httpx.Client,
    site_name: str,
) -> list[dict[str, Any]]:
    cache_key = f"lever:{site_name}"
    cached = _cached_ats_jobs(cache_key)
    if cached is not None:
        return cached

    _consume_provider_request()
    response = client.get(
        f"{LEVER_BASE_URL}/{site_name}",
        params={"mode": "json", "limit": str(MAX_PROVIDER_RESULTS_PER_BOARD)},
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    payload = response.json()
    jobs = [job for job in payload if isinstance(job, dict)] if isinstance(payload, list) else []
    _store_ats_jobs(cache_key, jobs)
    return jobs
'''
search = replace_once(
    search,
    '''def _search_greenhouse_boards(
''',
    ats_fetch_helpers + '''

def _search_greenhouse_boards(
''',
    "ATS fetch helpers",
)
search = replace_once(
    search,
    '''    errors = 0

    for board_token in board_tokens:
        try:
            response = client.get(f"{GREENHOUSE_BASE_URL}/{board_token}/jobs", params={"content": "true"})
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            errors += 1
            continue

        raw_jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
        if not isinstance(raw_jobs, list):
            continue
''',
    '''    errors = 0
    budget_exhausted = False

    for board_token in board_tokens:
        try:
            raw_jobs = _greenhouse_jobs_for_board(client, board_token)
        except ProviderRequestBudgetExceeded:
            budget_exhausted = True
            break
        except (httpx.HTTPError, ValueError):
            errors += 1
            continue
''',
    "greenhouse budgeted fetch loop",
)
search = replace_once(
    search,
    '''    if errors:
        notes.append(f"{errors} Greenhouse board request{'s' if errors != 1 else ''} failed or returned invalid data.")
    return _ProviderOutcome("greenhouse", "Greenhouse company boards", fetched_count, scored_jobs, notes=notes)
''',
    '''    if errors:
        notes.append(f"{errors} Greenhouse board request{'s' if errors != 1 else ''} failed or returned invalid data.")
    if budget_exhausted:
        notes.append("Stopped Greenhouse requests after the per-search provider budget was reached.")
    return _ProviderOutcome("greenhouse", "Greenhouse company boards", fetched_count, scored_jobs, notes=notes)
''',
    "greenhouse budget note",
)
search = replace_once(
    search,
    '''    errors = 0

    for site_name in site_names:
        try:
            response = client.get(
                f"{LEVER_BASE_URL}/{site_name}",
                params={"mode": "json", "limit": str(MAX_PROVIDER_RESULTS_PER_BOARD)},
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            raw_jobs = response.json()
        except (httpx.HTTPError, ValueError):
            errors += 1
            continue

        if not isinstance(raw_jobs, list):
            continue
''',
    '''    errors = 0
    budget_exhausted = False

    for site_name in site_names:
        try:
            raw_jobs = _lever_jobs_for_site(client, site_name)
        except ProviderRequestBudgetExceeded:
            budget_exhausted = True
            break
        except (httpx.HTTPError, ValueError):
            errors += 1
            continue
''',
    "lever budgeted fetch loop",
)
search = replace_once(
    search,
    '''    if errors:
        notes.append(f"{errors} Lever site request{'s' if errors != 1 else ''} failed or returned invalid data.")
    return _ProviderOutcome("lever", "Lever company boards", fetched_count, scored_jobs, notes=notes)
''',
    '''    if errors:
        notes.append(f"{errors} Lever site request{'s' if errors != 1 else ''} failed or returned invalid data.")
    if budget_exhausted:
        notes.append("Stopped Lever requests after the per-search provider budget was reached.")
    return _ProviderOutcome("lever", "Lever company boards", fetched_count, scored_jobs, notes=notes)
''',
    "lever budget note",
)
search = replace_once(
    search,
    '''    response = client.get(
        REMOTEOK_BASE_URL,
''',
    '''    _consume_provider_request()
    response = client.get(
        REMOTEOK_BASE_URL,
''',
    "remoteok budget consumption",
)
search = replace_once(
    search,
    '''    except (httpx.HTTPError, ValueError) as exc:
        return _ProviderOutcome(
''',
    '''    except (httpx.HTTPError, ValueError, ProviderRequestBudgetExceeded) as exc:
        return _ProviderOutcome(
''',
    "remoteok budget handling",
)
search = replace_once(
    search,
    '''    response = client.get(
        REMOTIVE_BASE_URL,
''',
    '''    _consume_provider_request()
    response = client.get(
        REMOTIVE_BASE_URL,
''',
    "remotive budget consumption",
)
search = replace_once(
    search,
    '''    failed_searches = 0

    for search_term in search_terms:
''',
    '''    failed_searches = 0
    budget_exhausted = False

    for search_term in search_terms:
''',
    "remotive budget state",
)
search = replace_once(
    search,
    '''        except (httpx.HTTPError, ValueError):
            failed_searches += 1

    notes = [
''',
    '''        except ProviderRequestBudgetExceeded:
            budget_exhausted = True
            break
        except (httpx.HTTPError, ValueError):
            failed_searches += 1

    notes = [
''',
    "remotive budget exception",
)
search = replace_once(
    search,
    '''    if failed_searches:
        notes.append(f"{failed_searches} Remotive search pass{'es' if failed_searches != 1 else ''} failed.")
    notes.append("Remotive is remote-first; it may not cover local or campus internship postings.")
''',
    '''    if failed_searches:
        notes.append(f"{failed_searches} Remotive search pass{'es' if failed_searches != 1 else ''} failed.")
    if budget_exhausted:
        notes.append("Stopped Remotive requests after the per-search provider budget was reached.")
    notes.append("Remotive is remote-first; it may not cover local or campus internship postings.")
''',
    "remotive budget note",
)
search = replace_once(
    search,
    '''    outcomes: list[_ProviderOutcome] = []

    with httpx.Client(timeout=8.0, follow_redirects=True) as client:
        outcomes.append(_search_greenhouse_boards(client, greenhouse_boards, cleaned_query, cleaned_location, resolved_level))
        outcomes.append(_search_lever_sites(client, lever_sites, cleaned_query, cleaned_location, resolved_level))

        if remoteok_enabled:
            outcomes.append(_search_remoteok(client, cleaned_query, cleaned_location, resolved_level))
        else:
            outcomes.append(_ProviderOutcome("remoteok", "Remote OK remote feed", 0, [], status="disabled", notes=["Disabled by configuration."]))

        if remotive_enabled:
            outcomes.append(_search_remotive(client, cleaned_query, cleaned_location, resolved_level))
        else:
            outcomes.append(_ProviderOutcome("remotive", "Remotive remote feed", 0, [], status="disabled", notes=["Disabled by configuration."]))
''',
    '''    outcomes: list[_ProviderOutcome] = []
    budget_token = _ACTIVE_PROVIDER_REQUEST_BUDGET.set(
        _ProviderRequestBudget(_provider_request_limit())
    )

    try:
        with _build_provider_client() as client:
            outcomes.append(_search_greenhouse_boards(client, greenhouse_boards, cleaned_query, cleaned_location, resolved_level))
            outcomes.append(_search_lever_sites(client, lever_sites, cleaned_query, cleaned_location, resolved_level))

            if remoteok_enabled:
                outcomes.append(_search_remoteok(client, cleaned_query, cleaned_location, resolved_level))
            else:
                outcomes.append(_ProviderOutcome("remoteok", "Remote OK remote feed", 0, [], status="disabled", notes=["Disabled by configuration."]))

            if remotive_enabled:
                outcomes.append(_search_remotive(client, cleaned_query, cleaned_location, resolved_level))
            else:
                outcomes.append(_ProviderOutcome("remotive", "Remotive remote feed", 0, [], status="disabled", notes=["Disabled by configuration."]))
    finally:
        _ACTIVE_PROVIDER_REQUEST_BUDGET.reset(budget_token)
''',
    "search request budget lifecycle",
)
search_path.write_text(search)

main = main_path.read_text()
main = replace_once(
    main,
    '''import csv
import io
import os
import secrets
import time
''',
    '''import csv
import io
import ipaddress
import os
import secrets
import time
''',
    "main imports",
)
main = replace_once(
    main,
    '''RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 30
''',
    '''RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 30
RATE_LIMIT_GLOBAL_MAX_REQUESTS = 300
RATE_LIMIT_MAX_TRACKED_CLIENTS = 5_000
''',
    "rate limit constants",
)
main = replace_once(
    main,
    '''_rate_limit_buckets: dict[str, list[float]] = {}
''',
    '''_rate_limit_buckets: dict[str, list[float]] = {}
_global_rate_limit_timestamps: list[float] = []
''',
    "rate limit state",
)
main = replace_once(
    main,
    '''def _get_rate_limit_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()

    if request.client and request.client.host:
        return request.client.host

    return "unknown-client"


def enforce_public_rate_limit(request: Request) -> None:
    """Small in-memory fixed-window rate limit for public analysis endpoints."""
    identifier = _get_rate_limit_identifier(request)
    now = time.monotonic()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS

    request_timestamps = _rate_limit_buckets.setdefault(identifier, [])
    request_timestamps[:] = [
        timestamp for timestamp in request_timestamps if timestamp >= window_start
    ]

    if len(request_timestamps) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait before trying again.",
        )

    request_timestamps.append(now)
''',
    '''def _validated_ip(value: str | None) -> str | None:
    if not value:
        return None
    candidate = value.strip()
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


def _get_rate_limit_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        forwarded_ip = _validated_ip(forwarded_for.split(",", maxsplit=1)[0])
        if forwarded_ip:
            return forwarded_ip

    if request.client and request.client.host:
        return _validated_ip(request.client.host) or request.client.host[:120]

    return "unknown-client"


def _prune_rate_limit_state(window_start: float) -> None:
    global _global_rate_limit_timestamps
    _global_rate_limit_timestamps = [
        timestamp
        for timestamp in _global_rate_limit_timestamps
        if timestamp >= window_start
    ]

    stale_identifiers = [
        identifier
        for identifier, timestamps in _rate_limit_buckets.items()
        if not timestamps or timestamps[-1] < window_start
    ]
    for identifier in stale_identifiers:
        _rate_limit_buckets.pop(identifier, None)

    if len(_rate_limit_buckets) > RATE_LIMIT_MAX_TRACKED_CLIENTS:
        oldest = sorted(
            _rate_limit_buckets,
            key=lambda identifier: _rate_limit_buckets[identifier][-1]
            if _rate_limit_buckets[identifier]
            else 0.0,
        )
        for identifier in oldest[: len(_rate_limit_buckets) - RATE_LIMIT_MAX_TRACKED_CLIENTS]:
            _rate_limit_buckets.pop(identifier, None)


def enforce_public_rate_limit(request: Request) -> None:
    """Bounded instance-level abuse protection for public endpoints.

    Railway or another edge proxy should still provide platform-level rate
    limiting for high-volume production traffic. This guard prevents one client
    or a burst across many clients from fan-out triggering unlimited providers.
    """

    identifier = _get_rate_limit_identifier(request)
    now = time.monotonic()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    _prune_rate_limit_state(window_start)

    if len(_global_rate_limit_timestamps) >= RATE_LIMIT_GLOBAL_MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail="Service-wide rate limit exceeded. Please wait before trying again.",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECONDS)},
        )

    request_timestamps = _rate_limit_buckets.setdefault(identifier, [])
    request_timestamps[:] = [
        timestamp for timestamp in request_timestamps if timestamp >= window_start
    ]

    if len(request_timestamps) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait before trying again.",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECONDS)},
        )

    request_timestamps.append(now)
    _global_rate_limit_timestamps.append(now)
''',
    "bounded rate limiter",
)
main_path.write_text(main)

saved_jobs = saved_jobs_path.read_text()
saved_jobs = replace_once(
    saved_jobs,
    '''from pydantic import BaseModel, ConfigDict, Field
''',
    '''from pydantic import BaseModel, ConfigDict, Field, field_validator
''',
    "saved jobs pydantic imports",
)
saved_jobs = replace_once(
    saved_jobs,
    '''from app.database import get_db
''',
    '''from app.database import get_db
from app.external_urls import require_external_https_url, sanitize_external_https_url
''',
    "saved jobs URL imports",
)
saved_jobs = replace_once(
    saved_jobs,
    '''    apply_url: str | None = Field(default=None, max_length=2048)


class SavedJob(SavedJobCreate):
''',
    '''    apply_url: str | None = Field(default=None, max_length=2048)

    @field_validator("apply_url")
    @classmethod
    def validate_apply_url(cls, value: str | None) -> str | None:
        return require_external_https_url(value)


class SavedJob(SavedJobCreate):
''',
    "saved job URL validator",
)
saved_jobs = replace_once(
    saved_jobs,
    '''def _to_saved_job_response(saved_job: SavedJobDB) -> SavedJob:
    return SavedJob.model_validate(saved_job)
''',
    '''def _to_saved_job_response(saved_job: SavedJobDB) -> SavedJob:
    return SavedJob(
        source=saved_job.source,
        source_job_id=saved_job.source_job_id,
        company=saved_job.company,
        title=saved_job.title,
        location=saved_job.location,
        description=saved_job.description,
        apply_url=sanitize_external_https_url(saved_job.apply_url),
        id=saved_job.id,
        extracted_skills=saved_job.extracted_skills,
        created_at=saved_job.created_at,
    )
''',
    "saved job response sanitization",
)
saved_jobs_path.write_text(saved_jobs)

saved_reports = saved_reports_path.read_text()
saved_reports = replace_once(
    saved_reports,
    '''from pydantic import BaseModel, ConfigDict, Field
''',
    '''from pydantic import BaseModel, ConfigDict, Field, field_validator
''',
    "saved reports pydantic imports",
)
saved_reports = replace_once(
    saved_reports,
    '''from app.database import get_db
''',
    '''from app.database import get_db
from app.external_urls import require_external_https_url, sanitize_external_https_url
''',
    "saved reports URL imports",
)
saved_reports = replace_once(
    saved_reports,
    '''    apply_url: str | None = Field(default=None, max_length=2048)
    summary: SavedReportSummary
''',
    '''    apply_url: str | None = Field(default=None, max_length=2048)
    summary: SavedReportSummary

    @field_validator("apply_url")
    @classmethod
    def validate_apply_url(cls, value: str | None) -> str | None:
        return require_external_https_url(value)
''',
    "saved report URL validator",
)
saved_reports = replace_once(
    saved_reports,
    '''        apply_url=saved_report.apply_url,
''',
    '''        apply_url=sanitize_external_https_url(saved_report.apply_url),
''',
    "saved report response sanitization",
)
saved_reports_path.write_text(saved_reports)

app = app_path.read_text()
app = replace_once(
    app,
    '''import {
  SaveSmartFitReportButton,
  SavedReportsPanel,
} from "./SavedReports";
''',
    '''import {
  SaveSmartFitReportButton,
  SavedReportsPanel,
} from "./SavedReports";
import { SafeExternalLink } from "./SafeExternalLink";
''',
    "App safe link import",
)
app = replace_once(
    app,
    '''          {job.location ?? "Location not listed"} · <a href={job.apply_url} target="_blank" rel="noreferrer">Open posting</a>
''',
    '''          {job.location ?? "Location not listed"} · <SafeExternalLink url={job.apply_url}>Open posting</SafeExternalLink>
''',
    "App safe posting link",
)
app_path.write_text(app)

frontend_saved_jobs = frontend_saved_jobs_path.read_text()
frontend_saved_jobs = replace_once(
    frontend_saved_jobs,
    '''import {
  createSavedJob,
  deleteSavedJob,
  getSavedJobs,
} from "./api";
''',
    '''import {
  createSavedJob,
  deleteSavedJob,
  getSavedJobs,
} from "./api";
import { SafeExternalLink } from "./SafeExternalLink";
''',
    "SavedJobs safe link import",
)
frontend_saved_jobs = replace_once(
    frontend_saved_jobs,
    '''                      <a
                        href={job.apply_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open posting
                      </a>
''',
    '''                      <SafeExternalLink url={job.apply_url}>
                        Open posting
                      </SafeExternalLink>
''',
    "SavedJobs safe posting link",
)
frontend_saved_jobs_path.write_text(frontend_saved_jobs)

frontend_saved_reports = frontend_saved_reports_path.read_text()
frontend_saved_reports = replace_once(
    frontend_saved_reports,
    '''import { createSavedReport, deleteSavedReport, getSavedReports } from "./api";
''',
    '''import { createSavedReport, deleteSavedReport, getSavedReports } from "./api";
import { SafeExternalLink } from "./SafeExternalLink";
''',
    "SavedReports safe link import",
)
frontend_saved_reports = replace_once(
    frontend_saved_reports,
    '''                      <a
                        href={report.apply_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open posting
                      </a>
''',
    '''                      <SafeExternalLink url={report.apply_url}>
                        Open posting
                      </SafeExternalLink>
''',
    "SavedReports safe posting link",
)
frontend_saved_reports_path.write_text(frontend_saved_reports)

registry_tests = registry_tests_path.read_text()
registry_tests = replace_once(
    registry_tests,
    '''    default_source_identifiers,
    find_source,
''',
    '''    configured_source_identifiers,
    default_source_identifiers,
    find_source,
    normalize_source_identifier,
''',
    "registry test imports",
)
registry_tests += '''


def test_registry_rejects_malformed_and_unregistered_identifiers() -> None:
    assert normalize_source_identifier("github") == "github"
    assert normalize_source_identifier("../internal") is None
    assert normalize_source_identifier("https://evil.example") is None
    assert normalize_source_identifier("name with spaces") is None
    assert find_source("../internal", "lever") is None


def test_environment_source_configuration_is_registry_allowlisted() -> None:
    assert configured_source_identifiers(
        "lever",
        " github,../internal,unknown-company,github, twitch ",
    ) == ("github", "twitch")
    assert configured_source_identifiers(
        "greenhouse",
        "https://evil.example,unknown-company",
    ) == EXPECTED_GREENHOUSE_BOARDS
'''
registry_tests_path.write_text(registry_tests)

security_tests_content = '''import pytest
from pydantic import ValidationError

from app.external_urls import sanitize_external_https_url
from app.job_search import (
    ProviderRequestBudgetExceeded,
    _ACTIVE_PROVIDER_REQUEST_BUDGET,
    _ATS_PROVIDER_CACHE,
    _ProviderRequestBudget,
    _build_provider_client,
    _greenhouse_jobs_for_board,
    _normalize_greenhouse_job,
)
from app.saved_jobs import SavedJobCreate


class _FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, list[dict[str, object]]]:
        return {
            "jobs": [
                {
                    "id": 1,
                    "title": "Software Engineer",
                    "absolute_url": "https://boards.greenhouse.io/example/jobs/1",
                    "location": {"name": "Remote"},
                    "content": "Python",
                }
            ]
        }


class _FakeClient:
    def __init__(self) -> None:
        self.calls = 0

    def get(self, *args: object, **kwargs: object) -> _FakeResponse:
        self.calls += 1
        return _FakeResponse()


def test_external_links_must_be_public_https_urls() -> None:
    assert sanitize_external_https_url("https://example.com/jobs/1") == "https://example.com/jobs/1"
    assert sanitize_external_https_url("http://example.com/jobs/1") is None
    assert sanitize_external_https_url("javascript:alert(1)") is None
    assert sanitize_external_https_url("https://user:password@example.com/jobs/1") is None
    assert sanitize_external_https_url("https://localhost/jobs/1") is None
    assert sanitize_external_https_url("https://127.0.0.1/jobs/1") is None
    assert sanitize_external_https_url("https://10.0.0.1/jobs/1") is None
    assert sanitize_external_https_url("https://example.com:8443/jobs/1") is None


def test_saved_job_payload_rejects_unsafe_application_url() -> None:
    with pytest.raises(ValidationError):
        SavedJobCreate(
            company="Example",
            title="Engineer",
            description="Python",
            apply_url="javascript:alert(1)",
        )


def test_provider_payload_with_unsafe_url_is_dropped() -> None:
    assert _normalize_greenhouse_job(
        "example",
        {
            "id": 1,
            "title": "Engineer",
            "absolute_url": "http://example.com/job/1",
            "location": {"name": "Remote"},
            "content": "Python",
        },
    ) is None


def test_ats_payload_cache_avoids_repeated_network_fanout() -> None:
    _ATS_PROVIDER_CACHE.clear()
    client = _FakeClient()
    token = _ACTIVE_PROVIDER_REQUEST_BUDGET.set(_ProviderRequestBudget(remaining=1))
    try:
        first = _greenhouse_jobs_for_board(client, "example")
        second = _greenhouse_jobs_for_board(client, "example")
    finally:
        _ACTIVE_PROVIDER_REQUEST_BUDGET.reset(token)

    assert first == second
    assert client.calls == 1


def test_provider_request_budget_fails_closed() -> None:
    _ATS_PROVIDER_CACHE.clear()
    client = _FakeClient()
    token = _ACTIVE_PROVIDER_REQUEST_BUDGET.set(_ProviderRequestBudget(remaining=0))
    try:
        with pytest.raises(ProviderRequestBudgetExceeded):
            _greenhouse_jobs_for_board(client, "uncached-example")
    finally:
        _ACTIVE_PROVIDER_REQUEST_BUDGET.reset(token)

    assert client.calls == 0


def test_provider_client_does_not_follow_redirects() -> None:
    client = _build_provider_client()
    try:
        assert client.follow_redirects is False
    finally:
        client.close()
'''
(root / "backend/tests/test_external_security.py").write_text(security_tests_content)

docs = docs_path.read_text()
docs += '''

## Security hardening

The registry now acts as an outbound allowlist rather than a display-only catalog.
Environment configuration can select only enabled, registered Greenhouse and Lever identifiers; malformed or unknown identifiers fail closed to the safe defaults.

Additional controls in this phase:

- provider identifiers use a strict lowercase token format
- application links must be public HTTPS URLs without embedded credentials
- unsafe links are rejected by the backend and independently hidden by the frontend
- provider HTTP clients do not automatically follow redirects
- ATS responses are cached briefly to avoid repeated network fan-out
- every search has a bounded outbound provider-request budget
- the public endpoint has both per-client and service-wide in-memory rate limits with bounded tracking state

These controls protect the portfolio-scale deployment. Large multi-instance deployments should add an edge or shared-store rate limiter because in-memory limits are instance-local.
'''
docs_path.write_text(docs)
