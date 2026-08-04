"""Bounded exact-revision production audit for universal occupation search."""

from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx

from . import occupation_catalog_runtime as occupation_runtime
from .production_canary import DEFAULT_BACKEND_URL, normalize_base_url, normalize_revision

DEFAULT_AUDIT_PATH = (
    Path(__file__).resolve().parents[1]
    / "evaluation"
    / "production_occupation_audit.json"
)


class ProductionOccupationAuditError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ProductionOccupationAuditCaseResult:
    id: str
    kind: str
    career_sphere: str
    query: str
    passed: bool
    latency_ms: float
    result_count: int
    relevant_title_count: int
    returned_titles: list[str]
    providers_searched_count: int
    coverage_statuses: dict[str, int]
    warning_count: int
    suggestion_count: int
    external_link_count: int
    error_code: str | None = None


def load_production_occupation_audit(
    path: Path | None = None,
) -> dict[str, Any]:
    with (path or DEFAULT_AUDIT_PATH).open(encoding="utf-8") as audit_file:
        audit = json.load(audit_file)
    if audit.get("version") != 1:
        raise ValueError("Unsupported production occupation audit version.")
    cases = audit.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Production occupation audit cases must be non-empty.")
    ids = [str(case.get("id") or "") for case in cases]
    if any(not case_id for case_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("Production occupation audit case ids must be unique and non-empty.")
    if len(cases) < int(audit.get("minimum_cases") or 0):
        raise ValueError("Production occupation audit does not meet its minimum case count.")
    max_results = int(audit.get("max_results_per_case") or 0)
    if not 1 <= max_results <= 5:
        raise ValueError("Production occupation audit max-results bound must be between one and five.")

    recognized_spheres = {
        str(case.get("career_sphere") or "")
        for case in cases
        if case.get("kind") == "recognized"
    }
    if len(recognized_spheres) < int(audit.get("minimum_career_spheres") or 0):
        raise ValueError("Production occupation audit does not meet career-sphere coverage.")

    for case in cases:
        if case.get("kind") not in {"recognized", "ambiguous", "unknown"}:
            raise ValueError(f"Unsupported production audit kind for {case['id']}.")
        if not str(case.get("query") or "").strip():
            raise ValueError(f"Production audit query is missing for {case['id']}.")
    return audit


def _safe_object(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise ProductionOccupationAuditError(
            "invalid_json_response",
            "Production search returned invalid JSON.",
        ) from exc
    if not isinstance(payload, dict):
        raise ProductionOccupationAuditError(
            "unexpected_json_shape",
            "Production search returned a non-object JSON response.",
        )
    return payload


def _safe_list(payload: dict[str, Any], field: str) -> list[Any]:
    value = payload.get(field)
    if not isinstance(value, list):
        raise ProductionOccupationAuditError(
            "unexpected_json_shape",
            f"Production search field {field!r} was not a list.",
        )
    return value


class ProductionOccupationAudit:
    def __init__(
        self,
        *,
        backend_url: str = DEFAULT_BACKEND_URL,
        expected_revision: str | None = None,
        timeout_seconds: float = 90.0,
        inter_request_seconds: float = 2.25,
        audit: dict[str, Any] | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.backend_url = normalize_base_url(backend_url)
        self.expected_revision = normalize_revision(expected_revision)
        self.inter_request_seconds = max(0.0, inter_request_seconds)
        self.audit = audit or load_production_occupation_audit()
        self._client = client or httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "MarketLens-Production-Occupation-Audit/1.0"},
        )
        self._owns_client = client is None
        self.case_results: list[ProductionOccupationAuditCaseResult] = []

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def wait_for_exact_revision(
        self,
        *,
        wait_seconds: float = 0.0,
        interval_seconds: float = 10.0,
    ) -> None:
        if self.expected_revision is None:
            return
        deadline = time.monotonic() + max(0.0, wait_seconds)
        last_revision: str | None = None
        while True:
            try:
                response = self._client.get(f"{self.backend_url}/deployment/status")
                if response.status_code == 200:
                    last_revision = str(_safe_object(response).get("revision") or "").lower()
            except Exception:
                pass
            if last_revision == self.expected_revision:
                return
            if time.monotonic() >= deadline:
                raise ProductionOccupationAuditError(
                    "deployment_revision_timeout",
                    "Production backend did not reach the expected revision before the audit deadline.",
                )
            time.sleep(max(0.1, interval_seconds))

    def _search_response(self, params: dict[str, Any]) -> httpx.Response:
        response = self._client.get(f"{self.backend_url}/jobs/search", params=params)
        if response.status_code != 429:
            return response
        retry_after = response.headers.get("Retry-After", "60")
        try:
            wait_seconds = min(65.0, max(1.0, float(retry_after)))
        except ValueError:
            wait_seconds = 60.0
        time.sleep(wait_seconds)
        return self._client.get(f"{self.backend_url}/jobs/search", params=params)

    @staticmethod
    def _validate_interpretation(case: dict[str, Any]) -> Any:
        interpretation = occupation_runtime.interpret_occupation_query(case["query"])
        if interpretation.status != case["expected_status"]:
            raise ProductionOccupationAuditError(
                "local_interpretation_mismatch",
                "Checked-out runtime did not match the committed production-audit expectation.",
            )
        if case["kind"] == "recognized":
            if interpretation.concept_key != case["expected_concept_key"]:
                raise ProductionOccupationAuditError(
                    "local_concept_mismatch",
                    "Checked-out runtime resolved the wrong occupation concept.",
                )
            if interpretation.soc_major_group != case["expected_soc_major_group"]:
                raise ProductionOccupationAuditError(
                    "local_soc_group_mismatch",
                    "Checked-out runtime resolved the wrong SOC major group.",
                )
        return interpretation

    def _run_case(self, case: dict[str, Any]) -> dict[str, Any]:
        interpretation = self._validate_interpretation(case)
        max_results = int(self.audit["max_results_per_case"])
        params: dict[str, Any] = {
            "query": case["query"],
            "limit": str(max_results),
        }
        if case.get("location"):
            params["location"] = case["location"]
        if case.get("level"):
            params["level"] = case["level"]

        response = self._search_response(params)
        if response.status_code != 200:
            raise ProductionOccupationAuditError(
                "unexpected_http_status",
                f"Production search returned HTTP {response.status_code}.",
            )
        payload = _safe_object(response)
        results = _safe_list(payload, "results")
        providers = _safe_list(payload, "providers_searched")
        coverage = _safe_list(payload, "source_coverage")
        warnings = _safe_list(payload, "warnings")
        suggestions = _safe_list(payload, "search_suggestions")
        external_links = _safe_list(payload, "external_search_links")

        result_count = payload.get("result_count")
        if not isinstance(result_count, int) or result_count != len(results):
            raise ProductionOccupationAuditError(
                "result_count_mismatch",
                "Production result_count did not match the result list.",
            )
        if result_count > max_results:
            raise ProductionOccupationAuditError(
                "result_bound_failed",
                "Production search exceeded the committed result bound.",
            )

        if case.get("level") and payload.get("level") != case["level"]:
            raise ProductionOccupationAuditError(
                "level_echo_mismatch",
                "Production search did not preserve the requested level filter.",
            )
        if case.get("location") and payload.get("location") != case["location"]:
            raise ProductionOccupationAuditError(
                "location_echo_mismatch",
                "Production search did not preserve the requested location filter.",
            )

        returned_titles: list[str] = []
        relevant_title_count = 0
        if case["kind"] == "recognized":
            if not coverage:
                raise ProductionOccupationAuditError(
                    "source_coverage_missing",
                    "Recognized production search did not report source coverage.",
                )
            for result in results:
                if not isinstance(result, dict) or not isinstance(result.get("title"), str):
                    raise ProductionOccupationAuditError(
                        "unexpected_result_shape",
                        "Production result did not include a title.",
                    )
                title = result["title"].strip()
                returned_titles.append(title)
                if not occupation_runtime.title_matches_occupation(title, interpretation):
                    raise ProductionOccupationAuditError(
                        "irrelevant_result_title",
                        f"Production returned an unrelated title for {case['id']}.",
                    )
                relevant_title_count += 1
            if not results and (not warnings or not external_links):
                raise ProductionOccupationAuditError(
                    "zero_result_explanation_missing",
                    "Recognized zero-result search lacked warnings or external fallbacks.",
                )
        else:
            if providers or results:
                raise ProductionOccupationAuditError(
                    "unsafe_provider_fanout",
                    "Ambiguous or unknown query searched providers or returned jobs.",
                )
            if case["kind"] == "ambiguous" and not suggestions:
                raise ProductionOccupationAuditError(
                    "ambiguity_suggestions_missing",
                    "Ambiguous production query did not provide clarification suggestions.",
                )
            if case["kind"] == "unknown" and not (warnings or suggestions):
                raise ProductionOccupationAuditError(
                    "unknown_explanation_missing",
                    "Unknown production query did not explain the safe stop.",
                )

        coverage_statuses = Counter(
            str(item.get("status") or "unknown")
            for item in coverage
            if isinstance(item, dict)
        )
        return {
            "result_count": result_count,
            "relevant_title_count": relevant_title_count,
            "returned_titles": returned_titles,
            "providers_searched_count": len(providers),
            "coverage_statuses": dict(sorted(coverage_statuses.items())),
            "warning_count": len(warnings),
            "suggestion_count": len(suggestions),
            "external_link_count": len(external_links),
        }

    def run(self) -> None:
        self.case_results = []
        cases = self.audit["cases"]
        for index, case in enumerate(cases):
            started = time.perf_counter()
            try:
                details = self._run_case(case)
            except ProductionOccupationAuditError as exc:
                details = {
                    "result_count": 0,
                    "relevant_title_count": 0,
                    "returned_titles": [],
                    "providers_searched_count": 0,
                    "coverage_statuses": {},
                    "warning_count": 0,
                    "suggestion_count": 0,
                    "external_link_count": 0,
                }
                passed = False
                error_code = exc.code
            except Exception:
                details = {
                    "result_count": 0,
                    "relevant_title_count": 0,
                    "returned_titles": [],
                    "providers_searched_count": 0,
                    "coverage_statuses": {},
                    "warning_count": 0,
                    "suggestion_count": 0,
                    "external_link_count": 0,
                }
                passed = False
                error_code = "unexpected_audit_error"
            else:
                passed = True
                error_code = None

            self.case_results.append(
                ProductionOccupationAuditCaseResult(
                    id=case["id"],
                    kind=case["kind"],
                    career_sphere=case["career_sphere"],
                    query=case["query"],
                    passed=passed,
                    latency_ms=round((time.perf_counter() - started) * 1_000, 3),
                    error_code=error_code,
                    **details,
                )
            )
            if index < len(cases) - 1 and self.inter_request_seconds:
                time.sleep(self.inter_request_seconds)

    def report(self) -> dict[str, Any]:
        results = self.case_results
        passed_cases = sum(result.passed for result in results)
        total_titles = sum(result.result_count for result in results)
        relevant_titles = sum(result.relevant_title_count for result in results)
        recognized_results = [result for result in results if result.kind == "recognized"]
        provider_statuses: Counter[str] = Counter()
        for result in results:
            provider_statuses.update(result.coverage_statuses)
        latencies = [result.latency_ms for result in results]
        career_spheres = {
            result.career_sphere
            for result in recognized_results
        }
        return {
            "version": self.audit["version"],
            "backend_url": self.backend_url,
            "expected_revision": self.expected_revision,
            "passed": bool(results) and passed_cases == len(results),
            "counts": {
                "cases": len(results),
                "passed_cases": passed_cases,
                "failed_cases": len(results) - passed_cases,
                "recognized_cases": len(recognized_results),
                "ambiguous_cases": sum(result.kind == "ambiguous" for result in results),
                "unknown_cases": sum(result.kind == "unknown" for result in results),
                "career_spheres": len(career_spheres),
                "result_bearing_cases": sum(result.result_count > 0 for result in recognized_results),
                "zero_result_cases": sum(result.result_count == 0 for result in recognized_results),
                "returned_titles": total_titles,
                "relevant_titles": relevant_titles,
            },
            "metrics": {
                "case_accuracy": passed_cases / len(results) if results else 0.0,
                "returned_title_precision": (
                    relevant_titles / total_titles if total_titles else 1.0
                ),
                "average_case_latency_ms": (
                    round(sum(latencies) / len(latencies), 3) if latencies else 0.0
                ),
                "maximum_case_latency_ms": max(latencies, default=0.0),
                "total_measured_latency_ms": round(sum(latencies), 3),
            },
            "coverage": {
                "career_spheres": sorted(career_spheres),
                "provider_statuses": dict(sorted(provider_statuses.items())),
            },
            "cases": [asdict(result) for result in results],
        }


def format_production_occupation_audit_report(report: dict[str, Any]) -> str:
    counts = report["counts"]
    metrics = report["metrics"]
    lines = [
        f"MarketLens Production Occupation Audit: {'PASS' if report['passed'] else 'FAIL'}",
        f"Expected revision: {report.get('expected_revision') or 'not enforced'}",
        (
            f"Cases: {counts['passed_cases']}/{counts['cases']} passed across "
            f"{counts['career_spheres']} career spheres"
        ),
        (
            f"Returned titles: {counts['relevant_titles']}/{counts['returned_titles']} relevant "
            f"({metrics['returned_title_precision']:.1%} precision)"
        ),
        (
            f"Recognized searches: {counts['result_bearing_cases']} with results / "
            f"{counts['zero_result_cases']} honest zero-result outcomes"
        ),
        (
            f"Latency: {metrics['average_case_latency_ms']:.3f} ms average / "
            f"{metrics['maximum_case_latency_ms']:.3f} ms maximum"
        ),
    ]
    failed = [case for case in report["cases"] if not case["passed"]]
    if failed:
        lines.append("Failed cases:")
        for case in failed:
            lines.append(f"- {case['id']}: {case['error_code']}")
    else:
        lines.append("No production-audit case failures.")
    return "\n".join(lines)
