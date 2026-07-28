"""Offline provider-resilience evaluation for Milestone 8E.

The evaluator replaces ``httpx.Client`` with an in-memory client, exercises the
real extraction and coaching adapters, and proves every provider failure keeps
the completed deterministic report intact. Reports contain only scenario IDs,
safe failure codes, fingerprints, and pass/fail metrics.
"""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Literal
from unittest.mock import patch

import httpx

from app.analysis import analyze_smart_fit
from app.analysis.schemas import SmartFitAnalysisResponse
from app.analysis.semantic_contract import MODEL_ASSISTED_SCHEMA_VERSION
from app.analysis.schemas import COACHING_SCHEMA_VERSION

RESUME_TEXT = """PROJECTS
Built a Python FastAPI service backed by PostgreSQL.
SKILLS
Python, SQL, FastAPI, PostgreSQL
"""

JOB_DESCRIPTION = """Backend Engineer
REQUIRED QUALIFICATIONS
Python and SQL are required.
PREFERRED QUALIFICATIONS
Docker is preferred.
RESPONSIBILITIES
Build reliable backend APIs.
"""

EXTRACTION_FAILURES: tuple[tuple[str, str], ...] = (
    ("timeout", "provider_timeout"),
    ("transport", "provider_transport_error"),
    ("http", "provider_http_429"),
    ("invalid_json", "provider_invalid_json"),
    ("missing_output", "provider_missing_output"),
    ("schema_mismatch", "provider_schema_mismatch"),
    ("ungrounded", "provider_ungrounded_evidence"),
)

COACHING_FAILURES: tuple[tuple[str, str], ...] = (
    ("timeout", "coaching_timeout"),
    ("transport", "coaching_transport_error"),
    ("http", "coaching_http_429"),
    ("invalid_json", "coaching_invalid_json"),
    ("missing_output", "coaching_missing_output"),
    ("schema_mismatch", "coaching_schema_mismatch"),
    ("rejected", "coaching_unknown_reference"),
)

_PROVIDER_ENV_KEYS = (
    "AI_ANALYSIS_ENABLED",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OPENAI_BASE_URL",
    "OPENAI_TIMEOUT_SECONDS",
)
_METADATA_FIELDS = {
    "analysis_engine",
    "model_assisted_status",
    "coaching_engine",
    "coaching_status",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _preservation_payload(analysis: SmartFitAnalysisResponse) -> dict[str, Any]:
    payload = analysis.model_dump(mode="json")
    for field in _METADATA_FIELDS:
        payload.pop(field, None)
    return payload


def _empty_extraction_output() -> str:
    return json.dumps(
        {
            "schema_version": MODEL_ASSISTED_SCHEMA_VERSION,
            "resume_skills": [],
            "job_requirements": [],
            "hard_constraints": [],
            "unknown_resume_skills": [],
            "unknown_job_skills": [],
            "uncertainty_notes": [],
        }
    )


def _ungrounded_extraction_output() -> str:
    return json.dumps(
        {
            "schema_version": MODEL_ASSISTED_SCHEMA_VERSION,
            "resume_skills": [],
            "job_requirements": [
                {
                    "skill": "Kubernetes",
                    "category": "devops",
                    "semantic_category": "tool_technology",
                    "requirement_type": "required_qualification",
                    "confidence": 0.95,
                    "context": "container orchestration",
                    "source_text": "Kubernetes is required",
                }
            ],
            "hard_constraints": [],
            "unknown_resume_skills": [],
            "unknown_job_skills": ["Kubernetes"],
            "uncertainty_notes": [],
        }
    )


def _rejected_coaching_output() -> str:
    return json.dumps(
        {
            "schema_version": COACHING_SCHEMA_VERSION,
            "strategy_summary": "Prioritize the strongest grounded evidence while addressing the most important documented gaps.",
            "action_items": [
                {
                    "action_type": "resume_rewrite",
                    "priority": "high",
                    "basis": "wording_proof_gap",
                    "title": "Rewrite an unsupported requirement",
                    "reference": "Unknown Provider Reference",
                    "category": None,
                    "resume_evidence": [],
                    "job_evidence": None,
                    "advice": "Rewrite the resume around this unsupported reference even though it is absent from the completed assessment.",
                }
            ],
            "application_guidance": "Apply only after verifying every claim against the completed grounded assessment.",
            "uncertainty_note": None,
        }
    )


@dataclass(frozen=True)
class ProviderScenario:
    extraction: str = "success"
    coaching: str = "timeout"


class _ScenarioClient:
    def __init__(self, scenario: ProviderScenario, timeout: float | None = None):
        self._scenario = scenario
        self._timeout = timeout

    def __enter__(self) -> "_ScenarioClient":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        return None

    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any],
    ) -> httpx.Response:
        del headers
        format_name = str(json.get("text", {}).get("format", {}).get("name", ""))
        stage: Literal["extraction", "coaching"] = (
            "extraction" if "semantic_extraction" in format_name else "coaching"
        )
        behavior = getattr(self._scenario, stage)
        request = httpx.Request("POST", url)

        if behavior == "timeout":
            raise httpx.ReadTimeout("synthetic timeout", request=request)
        if behavior == "transport":
            raise httpx.ConnectError("synthetic transport failure", request=request)
        if behavior == "http":
            return httpx.Response(
                429,
                json={"error": {"type": "rate_limit"}},
                headers={"x-request-id": "synthetic-request"},
                request=request,
            )
        if behavior == "invalid_json":
            return httpx.Response(200, content=b"not-json", request=request)
        if behavior == "missing_output":
            return httpx.Response(200, json={}, request=request)
        if behavior == "schema_mismatch":
            return httpx.Response(
                200,
                json={"output_text": json_module.dumps({"schema_version": "invalid"})},
                request=request,
            )
        if behavior == "ungrounded" and stage == "extraction":
            return httpx.Response(
                200,
                json={"output_text": _ungrounded_extraction_output()},
                request=request,
            )
        if behavior == "rejected" and stage == "coaching":
            return httpx.Response(
                200,
                json={"output_text": _rejected_coaching_output()},
                request=request,
            )
        if behavior != "success":
            raise AssertionError(f"Unsupported synthetic behavior: {behavior}")

        output_text = (
            _empty_extraction_output()
            if stage == "extraction"
            else _rejected_coaching_output()
        )
        return httpx.Response(
            200,
            json={"output_text": output_text},
            request=request,
        )


# Keep JSON payload construction readable without shadowing the ``json`` request argument.
json_module = json


@contextmanager
def _provider_environment(*, configured: bool) -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in _PROVIDER_ENV_KEYS}
    try:
        if configured:
            os.environ.update(
                {
                    "AI_ANALYSIS_ENABLED": "true",
                    "OPENAI_API_KEY": "synthetic-test-key",
                    "OPENAI_MODEL": "synthetic-test-model",
                    "OPENAI_BASE_URL": "https://provider.invalid/v1",
                    "OPENAI_TIMEOUT_SECONDS": "1",
                }
            )
        else:
            os.environ["AI_ANALYSIS_ENABLED"] = "false"
            os.environ.pop("OPENAI_API_KEY", None)
            os.environ.pop("OPENAI_MODEL", None)
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@contextmanager
def _scenario_client(scenario: ProviderScenario) -> Iterator[None]:
    def client_factory(*args: Any, **kwargs: Any) -> _ScenarioClient:
        timeout = kwargs.get("timeout")
        if timeout is None and args:
            timeout = args[0]
        return _ScenarioClient(scenario, timeout=timeout)

    with patch.object(httpx, "Client", client_factory):
        yield


def _run_scenario(scenario: ProviderScenario) -> SmartFitAnalysisResponse:
    with _provider_environment(configured=True), _scenario_client(scenario):
        return analyze_smart_fit(
            resume_text=RESUME_TEXT,
            job_description=JOB_DESCRIPTION,
            use_model_assisted=True,
        )


def evaluate_provider_resilience() -> dict[str, Any]:
    baseline = analyze_smart_fit(
        resume_text=RESUME_TEXT,
        job_description=JOB_DESCRIPTION,
        use_model_assisted=False,
    )
    baseline_payload = _preservation_payload(baseline)
    baseline_fingerprint = _fingerprint(baseline_payload)

    cases: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    with _provider_environment(configured=False):
        unavailable = analyze_smart_fit(
            resume_text=RESUME_TEXT,
            job_description=JOB_DESCRIPTION,
            use_model_assisted=True,
        )
    unavailable_preserved = _fingerprint(_preservation_payload(unavailable)) == baseline_fingerprint
    unavailable_passed = (
        unavailable_preserved
        and unavailable.model_assisted_status.startswith("fallback_unavailable:")
        and unavailable.coaching_status.startswith("fallback_unavailable:")
    )
    cases.append(
        {
            "id": "provider_unavailable",
            "stage": "both",
            "passed": unavailable_passed,
            "preserved": unavailable_preserved,
            "model_status": unavailable.model_assisted_status.split(":", 1)[0],
            "coaching_status": unavailable.coaching_status.split(":", 1)[0],
            "fingerprint": _fingerprint(_preservation_payload(unavailable)),
        }
    )
    if not unavailable_passed:
        failures.append({"id": "provider_unavailable", "check": "unavailable_fallback"})

    for behavior, expected_code in EXTRACTION_FAILURES:
        analysis = _run_scenario(
            ProviderScenario(extraction=behavior, coaching="timeout")
        )
        preserved = _fingerprint(_preservation_payload(analysis)) == baseline_fingerprint
        expected_model_status = f"fallback_failed: {expected_code}"
        expected_coaching_status = "fallback_failed: coaching_timeout"
        passed = (
            preserved
            and analysis.analysis_engine == "deterministic"
            and analysis.coaching_engine == "deterministic"
            and analysis.model_assisted_status == expected_model_status
            and analysis.coaching_status == expected_coaching_status
        )
        cases.append(
            {
                "id": f"extraction_{behavior}",
                "stage": "extraction",
                "passed": passed,
                "preserved": preserved,
                "model_status": analysis.model_assisted_status,
                "coaching_status": analysis.coaching_status,
                "fingerprint": _fingerprint(_preservation_payload(analysis)),
            }
        )
        if not passed:
            failures.append(
                {
                    "id": f"extraction_{behavior}",
                    "check": "status_or_preservation",
                    "expected_model_status": expected_model_status,
                    "actual_model_status": analysis.model_assisted_status,
                    "expected_coaching_status": expected_coaching_status,
                    "actual_coaching_status": analysis.coaching_status,
                    "preserved": preserved,
                }
            )

    for behavior, expected_code in COACHING_FAILURES:
        analysis = _run_scenario(
            ProviderScenario(extraction="success", coaching=behavior)
        )
        preserved = _fingerprint(_preservation_payload(analysis)) == baseline_fingerprint
        expected_coaching_status = f"fallback_failed: {expected_code}"
        passed = (
            preserved
            and analysis.analysis_engine == "model_assisted"
            and analysis.model_assisted_status == "used"
            and analysis.coaching_engine == "deterministic"
            and analysis.coaching_status == expected_coaching_status
        )
        cases.append(
            {
                "id": f"coaching_{behavior}",
                "stage": "coaching",
                "passed": passed,
                "preserved": preserved,
                "model_status": analysis.model_assisted_status,
                "coaching_status": analysis.coaching_status,
                "fingerprint": _fingerprint(_preservation_payload(analysis)),
            }
        )
        if not passed:
            failures.append(
                {
                    "id": f"coaching_{behavior}",
                    "check": "status_or_preservation",
                    "expected_coaching_status": expected_coaching_status,
                    "actual_coaching_status": analysis.coaching_status,
                    "model_status": analysis.model_assisted_status,
                    "preserved": preserved,
                }
            )

    passed_count = sum(int(case["passed"]) for case in cases)
    preserved_count = sum(int(case["preserved"]) for case in cases)
    return {
        "version": 1,
        "passed": not failures,
        "baseline_fingerprint": baseline_fingerprint,
        "counts": {
            "cases": len(cases),
            "passed": passed_count,
            "preserved": preserved_count,
            "failures": len(failures),
        },
        "metrics": {
            "case_pass_rate": passed_count / len(cases),
            "deterministic_preservation_rate": preserved_count / len(cases),
        },
        "failures": failures,
        "cases": cases,
    }


def format_provider_resilience_report(report: dict[str, Any]) -> str:
    status = "PASS" if report["passed"] else "FAIL"
    lines = [
        f"Provider resilience evaluation: {status}",
        f"Cases: {report['counts']['cases']}",
        f"Case pass rate: {report['metrics']['case_pass_rate']:.1%}",
        (
            "Deterministic output preservation: "
            f"{report['metrics']['deterministic_preservation_rate']:.1%}"
        ),
    ]
    if report["failures"]:
        lines.append("Failures:")
        for failure in report["failures"]:
            lines.append(f"- {failure['id']}: {failure['check']}")
    return "\n".join(lines)


__all__ = [
    "COACHING_FAILURES",
    "EXTRACTION_FAILURES",
    "ProviderScenario",
    "evaluate_provider_resilience",
    "format_provider_resilience_report",
]
