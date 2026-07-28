"""Request-scoped, document-free provider telemetry for Milestone 8E.

This module observes the existing extraction and coaching provider boundaries. It
never records prompts, resume text, job text, provider bodies, credentials, or
raw exceptions. Token-based cost values are estimates using a dated standard-
rate catalog and are deliberately unavailable for unknown models.
"""

from __future__ import annotations

import os
from contextvars import ContextVar, Token
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from time import perf_counter
from typing import Any

from app.analysis.failure_status import safe_failure_code
from app.analysis.model_extractor import (
    MODEL_ASSISTED_PROMPT_VERSION,
    ModelAssistedExtractionError,
    ModelAssistedUnavailable,
)
from app.analysis.schemas import (
    COACHING_SCHEMA_VERSION,
    ProviderStageTelemetry,
    ProviderTelemetrySummary,
    ProviderTokenUsage,
    SmartFitAnalysisResponse,
)
from app.analysis.semantic_contract import MODEL_ASSISTED_SCHEMA_VERSION

TELEMETRY_VERSION = "8e.1"
PRICING_CATALOG_VERSION = "openai-standard-2026-07-28"
PRICING_CURRENCY = "USD"
PRICING_BASIS = (
    "Estimated from standard text-token rates; excludes regional, priority, "
    "batch, negotiated, and other pricing adjustments."
)

# Official standard token rates verified 2026-07-28. Values are USD per 1M
# tokens. Only the configured MarketLens model and its published snapshot are
# listed; unknown models intentionally receive no estimate.
_STANDARD_RATES_USD_PER_MILLION: dict[str, tuple[Decimal, Decimal, Decimal]] = {
    "gpt-5.4-mini": (Decimal("0.75"), Decimal("0.075"), Decimal("4.50")),
    "gpt-5.4-mini-2026-03-17": (
        Decimal("0.75"),
        Decimal("0.075"),
        Decimal("4.50"),
    ),
}


@dataclass(frozen=True)
class _ResponseMetadata:
    model: str | None
    usage: ProviderTokenUsage | None


@dataclass(frozen=True)
class _StageObservation:
    status_code: str
    model: str | None
    latency_ms: float
    usage: ProviderTokenUsage | None


_REQUEST_OBSERVATIONS: ContextVar[dict[str, _StageObservation] | None] = ContextVar(
    "marketlens_provider_telemetry_observations",
    default=None,
)
_ACTIVE_STAGE: ContextVar[str | None] = ContextVar(
    "marketlens_provider_telemetry_active_stage",
    default=None,
)
_ACTIVE_RESPONSE_METADATA: ContextVar[_ResponseMetadata | None] = ContextVar(
    "marketlens_provider_telemetry_response_metadata",
    default=None,
)


def _nonnegative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(value, 0)
    return 0


def _response_metadata(response_json: dict[str, Any]) -> _ResponseMetadata:
    model_value = response_json.get("model")
    model = model_value.strip() if isinstance(model_value, str) and model_value.strip() else None

    usage_value = response_json.get("usage")
    if not isinstance(usage_value, dict):
        return _ResponseMetadata(model=model, usage=None)

    input_details = usage_value.get("input_tokens_details")
    output_details = usage_value.get("output_tokens_details")
    input_tokens = _nonnegative_int(usage_value.get("input_tokens"))
    cached_input_tokens = _nonnegative_int(
        input_details.get("cached_tokens") if isinstance(input_details, dict) else 0
    )
    cached_input_tokens = min(cached_input_tokens, input_tokens)
    output_tokens = _nonnegative_int(usage_value.get("output_tokens"))
    reasoning_tokens = _nonnegative_int(
        output_details.get("reasoning_tokens") if isinstance(output_details, dict) else 0
    )
    total_tokens = _nonnegative_int(usage_value.get("total_tokens"))
    if total_tokens == 0 and (input_tokens or output_tokens):
        total_tokens = input_tokens + output_tokens

    return _ResponseMetadata(
        model=model,
        usage=ProviderTokenUsage(
            input_tokens=input_tokens,
            cached_input_tokens=cached_input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
            total_tokens=total_tokens,
        ),
    )


def _record_observation(
    stage: str,
    *,
    status_code: str,
    model: str | None,
    latency_ms: float,
    metadata: _ResponseMetadata | None,
) -> None:
    observations = _REQUEST_OBSERVATIONS.get()
    if observations is None:
        return

    resolved_model = (metadata.model if metadata else None) or model
    updated = dict(observations)
    updated[stage] = _StageObservation(
        status_code=safe_failure_code(status_code, fallback=f"{stage}_provider_error"),
        model=resolved_model,
        latency_ms=max(round(latency_ms, 3), 0.0),
        usage=metadata.usage if metadata else None,
    )
    _REQUEST_OBSERVATIONS.set(updated)


def _configured_model() -> str | None:
    model = os.getenv("OPENAI_MODEL")
    return model.strip() if model and model.strip() else None


def install_extraction_telemetry_patch() -> None:
    """Observe extraction without changing its result or exception behavior."""

    import app.analysis.model_extractor as model_extractor
    import app.analysis.service as service

    if getattr(service, "_provider_extraction_telemetry_installed", False):
        return

    original_output_text = model_extractor._extract_output_text
    original_extract = service.extract_model_assisted_signals

    def observed_output_text(response_json: dict[str, Any]) -> str:
        if _ACTIVE_STAGE.get() is not None:
            _ACTIVE_RESPONSE_METADATA.set(_response_metadata(response_json))
        return original_output_text(response_json)

    def observed_extract(*args: Any, **kwargs: Any):
        started = perf_counter()
        stage_token = _ACTIVE_STAGE.set("extraction")
        metadata_token = _ACTIVE_RESPONSE_METADATA.set(None)
        model = _configured_model()
        try:
            result = original_extract(*args, **kwargs)
        except ModelAssistedUnavailable:
            _record_observation(
                "extraction",
                status_code="provider_unavailable",
                model=model,
                latency_ms=(perf_counter() - started) * 1000,
                metadata=_ACTIVE_RESPONSE_METADATA.get(),
            )
            raise
        except ModelAssistedExtractionError as exc:
            _record_observation(
                "extraction",
                status_code=exc.code,
                model=model,
                latency_ms=(perf_counter() - started) * 1000,
                metadata=_ACTIVE_RESPONSE_METADATA.get(),
            )
            raise
        else:
            _record_observation(
                "extraction",
                status_code="used",
                model=model,
                latency_ms=(perf_counter() - started) * 1000,
                metadata=_ACTIVE_RESPONSE_METADATA.get(),
            )
            return result
        finally:
            _ACTIVE_RESPONSE_METADATA.reset(metadata_token)
            _ACTIVE_STAGE.reset(stage_token)

    model_extractor._extract_output_text = observed_output_text
    service.extract_model_assisted_signals = observed_extract
    service._provider_extraction_telemetry_installed = True


def install_coaching_telemetry_patch() -> None:
    """Observe coaching after all existing validation/failure patches are installed."""

    import app.analysis.model_extractor as model_extractor
    import app.analysis.personalized_coaching as coaching

    if getattr(coaching, "_provider_coaching_telemetry_installed", False):
        return

    # Coaching imports this helper by value. Point it at the extraction telemetry
    # wrapper so the same safe response metadata parser serves both stages.
    coaching._extract_output_text = model_extractor._extract_output_text
    original_request = coaching._request_personalized_coaching

    def observed_request(*args: Any, **kwargs: Any):
        started = perf_counter()
        stage_token = _ACTIVE_STAGE.set("coaching")
        metadata_token = _ACTIVE_RESPONSE_METADATA.set(None)
        model = _configured_model()
        try:
            result = original_request(*args, **kwargs)
        except ModelAssistedUnavailable:
            _record_observation(
                "coaching",
                status_code="coaching_unavailable",
                model=model,
                latency_ms=(perf_counter() - started) * 1000,
                metadata=_ACTIVE_RESPONSE_METADATA.get(),
            )
            raise
        except coaching.PersonalizedCoachingError as exc:
            _record_observation(
                "coaching",
                status_code=exc.code,
                model=model,
                latency_ms=(perf_counter() - started) * 1000,
                metadata=_ACTIVE_RESPONSE_METADATA.get(),
            )
            raise
        else:
            _record_observation(
                "coaching",
                status_code="used",
                model=model,
                latency_ms=(perf_counter() - started) * 1000,
                metadata=_ACTIVE_RESPONSE_METADATA.get(),
            )
            return result
        finally:
            _ACTIVE_RESPONSE_METADATA.reset(metadata_token)
            _ACTIVE_STAGE.reset(stage_token)

    coaching._request_personalized_coaching = observed_request
    coaching._provider_coaching_telemetry_installed = True


def begin_provider_telemetry() -> Token[dict[str, _StageObservation] | None]:
    return _REQUEST_OBSERVATIONS.set({})


def reset_provider_telemetry(
    token: Token[dict[str, _StageObservation] | None],
) -> None:
    _REQUEST_OBSERVATIONS.reset(token)


def _status_code_from_public_status(status: str, *, stage: str) -> str:
    normalized = status.strip().lower()
    if normalized in {"used", "not_requested"}:
        return normalized
    if normalized.startswith("fallback_unavailable"):
        return f"{stage}_unavailable"
    if normalized.startswith("fallback_insufficient_grounded_context"):
        return "insufficient_grounded_context"
    if ":" in normalized:
        candidate = normalized.split(":", 1)[1].strip()
        return safe_failure_code(candidate, fallback=f"{stage}_provider_error")
    return safe_failure_code(normalized, fallback=f"{stage}_provider_error")


def _outcome(*, requested: bool, status_code: str) -> str:
    if not requested or status_code == "not_requested":
        return "not_requested"
    if status_code == "used":
        return "used"
    if status_code.endswith("_unavailable"):
        return "unavailable"
    return "fallback"


def _estimate_cost(
    *,
    model: str | None,
    usage: ProviderTokenUsage | None,
) -> tuple[float | None, str]:
    if usage is None:
        return None, "usage_unavailable"
    if model is None:
        return None, "model_unavailable"
    rates = _STANDARD_RATES_USD_PER_MILLION.get(model)
    if rates is None:
        return None, "pricing_unavailable"

    input_rate, cached_rate, output_rate = rates
    uncached_input_tokens = max(usage.input_tokens - usage.cached_input_tokens, 0)
    cost = (
        Decimal(uncached_input_tokens) * input_rate
        + Decimal(usage.cached_input_tokens) * cached_rate
        + Decimal(usage.output_tokens) * output_rate
    ) / Decimal(1_000_000)
    rounded = cost.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
    return float(rounded), "estimated_standard_rates"


def _stage_telemetry(
    *,
    stage: str,
    requested: bool,
    public_status: str,
    observation: _StageObservation | None,
    prompt_version: str,
    schema_version: str,
) -> ProviderStageTelemetry:
    status_code = (
        observation.status_code
        if observation is not None
        else _status_code_from_public_status(public_status, stage=stage)
    )
    model = observation.model if observation else (_configured_model() if requested else None)
    usage = observation.usage if observation else None
    estimated_cost, estimate_status = _estimate_cost(model=model, usage=usage)
    return ProviderStageTelemetry(
        stage=stage,
        requested=requested,
        outcome=_outcome(requested=requested, status_code=status_code),
        status_code=status_code,
        model=model,
        prompt_version=prompt_version,
        schema_version=schema_version,
        latency_ms=observation.latency_ms if observation else 0.0,
        usage=usage,
        estimated_cost_usd=estimated_cost,
        cost_estimate_status=estimate_status if requested else "not_applicable",
    )


def attach_provider_telemetry(
    analysis: SmartFitAnalysisResponse,
    *,
    use_model_assisted: bool,
) -> SmartFitAnalysisResponse:
    observations = _REQUEST_OBSERVATIONS.get() or {}

    # Imported lazily because the coaching module is installed after the base
    # extraction pipeline is captured.
    from app.analysis.personalized_coaching import COACHING_PROMPT_VERSION

    extraction = _stage_telemetry(
        stage="semantic_extraction",
        requested=use_model_assisted,
        public_status=analysis.model_assisted_status,
        observation=observations.get("extraction"),
        prompt_version=MODEL_ASSISTED_PROMPT_VERSION,
        schema_version=MODEL_ASSISTED_SCHEMA_VERSION,
    )
    coaching = _stage_telemetry(
        stage="personalized_coaching",
        requested=use_model_assisted,
        public_status=analysis.coaching_status,
        observation=observations.get("coaching"),
        prompt_version=COACHING_PROMPT_VERSION,
        schema_version=COACHING_SCHEMA_VERSION,
    )

    stages = (extraction, coaching)
    estimated_costs = [
        stage.estimated_cost_usd
        for stage in stages
        if stage.estimated_cost_usd is not None
    ]
    provider_attempted = [stage for stage in stages if stage.requested]
    fully_estimated = bool(provider_attempted) and all(
        stage.estimated_cost_usd is not None
        for stage in provider_attempted
        if stage.outcome == "used"
    ) and all(
        stage.cost_estimate_status != "pricing_unavailable"
        for stage in provider_attempted
    )

    if not provider_attempted:
        total_cost_status = "not_applicable"
    elif fully_estimated and estimated_costs:
        total_cost_status = "estimated_standard_rates"
    elif estimated_costs:
        total_cost_status = "partial_estimate"
    else:
        total_cost_status = "unavailable"

    total_estimated_cost = (
        round(sum(estimated_costs), 8) if estimated_costs else None
    )
    summary = ProviderTelemetrySummary(
        telemetry_version=TELEMETRY_VERSION,
        pricing_catalog_version=PRICING_CATALOG_VERSION,
        pricing_currency=PRICING_CURRENCY,
        pricing_basis=PRICING_BASIS,
        extraction=extraction,
        coaching=coaching,
        total_provider_latency_ms=round(
            extraction.latency_ms + coaching.latency_ms,
            3,
        ),
        total_input_tokens=sum(
            stage.usage.input_tokens for stage in stages if stage.usage
        ),
        total_cached_input_tokens=sum(
            stage.usage.cached_input_tokens for stage in stages if stage.usage
        ),
        total_output_tokens=sum(
            stage.usage.output_tokens for stage in stages if stage.usage
        ),
        total_tokens=sum(
            stage.usage.total_tokens for stage in stages if stage.usage
        ),
        total_estimated_cost_usd=total_estimated_cost,
        cost_estimate_status=total_cost_status,
    )
    return analysis.model_copy(update={"provider_telemetry": summary})


__all__ = [
    "PRICING_BASIS",
    "PRICING_CATALOG_VERSION",
    "PRICING_CURRENCY",
    "TELEMETRY_VERSION",
    "attach_provider_telemetry",
    "begin_provider_telemetry",
    "install_coaching_telemetry_patch",
    "install_extraction_telemetry_patch",
    "reset_provider_telemetry",
]
