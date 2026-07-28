from __future__ import annotations

import json
import os
from contextlib import contextmanager
from typing import Any, Iterator
from unittest.mock import patch

import httpx

from app.analysis import analyze_smart_fit
from app.analysis.model_extractor import MODEL_ASSISTED_PROMPT_VERSION
from app.analysis.personalized_coaching import COACHING_PROMPT_VERSION
from app.analysis.provider_telemetry import (
    PRICING_CATALOG_VERSION,
    TELEMETRY_VERSION,
)
from app.analysis.schemas import COACHING_SCHEMA_VERSION, EvidenceStatus
from app.analysis.semantic_contract import MODEL_ASSISTED_SCHEMA_VERSION

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

_PROVIDER_ENV_KEYS = (
    "AI_ANALYSIS_ENABLED",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OPENAI_BASE_URL",
    "OPENAI_TIMEOUT_SECONDS",
)


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


def _valid_coaching_output() -> str:
    deterministic = analyze_smart_fit(
        resume_text=RESUME_TEXT,
        job_description=JOB_DESCRIPTION,
        use_model_assisted=False,
    )
    assessment = next(
        item
        for item in deterministic.requirement_assessments
        if item.status in {EvidenceStatus.DEMONSTRATED, EvidenceStatus.EXPLICIT}
        and item.resume_evidence
    )
    return json.dumps(
        {
            "schema_version": COACHING_SCHEMA_VERSION,
            "strategy_summary": "Lead with the strongest grounded backend evidence and address the remaining documented gaps in priority order.",
            "action_items": [
                {
                    "action_type": "interview_prep",
                    "priority": "high",
                    "basis": "strength_positioning",
                    "title": "Prepare grounded backend evidence",
                    "reference": assessment.skill,
                    "category": None,
                    "resume_evidence": assessment.resume_evidence[:1],
                    "job_evidence": assessment.job_evidence,
                    "advice": "Prepare a concise example that explains the exact resume evidence, the technical decision, and the result without adding unsupported claims.",
                }
            ],
            "application_guidance": "Apply with the grounded backend evidence prominent and keep every resume claim traceable to the completed assessment.",
            "uncertainty_note": None,
        }
    )


class _SuccessfulTelemetryClient:
    def __init__(self, model: str, timeout: float | None = None):
        self._model = model
        self._timeout = timeout

    def __enter__(self) -> "_SuccessfulTelemetryClient":
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
        extraction = "semantic_extraction" in format_name
        request = httpx.Request("POST", url)
        if extraction:
            usage = {
                "input_tokens": 1000,
                "input_tokens_details": {"cached_tokens": 200},
                "output_tokens": 100,
                "output_tokens_details": {"reasoning_tokens": 20},
                "total_tokens": 1100,
            }
            output_text = _empty_extraction_output()
        else:
            usage = {
                "input_tokens": 500,
                "input_tokens_details": {"cached_tokens": 100},
                "output_tokens": 80,
                "output_tokens_details": {"reasoning_tokens": 10},
                "total_tokens": 580,
            }
            output_text = _valid_coaching_output()

        return httpx.Response(
            200,
            json={
                "model": self._model,
                "usage": usage,
                "output_text": output_text,
            },
            request=request,
        )


class _TimeoutTelemetryClient:
    def __init__(self, timeout: float | None = None):
        self._timeout = timeout

    def __enter__(self) -> "_TimeoutTelemetryClient":
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
        del headers, json
        request = httpx.Request("POST", url)
        raise httpx.ReadTimeout("synthetic timeout", request=request)


@contextmanager
def _provider_environment(model: str) -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in _PROVIDER_ENV_KEYS}
    os.environ.update(
        {
            "AI_ANALYSIS_ENABLED": "true",
            "OPENAI_API_KEY": "synthetic-telemetry-key",
            "OPENAI_MODEL": model,
            "OPENAI_BASE_URL": "https://provider.invalid/v1",
            "OPENAI_TIMEOUT_SECONDS": "1",
        }
    )
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _successful_client_factory(model: str):
    def factory(*args: Any, **kwargs: Any) -> _SuccessfulTelemetryClient:
        timeout = kwargs.get("timeout")
        if timeout is None and args:
            timeout = args[0]
        return _SuccessfulTelemetryClient(model, timeout=timeout)

    return factory


def _timeout_client_factory(*args: Any, **kwargs: Any) -> _TimeoutTelemetryClient:
    timeout = kwargs.get("timeout")
    if timeout is None and args:
        timeout = args[0]
    return _TimeoutTelemetryClient(timeout=timeout)


def test_deterministic_analysis_reports_explicit_no_call_telemetry() -> None:
    analysis = analyze_smart_fit(
        resume_text=RESUME_TEXT,
        job_description=JOB_DESCRIPTION,
        use_model_assisted=False,
    )
    telemetry = analysis.provider_telemetry

    assert telemetry is not None
    assert telemetry.telemetry_version == TELEMETRY_VERSION
    assert telemetry.pricing_catalog_version == PRICING_CATALOG_VERSION
    assert telemetry.extraction.requested is False
    assert telemetry.extraction.outcome == "not_requested"
    assert telemetry.extraction.status_code == "not_requested"
    assert telemetry.coaching.requested is False
    assert telemetry.coaching.outcome == "not_requested"
    assert telemetry.total_provider_latency_ms == 0
    assert telemetry.total_tokens == 0
    assert telemetry.total_estimated_cost_usd is None
    assert telemetry.cost_estimate_status == "not_applicable"


def test_successful_provider_calls_report_usage_cost_latency_and_versions() -> None:
    model = "gpt-5.4-mini-2026-03-17"
    with _provider_environment(model), patch.object(
        httpx,
        "Client",
        _successful_client_factory(model),
    ):
        analysis = analyze_smart_fit(
            resume_text=RESUME_TEXT,
            job_description=JOB_DESCRIPTION,
            use_model_assisted=True,
        )

    telemetry = analysis.provider_telemetry
    assert telemetry is not None
    assert analysis.analysis_engine == "model_assisted"
    assert analysis.coaching_engine == "model_assisted"

    extraction = telemetry.extraction
    assert extraction.outcome == "used"
    assert extraction.status_code == "used"
    assert extraction.model == model
    assert extraction.prompt_version == MODEL_ASSISTED_PROMPT_VERSION
    assert extraction.schema_version == MODEL_ASSISTED_SCHEMA_VERSION
    assert extraction.latency_ms >= 0
    assert extraction.usage is not None
    assert extraction.usage.input_tokens == 1000
    assert extraction.usage.cached_input_tokens == 200
    assert extraction.usage.output_tokens == 100
    assert extraction.usage.reasoning_tokens == 20
    assert extraction.estimated_cost_usd == 0.001065
    assert extraction.cost_estimate_status == "estimated_standard_rates"

    coaching = telemetry.coaching
    assert coaching.outcome == "used"
    assert coaching.status_code == "used"
    assert coaching.model == model
    assert coaching.prompt_version == COACHING_PROMPT_VERSION
    assert coaching.schema_version == COACHING_SCHEMA_VERSION
    assert coaching.usage is not None
    assert coaching.usage.input_tokens == 500
    assert coaching.usage.cached_input_tokens == 100
    assert coaching.usage.output_tokens == 80
    assert coaching.estimated_cost_usd == 0.0006675

    assert telemetry.total_input_tokens == 1500
    assert telemetry.total_cached_input_tokens == 300
    assert telemetry.total_output_tokens == 180
    assert telemetry.total_tokens == 1680
    assert telemetry.total_estimated_cost_usd == 0.0017325
    assert telemetry.cost_estimate_status == "estimated_standard_rates"
    assert telemetry.pricing_currency == "USD"
    assert "standard text-token rates" in telemetry.pricing_basis


def test_timeout_fallback_reports_latency_without_invented_usage_or_cost() -> None:
    with _provider_environment("gpt-5.4-mini"), patch.object(
        httpx,
        "Client",
        _timeout_client_factory,
    ):
        analysis = analyze_smart_fit(
            resume_text=RESUME_TEXT,
            job_description=JOB_DESCRIPTION,
            use_model_assisted=True,
        )

    telemetry = analysis.provider_telemetry
    assert telemetry is not None
    assert analysis.analysis_engine == "deterministic"
    assert analysis.model_assisted_status == "fallback_failed: provider_timeout"
    assert analysis.coaching_engine == "deterministic"
    assert analysis.coaching_status == "fallback_failed: coaching_timeout"
    assert telemetry.extraction.outcome == "fallback"
    assert telemetry.extraction.status_code == "provider_timeout"
    assert telemetry.extraction.usage is None
    assert telemetry.extraction.estimated_cost_usd is None
    assert telemetry.extraction.latency_ms >= 0
    assert telemetry.coaching.status_code == "coaching_timeout"
    assert telemetry.coaching.usage is None
    assert telemetry.total_estimated_cost_usd is None
    assert telemetry.cost_estimate_status == "unavailable"


def test_unknown_model_usage_is_reported_without_guessing_price() -> None:
    model = "unknown-model-for-telemetry-test"
    with _provider_environment(model), patch.object(
        httpx,
        "Client",
        _successful_client_factory(model),
    ):
        analysis = analyze_smart_fit(
            resume_text=RESUME_TEXT,
            job_description=JOB_DESCRIPTION,
            use_model_assisted=True,
        )

    telemetry = analysis.provider_telemetry
    assert telemetry is not None
    assert telemetry.extraction.usage is not None
    assert telemetry.extraction.estimated_cost_usd is None
    assert telemetry.extraction.cost_estimate_status == "pricing_unavailable"
    assert telemetry.coaching.usage is not None
    assert telemetry.coaching.estimated_cost_usd is None
    assert telemetry.coaching.cost_estimate_status == "pricing_unavailable"
    assert telemetry.total_estimated_cost_usd is None
    assert telemetry.cost_estimate_status == "unavailable"


def test_telemetry_json_contains_no_documents_prompts_or_credentials() -> None:
    analysis = analyze_smart_fit(
        resume_text=RESUME_TEXT,
        job_description=JOB_DESCRIPTION,
        use_model_assisted=False,
    )
    telemetry_json = json.dumps(
        analysis.provider_telemetry.model_dump(mode="json")
        if analysis.provider_telemetry
        else {}
    )

    assert "Built a Python FastAPI service" not in telemetry_json
    assert "Python and SQL are required" not in telemetry_json
    assert "You extract structured career-fit signals" not in telemetry_json
    assert "synthetic-telemetry-key" not in telemetry_json
