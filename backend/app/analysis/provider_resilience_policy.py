"""Telemetry compatibility policy for provider-resilience evaluation."""

from __future__ import annotations

from app.analysis import provider_resilience as _base

# Provider resilience proves that scored analysis content survives failures.
# Telemetry has its own invariants and is intentionally excluded from that
# content fingerprint.
_base._METADATA_FIELDS.add("provider_telemetry")

COACHING_FAILURES = _base.COACHING_FAILURES
EXTRACTION_FAILURES = _base.EXTRACTION_FAILURES
ProviderScenario = _base.ProviderScenario
evaluate_provider_resilience = _base.evaluate_provider_resilience
format_provider_resilience_report = _base.format_provider_resilience_report

__all__ = [
    "COACHING_FAILURES",
    "EXTRACTION_FAILURES",
    "ProviderScenario",
    "evaluate_provider_resilience",
    "format_provider_resilience_report",
]
