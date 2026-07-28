"""Final cost-summary policy for provider telemetry."""

from __future__ import annotations

from app.analysis import provider_telemetry as _base
from app.analysis.schemas import SmartFitAnalysisResponse

_NO_PROVIDER_CALL_CODES = {
    "not_requested",
    "provider_unavailable",
    "coaching_unavailable",
    "insufficient_grounded_context",
}


def attach_provider_telemetry(
    analysis: SmartFitAnalysisResponse,
    *,
    use_model_assisted: bool,
) -> SmartFitAnalysisResponse:
    result = _base.attach_provider_telemetry(
        analysis,
        use_model_assisted=use_model_assisted,
    )
    telemetry = result.provider_telemetry
    if telemetry is None:
        return result

    stages = (telemetry.extraction, telemetry.coaching)
    attempted_stages = [
        stage
        for stage in stages
        if stage.requested and stage.status_code not in _NO_PROVIDER_CALL_CODES
    ]
    estimates = [
        stage.estimated_cost_usd
        for stage in attempted_stages
        if stage.estimated_cost_usd is not None
    ]

    if not attempted_stages:
        status = "not_applicable"
        total = None
    elif len(estimates) == len(attempted_stages):
        status = "estimated_standard_rates"
        total = round(sum(estimates), 8)
    elif estimates:
        status = "partial_estimate"
        total = round(sum(estimates), 8)
    else:
        status = "unavailable"
        total = None

    updated = telemetry.model_copy(
        update={
            "total_estimated_cost_usd": total,
            "cost_estimate_status": status,
        }
    )
    return result.model_copy(update={"provider_telemetry": updated})


begin_provider_telemetry = _base.begin_provider_telemetry
install_coaching_telemetry_patch = _base.install_coaching_telemetry_patch
install_extraction_telemetry_patch = _base.install_extraction_telemetry_patch
reset_provider_telemetry = _base.reset_provider_telemetry

__all__ = [
    "attach_provider_telemetry",
    "begin_provider_telemetry",
    "install_coaching_telemetry_patch",
    "install_extraction_telemetry_patch",
    "reset_provider_telemetry",
]
