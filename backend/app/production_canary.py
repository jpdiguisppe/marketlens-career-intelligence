from __future__ import annotations

import json
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from typing import Any, Callable
from urllib.parse import urljoin

import httpx

DEFAULT_FRONTEND_URL = "https://marketlens-career-intelligence-production-8a34.up.railway.app"
DEFAULT_BACKEND_URL = "https://marketlens-career-intelligence-production.up.railway.app"

SYNTHETIC_RESUME = """MarketLens Production Canary
Skills: Python, SQL, React, REST APIs, Docker, Git, automated testing.
Projects: Built a FastAPI and React application with SQL persistence, Docker packaging, and CI tests.
Experience: Implemented API integrations, analyzed failures, documented evidence, and worked in Agile sprints.
Education: Bachelor-level computer science coursework.
"""

SYNTHETIC_JOB = """Entry-Level Software Engineer
Responsibilities: Build and test web APIs, collaborate in Agile sprints, and document software behavior.
Required qualifications: Python, SQL, REST APIs, Git, and automated testing.
Preferred qualifications: React, Docker, cloud deployment, and a bachelor's degree or equivalent experience.
"""

_CONFIG_PATTERN = re.compile(
    r"apiBaseUrl:\s*[\"'](?P<api>[^\"']+)[\"']\s*,\s*"
    r"deploymentRevision:\s*[\"'](?P<revision>[^\"']+)[\"']",
    re.DOTALL,
)
_SCRIPT_PATTERN = re.compile(r"<script[^>]+src=[\"'](?P<src>[^\"']+)[\"']", re.IGNORECASE)
_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class CanaryCheck:
    name: str
    passed: bool
    latency_ms: float
    details: dict[str, Any]
    error_code: str | None = None


class ProductionCanaryError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def normalize_base_url(value: str) -> str:
    return value.strip().rstrip("/")


def normalize_revision(value: str | None) -> str | None:
    candidate = (value or "").strip().lower()
    return candidate if _SHA_PATTERN.fullmatch(candidate) else None


def parse_frontend_config(text: str) -> dict[str, str]:
    match = _CONFIG_PATTERN.search(text)
    if match is None:
        raise ProductionCanaryError("frontend_config_invalid", "Frontend config.js was not parseable.")
    return {
        "api_base_url": normalize_base_url(match.group("api")),
        "revision": match.group("revision").strip().lower(),
    }


def _authorization_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _safe_json(response: httpx.Response) -> dict[str, Any]:
    try:
        value = response.json()
    except ValueError as exc:
        raise ProductionCanaryError(
            "invalid_json_response",
            f"{response.request.method} {response.request.url.path} returned invalid JSON.",
        ) from exc
    if not isinstance(value, dict):
        raise ProductionCanaryError(
            "unexpected_json_shape",
            f"{response.request.method} {response.request.url.path} returned a non-object JSON response.",
        )
    return value


def _require_status(response: httpx.Response, expected: set[int]) -> None:
    if response.status_code not in expected:
        raise ProductionCanaryError(
            "unexpected_http_status",
            f"{response.request.method} {response.request.url.path} returned HTTP {response.status_code}.",
        )


class ProductionCareerPlanCanary:
    def __init__(
        self,
        *,
        frontend_url: str = DEFAULT_FRONTEND_URL,
        backend_url: str = DEFAULT_BACKEND_URL,
        expected_revision: str | None = None,
        timeout_seconds: float = 90.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.frontend_url = normalize_base_url(frontend_url)
        self.backend_url = normalize_base_url(backend_url)
        self.expected_revision = normalize_revision(expected_revision)
        self._client = client or httpx.Client(timeout=timeout_seconds, follow_redirects=True)
        self._owns_client = client is None
        self.checks: list[CanaryCheck] = []
        self.model_status: dict[str, Any] | None = None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _record(self, name: str, operation: Callable[[], dict[str, Any]]) -> None:
        started = time.perf_counter()
        try:
            details = operation()
        except ProductionCanaryError as exc:
            self.checks.append(
                CanaryCheck(
                    name=name,
                    passed=False,
                    latency_ms=round((time.perf_counter() - started) * 1_000, 3),
                    details={},
                    error_code=exc.code,
                )
            )
        except Exception:
            self.checks.append(
                CanaryCheck(
                    name=name,
                    passed=False,
                    latency_ms=round((time.perf_counter() - started) * 1_000, 3),
                    details={},
                    error_code="unexpected_canary_error",
                )
            )
        else:
            self.checks.append(
                CanaryCheck(
                    name=name,
                    passed=True,
                    latency_ms=round((time.perf_counter() - started) * 1_000, 3),
                    details=details,
                )
            )

    def _get(self, base_url: str, path: str, **kwargs: Any) -> httpx.Response:
        return self._client.get(f"{base_url}{path}", **kwargs)

    def _post(self, path: str, **kwargs: Any) -> httpx.Response:
        return self._client.post(f"{self.backend_url}{path}", **kwargs)

    def _delete(self, path: str, **kwargs: Any) -> httpx.Response:
        return self._client.delete(f"{self.backend_url}{path}", **kwargs)

    def wait_for_exact_revision(self, *, wait_seconds: float = 0.0, interval_seconds: float = 10.0) -> None:
        if self.expected_revision is None:
            return
        deadline = time.monotonic() + max(wait_seconds, 0.0)
        last_backend = None
        last_frontend = None
        while True:
            try:
                backend_response = self._get(self.backend_url, "/deployment/status")
                if backend_response.status_code == 200:
                    last_backend = str(_safe_json(backend_response).get("revision") or "").lower()
                frontend_response = self._get(self.frontend_url, "/config.js")
                if frontend_response.status_code == 200:
                    last_frontend = parse_frontend_config(frontend_response.text)["revision"]
            except Exception:
                pass
            if last_backend == self.expected_revision and last_frontend == self.expected_revision:
                return
            if time.monotonic() >= deadline:
                raise ProductionCanaryError(
                    "deployment_revision_timeout",
                    "Production services did not reach the expected revision before the canary deadline.",
                )
            time.sleep(max(interval_seconds, 0.1))

    def run_public(self, *, run_model: bool = False) -> None:
        self._record("backend_health", self._check_backend_health)
        self._record("backend_revision", self._check_backend_revision)
        self._record("frontend_revision", self._check_frontend_revision)
        self._record("frontend_career_plan_bundle", self._check_frontend_bundle)
        self._record("model_status", self._check_model_status)
        self._record("private_route_auth_boundary", self._check_auth_boundary)
        self._record("live_job_search", self._check_live_search)
        self._record("deterministic_smart_fit", self._check_deterministic_smart_fit)
        if run_model and bool((self.model_status or {}).get("enabled")):
            self._record("model_assisted_smart_fit", self._check_model_assisted_smart_fit)

    def _check_backend_health(self) -> dict[str, Any]:
        response = self._get(self.backend_url, "/health")
        _require_status(response, {200})
        payload = _safe_json(response)
        if payload.get("status") != "ok":
            raise ProductionCanaryError("backend_health_failed", "Backend health status was not ok.")
        return {"status": "ok"}

    def _check_backend_revision(self) -> dict[str, Any]:
        response = self._get(self.backend_url, "/deployment/status")
        _require_status(response, {200})
        payload = _safe_json(response)
        revision = str(payload.get("revision") or "").lower()
        if self.expected_revision and revision != self.expected_revision:
            raise ProductionCanaryError("backend_revision_mismatch", "Backend revision did not match expected revision.")
        if revision != "unknown" and normalize_revision(revision) is None:
            raise ProductionCanaryError("backend_revision_invalid", "Backend revision was not a safe SHA.")
        return {
            "revision": revision,
            "branch": payload.get("branch"),
            "environment": payload.get("environment"),
        }

    def _check_frontend_revision(self) -> dict[str, Any]:
        response = self._get(self.frontend_url, "/config.js")
        _require_status(response, {200})
        config = parse_frontend_config(response.text)
        if config["api_base_url"] != self.backend_url:
            raise ProductionCanaryError("frontend_api_base_mismatch", "Frontend runtime API URL did not match production backend.")
        if self.expected_revision and config["revision"] != self.expected_revision:
            raise ProductionCanaryError("frontend_revision_mismatch", "Frontend revision did not match expected revision.")
        return config

    def _check_frontend_bundle(self) -> dict[str, Any]:
        response = self._get(self.frontend_url, "/")
        _require_status(response, {200})
        if 'id="root"' not in response.text and "id='root'" not in response.text:
            raise ProductionCanaryError("frontend_root_missing", "Frontend root element was missing.")
        sources = [match.group("src") for match in _SCRIPT_PATTERN.finditer(response.text)]
        if not sources:
            raise ProductionCanaryError("frontend_bundle_missing", "Frontend JavaScript bundle was not referenced.")
        bundle_text = ""
        for source in sources[:5]:
            asset_url = urljoin(f"{self.frontend_url}/", source)
            asset_response = self._client.get(asset_url)
            _require_status(asset_response, {200})
            bundle_text += asset_response.text
        required_markers = ("Career Plans", "Candidate Selection Audit", "/career-plans")
        missing = [marker for marker in required_markers if marker not in bundle_text]
        if missing:
            raise ProductionCanaryError("career_plan_bundle_stale", "Career Plan workspace markers were missing from the frontend bundle.")
        return {"script_count": len(sources), "markers": list(required_markers)}

    def _check_model_status(self) -> dict[str, Any]:
        response = self._get(self.backend_url, "/analysis/model-status")
        _require_status(response, {200})
        payload = _safe_json(response)
        if not isinstance(payload.get("enabled"), bool):
            raise ProductionCanaryError("model_status_invalid", "Model status did not include a boolean enabled field.")
        self.model_status = payload
        return {"enabled": payload["enabled"], "status": payload.get("status")}

    def _check_auth_boundary(self) -> dict[str, Any]:
        response = self._get(self.backend_url, "/career-plans")
        _require_status(response, {401, 403})
        return {"status_code": response.status_code}

    def _check_live_search(self) -> dict[str, Any]:
        response = self._get(
            self.backend_url,
            "/jobs/search",
            params={
                "query": "Software Engineer",
                "location": "Philadelphia",
                "level": "entry",
                "limit": "5",
            },
        )
        _require_status(response, {200})
        payload = _safe_json(response)
        results = payload.get("results")
        coverage = payload.get("source_coverage")
        if not isinstance(results, list) or len(results) > 5:
            raise ProductionCanaryError("search_result_bound_failed", "Live search results were missing or outside the five-job bound.")
        if not isinstance(coverage, list) or not coverage:
            raise ProductionCanaryError("search_coverage_missing", "Live search did not report provider coverage.")
        return {
            "result_count": len(results),
            "provider_count": len(coverage),
            "providers_searched": payload.get("providers_searched", []),
            "warning_count": len(payload.get("warnings") or []),
        }

    def _smart_fit_payload(self, use_model_assisted: bool) -> dict[str, Any]:
        return {
            "resume_text": SYNTHETIC_RESUME,
            "job_description": SYNTHETIC_JOB,
            "use_model_assisted": use_model_assisted,
        }

    def _validate_smart_fit(self, payload: dict[str, Any]) -> dict[str, Any]:
        fit_summary = payload.get("fit_summary")
        if not isinstance(fit_summary, dict):
            raise ProductionCanaryError("smart_fit_missing_summary", "Smart Fit did not return a fit summary.")
        score = fit_summary.get("score")
        if not isinstance(score, int) or not 0 <= score <= 100:
            raise ProductionCanaryError("smart_fit_score_invalid", "Smart Fit returned an invalid score.")
        telemetry = payload.get("provider_telemetry")
        return {
            "score": score,
            "analysis_engine": payload.get("analysis_engine"),
            "model_assisted_status": payload.get("model_assisted_status"),
            "coaching_status": payload.get("coaching_status"),
            "provider_telemetry": {
                "total_provider_latency_ms": telemetry.get("total_provider_latency_ms"),
                "total_tokens": telemetry.get("total_tokens"),
                "total_estimated_cost_usd": telemetry.get("total_estimated_cost_usd"),
                "cost_estimate_status": telemetry.get("cost_estimate_status"),
            }
            if isinstance(telemetry, dict)
            else None,
        }

    def _check_deterministic_smart_fit(self) -> dict[str, Any]:
        response = self._post("/analysis/smart", json=self._smart_fit_payload(False))
        _require_status(response, {200})
        payload = _safe_json(response)
        details = self._validate_smart_fit(payload)
        if details["analysis_engine"] != "deterministic":
            raise ProductionCanaryError("deterministic_engine_changed", "Deterministic Smart Fit did not remain deterministic.")
        return details

    def _check_model_assisted_smart_fit(self) -> dict[str, Any]:
        response = self._post("/analysis/smart", json=self._smart_fit_payload(True))
        _require_status(response, {200})
        return self._validate_smart_fit(_safe_json(response))

    def run_authenticated(
        self,
        *,
        token: str,
        second_token: str | None = None,
        run_model: bool = False,
        test_cancellation: bool = True,
    ) -> None:
        self._record(
            "authenticated_deterministic_lifecycle",
            lambda: self._authenticated_lifecycle(token, second_token=second_token, model_assisted=False),
        )
        if run_model and bool((self.model_status or {}).get("enabled")):
            self._record(
                "authenticated_model_lifecycle",
                lambda: self._authenticated_lifecycle(token, second_token=second_token, model_assisted=True),
            )
        if test_cancellation:
            self._record("authenticated_cancellation_retry", lambda: self._cancellation_retry(token))

    def _create_plan(self, token: str, *, model_assisted: bool) -> dict[str, Any]:
        response = self._post(
            "/career-plans",
            headers=_authorization_headers(token),
            json={
                "goal": {
                    "target_occupation": "Software Engineer",
                    "experience_level": "entry",
                    "industry": "technology",
                    "location": "Philadelphia",
                    "work_mode": "any",
                    "portfolio_strategy": "balanced",
                    "max_jobs_to_analyze": 2,
                    "model_assisted_planning": model_assisted,
                },
                "idempotency_key": f"production-canary-{uuid.uuid4()}",
            },
        )
        _require_status(response, {201})
        return _safe_json(response)

    def _execute_plan(self, token: str, run: dict[str, Any]) -> dict[str, Any]:
        response = self._post(
            f"/career-plans/{run['id']}/execute",
            headers=_authorization_headers(token),
            json={"resume_text": SYNTHETIC_RESUME, "expected_run_version": run["run_version"]},
        )
        _require_status(response, {200})
        return _safe_json(response)

    def _authenticated_lifecycle(
        self,
        token: str,
        *,
        second_token: str | None,
        model_assisted: bool,
    ) -> dict[str, Any]:
        run = self._create_plan(token, model_assisted=model_assisted)
        run_id = int(run["id"])
        try:
            executed = self._execute_plan(token, run)
            if executed.get("status") != "awaiting_approval":
                raise ProductionCanaryError("career_plan_not_ready", "Career Plan did not reach awaiting_approval.")
            steps = executed.get("steps")
            if not isinstance(steps, list) or len(steps) != 7:
                raise ProductionCanaryError("career_plan_step_count", "Career Plan did not persist all seven workflow steps.")
            proposal = executed.get("proposal")
            if not isinstance(proposal, dict):
                raise ProductionCanaryError("career_plan_proposal_missing", "Career Plan proposal was missing.")
            actions = proposal.get("actions")
            if not isinstance(actions, list) or not actions or len(actions) > 20:
                raise ProductionCanaryError("career_plan_action_bound", "Career Plan actions were missing or outside bounds.")
            if any(action.get("status") != "proposed" for action in actions if isinstance(action, dict)):
                raise ProductionCanaryError("career_plan_action_state", "A production action bypassed proposed state.")

            explain = self._post(
                f"/career-plans/{run_id}/explain",
                headers=_authorization_headers(token),
                json={"explanation_type": "model_assistance"},
            )
            _require_status(explain, {200})

            edited = dict(actions[0])
            edited["title"] = f"Production canary review: {edited['title']}"[:255]
            edited["rationale"] = f"Production canary confirmed this remains a user-approved proposal. {edited['rationale']}"[:2000]
            edited["status"] = "edited"
            decision = self._post(
                f"/career-plans/{run_id}/decision",
                headers=_authorization_headers(token),
                json={"decision": "approved", "edited_actions": [edited]},
            )
            _require_status(decision, {200})
            decided = _safe_json(decision)
            if decided.get("status") != "approved":
                raise ProductionCanaryError("career_plan_approval_failed", "Career Plan approval did not persist.")

            reopened = self._get(
                self.backend_url,
                f"/career-plans/{run_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            _require_status(reopened, {200})
            if _safe_json(reopened).get("status") != "approved":
                raise ProductionCanaryError("career_plan_reopen_failed", "Approved Career Plan did not reopen correctly.")

            ownership_status = "not_configured"
            if second_token:
                cross_user = self._get(
                    self.backend_url,
                    f"/career-plans/{run_id}",
                    headers={"Authorization": f"Bearer {second_token}"},
                )
                _require_status(cross_user, {404})
                ownership_status = "isolated"

            assistance = proposal.get("model_assisted")
            telemetry = assistance.get("telemetry") if isinstance(assistance, dict) else None
            return {
                "run_id": run_id,
                "step_count": len(steps),
                "portfolio_count": len(proposal.get("portfolio") or []),
                "action_count": len(actions),
                "fallback_status": executed.get("fallback_status"),
                "model_status": assistance.get("status") if isinstance(assistance, dict) else None,
                "model_latency_ms": telemetry.get("latency_ms") if isinstance(telemetry, dict) else None,
                "model_total_tokens": (telemetry.get("usage") or {}).get("total_tokens")
                if isinstance(telemetry, dict)
                else None,
                "model_estimated_cost_usd": telemetry.get("estimated_cost_usd")
                if isinstance(telemetry, dict)
                else None,
                "ownership_status": ownership_status,
            }
        finally:
            deleted = self._delete(
                f"/career-plans/{run_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            if deleted.status_code not in {200, 404}:
                raise ProductionCanaryError("career_plan_cleanup_failed", "Production canary plan could not be deleted.")

    def _cancellation_retry(self, token: str) -> dict[str, Any]:
        run = self._create_plan(token, model_assisted=False)
        run_id = int(run["id"])
        headers = _authorization_headers(token)
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._execute_plan, token, run)
                cancel_response: httpx.Response | None = None
                for _ in range(60):
                    status_response = self._get(
                        self.backend_url,
                        f"/career-plans/{run_id}",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    _require_status(status_response, {200})
                    status_payload = _safe_json(status_response)
                    if status_payload.get("status") == "running":
                        cancel_response = self._post(
                            f"/career-plans/{run_id}/cancel",
                            headers=headers,
                            json={},
                        )
                        break
                    if future.done():
                        break
                    time.sleep(0.1)
                first_result = future.result(timeout=120)

            if cancel_response is None or cancel_response.status_code != 200:
                raise ProductionCanaryError(
                    "cancellation_window_not_observed",
                    "Production execution completed before the cancellation boundary could be observed.",
                )
            if first_result.get("status") != "cancelled":
                raise ProductionCanaryError("cancellation_not_applied", "Cancellation request did not end the run safely.")

            retried = self._execute_plan(token, first_result)
            if retried.get("status") != "awaiting_approval":
                raise ProductionCanaryError("cancelled_retry_failed", "Cancelled Career Plan did not complete on retry.")
            actions = (retried.get("proposal") or {}).get("actions") or []
            action_ids = [action.get("id") for action in actions if isinstance(action, dict)]
            if len(action_ids) != len(set(action_ids)):
                raise ProductionCanaryError("retry_duplicate_actions", "Retry produced duplicate action IDs.")
            return {
                "attempt_count": retried.get("attempt_count"),
                "action_count": len(actions),
                "unique_action_count": len(set(action_ids)),
            }
        finally:
            self._delete(
                f"/career-plans/{run_id}",
                headers={"Authorization": f"Bearer {token}"},
            )

    def report(self, *, mode: str, authenticated_configured: bool) -> dict[str, Any]:
        failed = [check for check in self.checks if not check.passed]
        total_latency = round(sum(check.latency_ms for check in self.checks), 3)
        return {
            "version": "8.1f.1",
            "mode": mode,
            "passed": not failed and (mode != "full" or authenticated_configured),
            "authenticated_configured": authenticated_configured,
            "frontend_url": self.frontend_url,
            "backend_url": self.backend_url,
            "expected_revision": self.expected_revision,
            "check_count": len(self.checks),
            "failed_check_count": len(failed),
            "total_measured_latency_ms": total_latency,
            "checks": [asdict(check) for check in self.checks],
            "boundaries": [
                "Canary documents are synthetic and every created Career Plan is deleted.",
                "Bearer tokens and provider credentials are never included in the report.",
                "A full sign-off cannot pass without an authenticated canary identity.",
                "Production actions must remain proposals until an explicit user decision.",
            ],
        }


def format_production_canary_report(report: dict[str, Any]) -> str:
    status = "PASS" if report["passed"] else "FAIL"
    lines = [
        f"MarketLens Production Career Plan Canary: {status}",
        f"Version: {report['version']}",
        f"Mode: {report['mode']}",
        f"Expected revision: {report['expected_revision'] or 'not enforced'}",
        f"Authenticated canary configured: {report['authenticated_configured']}",
        f"Checks: {report['check_count']}",
        f"Failed checks: {report['failed_check_count']}",
        f"Measured check latency: {report['total_measured_latency_ms']} ms",
        "",
        "Check results:",
    ]
    for check in report["checks"]:
        marker = "PASS" if check["passed"] else "FAIL"
        suffix = f" error={check['error_code']}" if check["error_code"] else ""
        lines.append(f"- {marker} {check['name']}: {check['latency_ms']} ms{suffix}")
        if check["details"]:
            lines.append(f"  {json.dumps(check['details'], sort_keys=True)}")
    lines.extend(["", "Boundaries:"])
    lines.extend(f"- {item}" for item in report["boundaries"])
    return "\n".join(lines)


__all__ = [
    "DEFAULT_BACKEND_URL",
    "DEFAULT_FRONTEND_URL",
    "ProductionCareerPlanCanary",
    "ProductionCanaryError",
    "format_production_canary_report",
    "normalize_revision",
    "parse_frontend_config",
]
