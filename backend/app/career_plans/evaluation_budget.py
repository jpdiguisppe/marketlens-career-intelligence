"""Documented task-level budgets for Career Plan agent evaluation."""

from __future__ import annotations

from app.career_plans.evaluation import (
    MODEL_CALL_BUDGET,
    MODEL_CONTEXT_BUDGET_BYTES,
    MODEL_ESTIMATED_COST_BUDGET_USD,
    MODEL_LATENCY_BUDGET_MS,
    MODEL_TOTAL_TOKEN_BUDGET,
)


def model_budget_failures(
    *,
    call_count: int,
    context_bytes: int,
    latency_ms: float,
    total_tokens: int,
    estimated_cost_usd: float | None,
) -> list[str]:
    failures: list[str] = []
    if call_count > MODEL_CALL_BUDGET:
        failures.append("model_call_budget_exceeded")
    if context_bytes > MODEL_CONTEXT_BUDGET_BYTES:
        failures.append("model_context_budget_exceeded")
    if latency_ms > MODEL_LATENCY_BUDGET_MS:
        failures.append("model_latency_budget_exceeded")
    if total_tokens > MODEL_TOTAL_TOKEN_BUDGET:
        failures.append("model_token_budget_exceeded")
    if (
        estimated_cost_usd is not None
        and estimated_cost_usd > MODEL_ESTIMATED_COST_BUDGET_USD
    ):
        failures.append("model_cost_budget_exceeded")
    return failures


__all__ = ["model_budget_failures"]
