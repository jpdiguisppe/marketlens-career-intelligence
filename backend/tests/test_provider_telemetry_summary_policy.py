from __future__ import annotations

from app.analysis import analyze_smart_fit
from app.analysis import provider_telemetry_summary_policy as policy
from app.analysis.schemas import (
    ProviderStageTelemetry,
    ProviderTelemetrySummary,
    ProviderTokenUsage,
)

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


def test_successful_extraction_and_coaching_timeout_is_partial_estimate(
    monkeypatch,
) -> None:
    baseline = analyze_smart_fit(
        resume_text=RESUME_TEXT,
        job_description=JOB_DESCRIPTION,
        use_model_assisted=False,
    )
    extraction = ProviderStageTelemetry(
        stage="semantic_extraction",
        requested=True,
        outcome="used",
        status_code="used",
        model="gpt-5.4-mini",
        prompt_version="8b.1",
        schema_version="8b.1",
        latency_ms=125.0,
        usage=ProviderTokenUsage(
            input_tokens=1000,
            cached_input_tokens=200,
            output_tokens=100,
            reasoning_tokens=20,
            total_tokens=1100,
        ),
        estimated_cost_usd=0.001065,
        cost_estimate_status="estimated_standard_rates",
    )
    coaching = ProviderStageTelemetry(
        stage="personalized_coaching",
        requested=True,
        outcome="fallback",
        status_code="coaching_timeout",
        model="gpt-5.4-mini",
        prompt_version="8d.1",
        schema_version="8d.1",
        latency_ms=1000.0,
        usage=None,
        estimated_cost_usd=None,
        cost_estimate_status="usage_unavailable",
    )
    staged_summary = ProviderTelemetrySummary(
        telemetry_version="8e.1",
        pricing_catalog_version="openai-standard-2026-07-28",
        pricing_currency="USD",
        pricing_basis="Estimated from standard text-token rates.",
        extraction=extraction,
        coaching=coaching,
        total_provider_latency_ms=1125.0,
        total_input_tokens=1000,
        total_cached_input_tokens=200,
        total_output_tokens=100,
        total_tokens=1100,
        total_estimated_cost_usd=0.001065,
        cost_estimate_status="estimated_standard_rates",
    )
    staged_analysis = baseline.model_copy(
        update={"provider_telemetry": staged_summary}
    )

    monkeypatch.setattr(
        policy._base,
        "attach_provider_telemetry",
        lambda analysis, *, use_model_assisted: staged_analysis,
    )

    result = policy.attach_provider_telemetry(
        baseline,
        use_model_assisted=True,
    )
    telemetry = result.provider_telemetry

    assert telemetry is not None
    assert telemetry.total_estimated_cost_usd == 0.001065
    assert telemetry.cost_estimate_status == "partial_estimate"
