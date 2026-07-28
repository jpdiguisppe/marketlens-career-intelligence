from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

BACKEND_URL = os.getenv(
    "MARKETLENS_BACKEND_URL",
    "https://marketlens-career-intelligence-production.up.railway.app",
).rstrip("/")
FRONTEND_URL = os.getenv(
    "MARKETLENS_FRONTEND_URL",
    "https://marketlens-career-intelligence-production-8a34.up.railway.app",
).rstrip("/")
EXPECTED_REVISION = os.getenv("MARKETLENS_EXPECTED_REVISION", "").strip().lower()
TIMEOUT_SECONDS = 150
DEPLOYMENT_ATTEMPTS = 24
DEPLOYMENT_RETRY_SECONDS = 20
MAX_RESPONSE_BYTES = 2_000_000
CANARY_VERSION = "8e.5.3"
GIT_COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")

CANARY_RESUME = (
    "Software engineering student with project experience building Python FastAPI "
    "services, React and TypeScript interfaces, SQL-backed applications, REST APIs, "
    "Docker containers, Git workflows, and automated tests."
)
CANARY_JOB = """Associate Software Engineer
Build and maintain backend services and internal tools.
Required qualifications: Python, REST APIs, SQL, Git, and automated testing.
Preferred qualifications: Docker, React, TypeScript, and cloud deployment experience."""
REJECTED_MARKER = "marketlens-canary-rejected-value-8e5"

SMART_FIT_KEYS = {
    "fit_summary",
    "document_quality",
    "hard_requirements",
    "requirement_assessments",
    "category_coverage",
    "coaching_actions",
    "report_summary",
    "gap_groups",
    "analysis_engine",
    "model_assisted_status",
    "provenance_version",
    "grounding_warnings",
    "provider_telemetry",
}
FRONTEND_BUNDLE_MARKERS = (
    "Operational details",
    "safely fell back to deterministic analysis",
    "AI assisted",
    "Deterministic",
    "No provider model",
    "Unavailable",
)


class CanaryFailure(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CanaryFailure(message)


def request_text(
    url: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
) -> tuple[int, str]:
    headers = {
        "User-Agent": "MarketLens-Milestone-8E-Canary/1.0",
        "Accept": "application/json,text/html,*/*",
        "Cache-Control": "no-cache",
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        response = urlopen(request, timeout=TIMEOUT_SECONDS)
    except HTTPError as exc:
        response = exc
    except (URLError, TimeoutError) as exc:
        raise CanaryFailure(f"Request failed for {url}: {type(exc).__name__}") from exc

    with response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        require(len(raw) <= MAX_RESPONSE_BYTES, "Response exceeded the canary size limit")
        return response.status, raw.decode("utf-8", errors="replace")


def object_json(
    status: int,
    text: str,
    *,
    context: str,
    expected: int = 200,
) -> dict[str, Any]:
    require(status == expected, f"{context} returned HTTP {status}; expected {expected}")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CanaryFailure(f"{context} did not return valid JSON") from exc
    require(isinstance(payload, dict), f"{context} did not return a JSON object")
    return payload


def stable_hash(value: Any) -> str:
    packed = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(packed.encode("utf-8")).hexdigest()


def normalized_expected_revision() -> str | None:
    if not EXPECTED_REVISION:
        return None
    require(
        GIT_COMMIT_SHA_PATTERN.fullmatch(EXPECTED_REVISION) is not None,
        "Expected deployment revision is not a full Git commit SHA",
    )
    return EXPECTED_REVISION


def frontend_source_contract(root: Path) -> dict[str, Any]:
    app_source = (root / "frontend/src/App.tsx").read_text(encoding="utf-8")
    telemetry_source = (root / "frontend/src/ProviderTelemetryPanel.tsx").read_text(encoding="utf-8")
    entrypoint_source = (root / "frontend/docker-entrypoint.sh").read_text(encoding="utf-8")
    deployment_source = (root / "backend/app/saved_jobs.py").read_text(encoding="utf-8")
    app_markers = (
        'analysis.analysis_engine === "model_assisted"',
        'analysis.model_assisted_status.startsWith("fallback")',
        "safely fell back to deterministic analysis",
        '"AI assisted"',
        '"Deterministic"',
    )
    telemetry_markers = (
        'return "Unavailable"',
        "<details>",
        "<summary>Operational details</summary>",
        "if (!telemetry)",
        "telemetry.extraction.prompt_version",
        "telemetry.coaching.schema_version",
        "telemetry.pricing_catalog_version",
    )
    deployment_markers = (
        'deploymentRevision: "${DEPLOYMENT_REVISION}"',
        'os.getenv("RAILWAY_GIT_COMMIT_SHA"',
        '@router.get("/deployment-status")',
    )
    missing = [marker for marker in app_markers if marker not in app_source]
    missing += [marker for marker in telemetry_markers if marker not in telemetry_source]
    missing += [marker for marker in deployment_markers if marker not in entrypoint_source + deployment_source]
    require(not missing, "Frontend/deployment source contract is missing markers: " + ", ".join(missing))
    details = re.search(r"<details(?P<attrs>[^>]*)>", telemetry_source)
    require(details is not None, "Operational details element is missing")
    require("open" not in details.group("attrs"), "Operational details must be collapsed by default")
    return {
        "status": "passed",
        "marker_count": len(app_markers) + len(telemetry_markers) + len(deployment_markers),
        "operational_details_collapsed_by_default": True,
        "telemetry_hidden_when_absent": True,
        "unknown_cost_label": "Unavailable",
        "deployment_revision_contract": True,
    }


def frontend_bundle_contract(expected_revision: str | None) -> dict[str, Any]:
    cache_buster = int(time.time())
    status, html = request_text(f"{FRONTEND_URL}/?milestone8e_canary={cache_buster}")
    require(status == 200, f"Frontend root returned HTTP {status}")
    require('id="root"' in html or "id='root'" in html, "Frontend React root is missing")

    config_status, config = request_text(
        f"{FRONTEND_URL}/config.js?milestone8e_canary={cache_buster}"
    )
    require(config_status == 200, f"Frontend runtime config returned HTTP {config_status}")
    api_match = re.search(r"apiBaseUrl\s*:\s*[\"']([^\"']+)[\"']", config)
    require(api_match is not None, "Frontend runtime config does not expose apiBaseUrl")
    configured_api = api_match.group(1).rstrip("/")
    require(configured_api == BACKEND_URL, "Frontend runtime API URL does not match production")
    require(configured_api.startswith("https://"), "Frontend runtime API URL is not HTTPS")

    revision_match = re.search(
        r"deploymentRevision\s*:\s*[\"']([^\"']+)[\"']",
        config,
    )
    observed_revision = revision_match.group(1).lower() if revision_match else None
    if expected_revision is not None:
        require(
            observed_revision == expected_revision,
            "Frontend deployment revision does not match the triggering commit",
        )

    sources = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
    require(sources, "Frontend HTML did not expose a JavaScript bundle")
    assets: list[str] = []
    bundles: list[str] = []
    for source in sources:
        asset_url = urljoin(f"{FRONTEND_URL}/", source)
        asset_status, asset_text = request_text(asset_url)
        if asset_status == 200:
            assets.append(asset_url)
            bundles.append(asset_text)
    combined = "\n".join(bundles)
    missing = [marker for marker in FRONTEND_BUNDLE_MARKERS if marker not in combined]
    require(not missing, "Deployed frontend bundle is missing markers: " + ", ".join(missing))
    return {
        "status": status,
        "runtime_api_url": configured_api,
        "deployment_revision": observed_revision,
        "script_asset_count": len(assets),
        "marker_count": len(FRONTEND_BUNDLE_MARKERS),
    }


def backend_deployment_contract(expected_revision: str | None) -> dict[str, Any]:
    status, text = request_text(f"{BACKEND_URL}/health")
    health = object_json(status, text, context="Backend health")
    require(health == {"status": "ok"}, "Unexpected backend health payload")

    observed_revision: str | None = None
    if expected_revision is not None:
        revision_status, revision_text = request_text(
            f"{BACKEND_URL}/saved-jobs/deployment-status"
        )
        deployment = object_json(
            revision_status,
            revision_text,
            context="Backend deployment status",
        )
        require(deployment.get("status") == "ok", "Unexpected backend deployment status")
        observed_revision = deployment.get("revision")
        require(
            observed_revision == expected_revision,
            "Backend deployment revision does not match the triggering commit",
        )

    return {
        "health": health,
        "deployment_revision": observed_revision,
    }


def wait_for_deployment(expected_revision: str | None) -> dict[str, Any]:
    failures: list[str] = []
    for attempt in range(1, DEPLOYMENT_ATTEMPTS + 1):
        try:
            backend = backend_deployment_contract(expected_revision)
            frontend = frontend_bundle_contract(expected_revision)
            return {
                "attempt": attempt,
                "expected_revision": expected_revision,
                "backend": backend,
                "frontend": frontend,
            }
        except CanaryFailure as exc:
            failures.append(f"attempt {attempt}: {exc}")
            if attempt < DEPLOYMENT_ATTEMPTS:
                time.sleep(DEPLOYMENT_RETRY_SECONDS)
    raise CanaryFailure(
        "Production did not reach the expected deployment revision: "
        + " | ".join(failures[-5:])
    )


def validate_stage(stage: Any, *, requested: bool) -> dict[str, Any]:
    require(isinstance(stage, dict), "Provider stage telemetry is not an object")
    keys = {
        "stage",
        "requested",
        "outcome",
        "status_code",
        "model",
        "prompt_version",
        "schema_version",
        "latency_ms",
        "usage",
        "estimated_cost_usd",
        "cost_estimate_status",
    }
    require(keys.issubset(stage), "Provider stage telemetry is missing required fields")
    require(stage["requested"] is requested, "Provider stage requested flag is inconsistent")
    require(
        stage["outcome"] in {"not_requested", "used", "unavailable", "fallback"},
        "Unknown provider outcome",
    )
    require(
        isinstance(stage["status_code"], str) and len(stage["status_code"]) <= 96,
        "Unsafe provider status code",
    )
    require(
        isinstance(stage["latency_ms"], (int, float)) and stage["latency_ms"] >= 0,
        "Invalid provider latency",
    )
    usage = stage["usage"]
    if usage is not None:
        require(isinstance(usage, dict), "Provider usage is not an object")
        for field in (
            "input_tokens",
            "cached_input_tokens",
            "output_tokens",
            "reasoning_tokens",
            "total_tokens",
        ):
            require(
                isinstance(usage.get(field), int) and usage[field] >= 0,
                f"Invalid token field: {field}",
            )
    cost = stage["estimated_cost_usd"]
    require(
        cost is None or (isinstance(cost, (int, float)) and cost >= 0),
        "Invalid stage cost",
    )
    return {
        "stage": stage["stage"],
        "requested": stage["requested"],
        "outcome": stage["outcome"],
        "status_code": stage["status_code"],
        "model": stage["model"],
        "prompt_version": stage["prompt_version"],
        "schema_version": stage["schema_version"],
        "latency_ms": stage["latency_ms"],
        "total_tokens": usage["total_tokens"] if usage else 0,
        "estimated_cost_usd": cost,
        "cost_estimate_status": stage["cost_estimate_status"],
    }


def validate_telemetry(payload: dict[str, Any], *, requested: bool) -> dict[str, Any]:
    telemetry = payload.get("provider_telemetry")
    require(isinstance(telemetry, dict), "Smart Fit response is missing provider telemetry")
    keys = {
        "telemetry_version",
        "pricing_catalog_version",
        "pricing_currency",
        "pricing_basis",
        "extraction",
        "coaching",
        "total_provider_latency_ms",
        "total_tokens",
        "total_estimated_cost_usd",
        "cost_estimate_status",
    }
    require(keys.issubset(telemetry), "Provider telemetry summary is missing required fields")
    require(telemetry["pricing_currency"] == "USD", "Unexpected telemetry currency")
    require(telemetry["total_provider_latency_ms"] >= 0, "Invalid total provider latency")
    require(
        isinstance(telemetry["total_tokens"], int) and telemetry["total_tokens"] >= 0,
        "Invalid total token count",
    )
    serialized = json.dumps(telemetry, sort_keys=True)
    require(
        CANARY_RESUME not in serialized and CANARY_JOB not in serialized,
        "Provider telemetry contains request documents",
    )
    return {
        "telemetry_version": telemetry["telemetry_version"],
        "pricing_catalog_version": telemetry["pricing_catalog_version"],
        "pricing_currency": telemetry["pricing_currency"],
        "total_provider_latency_ms": telemetry["total_provider_latency_ms"],
        "total_tokens": telemetry["total_tokens"],
        "total_estimated_cost_usd": telemetry["total_estimated_cost_usd"],
        "cost_estimate_status": telemetry["cost_estimate_status"],
        "extraction": validate_stage(telemetry["extraction"], requested=requested),
        "coaching": validate_stage(telemetry["coaching"], requested=requested),
    }


def deterministic_fingerprint(payload: dict[str, Any]) -> str:
    assessments = [
        {
            key: item.get(key)
            for key in (
                "skill",
                "requirement_type",
                "weight",
                "status",
                "strength",
                "job_evidence",
                "resume_evidence",
                "grounded",
            )
        }
        for item in payload.get("requirement_assessments", [])
    ]
    return stable_hash(
        {
            "fit_summary": payload.get("fit_summary"),
            "hard_requirements": payload.get("hard_requirements"),
            "requirement_assessments": assessments,
            "category_coverage": payload.get("category_coverage"),
            "provenance_version": payload.get("provenance_version"),
        }
    )


def validate_smart_fit(payload: dict[str, Any], *, requested: bool) -> dict[str, Any]:
    missing = SMART_FIT_KEYS - payload.keys()
    require(not missing, "Smart Fit response is missing keys: " + ", ".join(sorted(missing)))
    require(
        payload["analysis_engine"] in {"deterministic", "model_assisted"},
        "Unknown analysis engine",
    )
    require(
        isinstance(payload["model_assisted_status"], str)
        and payload["model_assisted_status"],
        "Missing model status",
    )
    require(
        isinstance(payload["report_summary"], list) and payload["report_summary"],
        "Smart Fit report summary is empty",
    )
    require(
        isinstance(payload["category_coverage"], list) and payload["category_coverage"],
        "Category coverage is empty",
    )
    fit = payload["fit_summary"]
    require(isinstance(fit, dict), "Fit summary is not an object")
    require(
        isinstance(fit.get("score"), (int, float)) and 0 <= fit["score"] <= 100,
        "Fit score is out of range",
    )
    require(
        isinstance(fit.get("confidence"), (int, float))
        and 0 <= fit["confidence"] <= 1,
        "Confidence is out of range",
    )
    assessments = payload["requirement_assessments"]
    require(isinstance(assessments, list), "Requirement assessments are not a list")
    require(
        all(item.get("grounded") is True for item in assessments),
        "Smart Fit returned ungrounded conclusions",
    )
    return {
        "analysis_engine": payload["analysis_engine"],
        "model_assisted_status": payload["model_assisted_status"],
        "fit_score": fit["score"],
        "fit_band": fit.get("band"),
        "fit_confidence": fit["confidence"],
        "requirement_count": len(assessments),
        "hard_requirement_count": len(payload["hard_requirements"]),
        "grounding_warning_count": len(payload["grounding_warnings"]),
        "deterministic_fingerprint": deterministic_fingerprint(payload),
        "telemetry": validate_telemetry(payload, requested=requested),
    }


def run_smart_fit(*, assisted: bool) -> dict[str, Any]:
    status, text = request_text(
        f"{BACKEND_URL}/analysis/smart",
        method="POST",
        body={
            "resume_text": CANARY_RESUME,
            "job_description": CANARY_JOB,
            "use_model_assisted": assisted,
        },
    )
    payload = object_json(status, text, context="Smart Fit analysis")
    return validate_smart_fit(payload, requested=assisted)


def model_status() -> dict[str, Any]:
    status, text = request_text(f"{BACKEND_URL}/analysis/model-status")
    payload = object_json(status, text, context="Model-assisted status")
    required = {"enabled", "status", "required_backend_settings", "safety_notes"}
    require(required.issubset(payload), "Model status is missing required fields")
    require(
        payload["status"] in {"configured", "not_configured"},
        "Unknown model configuration status",
    )
    require(
        payload["enabled"] is (payload["status"] == "configured"),
        "Model enabled/status fields disagree",
    )
    return {
        "enabled": payload["enabled"],
        "status": payload["status"],
        "required_backend_setting_count": len(payload["required_backend_settings"]),
        "safety_note_count": len(payload["safety_notes"]),
    }


def safe_validation_error() -> dict[str, Any]:
    status, text = request_text(
        f"{BACKEND_URL}/analysis/smart",
        method="POST",
        body={
            "resume_text": [REJECTED_MARKER],
            "job_description": CANARY_JOB,
            "use_model_assisted": False,
        },
    )
    payload = object_json(status, text, context="Invalid Smart Fit request", expected=422)
    require(REJECTED_MARKER not in text, "HTTP 422 response echoed the rejected marker")
    require(
        payload.get("detail") == "Request validation failed.",
        "HTTP 422 response did not use the safe detail",
    )
    errors = payload.get("errors")
    require(
        isinstance(errors, list) and errors,
        "HTTP 422 response is missing bounded error metadata",
    )
    require(
        all(set(error).issubset({"type", "location"}) for error in errors),
        "HTTP 422 response exposed extra fields",
    )
    return {
        "status": status,
        "detail": payload["detail"],
        "error_count": len(errors),
        "rejected_value_echoed": False,
    }


def production_canary(root: Path) -> dict[str, Any]:
    expected_revision = normalized_expected_revision()
    deployment = wait_for_deployment(expected_revision)

    deterministic = run_smart_fit(assisted=False)
    require(
        deterministic["analysis_engine"] == "deterministic",
        "Non-requested Smart Fit was not deterministic",
    )
    require(
        deterministic["telemetry"]["extraction"]["outcome"] == "not_requested"
        and deterministic["telemetry"]["coaching"]["outcome"] == "not_requested",
        "Non-requested provider stages did not report not_requested",
    )

    assisted = run_smart_fit(assisted=True)
    fell_back = assisted["analysis_engine"] == "deterministic"
    if fell_back:
        require(
            assisted["model_assisted_status"].startswith("fallback"),
            "Fallback status was not explicit",
        )
        require(
            assisted["deterministic_fingerprint"]
            == deterministic["deterministic_fingerprint"],
            "Provider fallback did not preserve the deterministic report fingerprint",
        )
    else:
        require(
            assisted["model_assisted_status"] == "used",
            "Model-assisted result did not expose used status",
        )
        require(
            assisted["telemetry"]["extraction"]["outcome"] == "used",
            "Successful model-assisted analysis did not report used extraction telemetry",
        )

    return {
        "canary_version": CANARY_VERSION,
        "backend_url": BACKEND_URL,
        "frontend_url": FRONTEND_URL,
        "frontend_source_contract": frontend_source_contract(root),
        "deployment": deployment,
        "model_status": model_status(),
        "deterministic_smart_fit": deterministic,
        "model_assisted_smart_fit": assisted,
        "model_assisted_request_fell_back": fell_back,
        "fallback_fingerprint_preserved": (
            assisted["deterministic_fingerprint"]
            == deterministic["deterministic_fingerprint"]
            if fell_back
            else None
        ),
        "successful_assisted_analysis_grounded": (
            assisted["grounding_warning_count"] == 0 if not fell_back else None
        ),
        "safe_validation_error": safe_validation_error(),
        "status": "passed",
    }


def sanitized_failure(exc: BaseException) -> dict[str, Any]:
    message = re.sub(r"[\x00-\x1f\x7f]+", " ", str(exc)).strip()[:500]
    return {
        "canary_version": CANARY_VERSION,
        "status": "failed",
        "failure_type": type(exc).__name__,
        "failure_message": message or "Canary failed without a safe message.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontend-source-only", action="store_true")
    parser.add_argument(
        "--repository-root",
        default=str(Path(__file__).resolve().parents[1]),
    )
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()
    report = (
        {
            "canary_version": CANARY_VERSION,
            "frontend_source_contract": frontend_source_contract(root),
            "status": "passed",
        }
        if args.frontend_source_only
        else production_canary(root)
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CanaryFailure, OSError) as exc:
        print(json.dumps(sanitized_failure(exc), indent=2, sort_keys=True))
        raise SystemExit(1) from exc
