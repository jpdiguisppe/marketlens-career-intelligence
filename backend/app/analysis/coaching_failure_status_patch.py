"""Expose safe coaching failure codes after all coaching validators run."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

import app.analysis.personalized_coaching as _coaching
from app.analysis.failure_status import fallback_failed_status
from app.analysis.schemas import SmartFitAnalysisResponse

_LAST_COACHING_FAILURE_CODE: ContextVar[str | None] = ContextVar(
    "marketlens_last_coaching_failure_code",
    default=None,
)


def install_coaching_failure_status_patch() -> None:
    if getattr(_coaching, "_coaching_failure_status_patch_installed", False):
        return

    original_request = _coaching._request_personalized_coaching
    original_apply = _coaching.apply_personalized_coaching

    def tracked_request(*args: Any, **kwargs: Any):
        try:
            return original_request(*args, **kwargs)
        except _coaching.PersonalizedCoachingError as exc:
            _LAST_COACHING_FAILURE_CODE.set(exc.code)
            raise

    def apply_with_failure_code(
        analysis: SmartFitAnalysisResponse,
        *,
        use_model_assisted: bool,
    ) -> SmartFitAnalysisResponse:
        token = _LAST_COACHING_FAILURE_CODE.set(None)
        try:
            result = original_apply(
                analysis,
                use_model_assisted=use_model_assisted,
            )
            code = _LAST_COACHING_FAILURE_CODE.get()
            if code and result.coaching_status.startswith("fallback_failed:"):
                return result.model_copy(
                    update={
                        "coaching_status": fallback_failed_status(
                            code,
                            fallback="coaching_provider_error",
                        )
                    }
                )
            return result
        finally:
            _LAST_COACHING_FAILURE_CODE.reset(token)

    _coaching._request_personalized_coaching = tracked_request
    _coaching.apply_personalized_coaching = apply_with_failure_code
    _coaching._coaching_failure_status_patch_installed = True


__all__ = ["install_coaching_failure_status_patch"]
