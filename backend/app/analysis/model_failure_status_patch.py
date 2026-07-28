"""Expose safe extraction failure codes without changing deterministic output."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

import app.analysis.service as _service
from app.analysis.failure_status import fallback_failed_status
from app.analysis.model_extractor import ModelAssistedExtractionError
from app.analysis.schemas import SmartFitAnalysisResponse

_LAST_EXTRACTION_FAILURE_CODE: ContextVar[str | None] = ContextVar(
    "marketlens_last_extraction_failure_code",
    default=None,
)


def install_model_failure_status_patch() -> None:
    if getattr(_service, "_model_failure_status_patch_installed", False):
        return

    original_extract = _service.extract_model_assisted_signals
    original_analyze = _service.analyze_smart_fit

    def tracked_extract(*args: Any, **kwargs: Any):
        try:
            return original_extract(*args, **kwargs)
        except ModelAssistedExtractionError as exc:
            _LAST_EXTRACTION_FAILURE_CODE.set(exc.code)
            raise

    def analyze_with_failure_code(*args: Any, **kwargs: Any) -> SmartFitAnalysisResponse:
        token = _LAST_EXTRACTION_FAILURE_CODE.set(None)
        try:
            analysis = original_analyze(*args, **kwargs)
            code = _LAST_EXTRACTION_FAILURE_CODE.get()
            if code and analysis.model_assisted_status.startswith("fallback_failed:"):
                return analysis.model_copy(
                    update={
                        "model_assisted_status": fallback_failed_status(
                            code,
                            fallback="provider_error",
                        )
                    }
                )
            return analysis
        finally:
            _LAST_EXTRACTION_FAILURE_CODE.reset(token)

    _service.extract_model_assisted_signals = tracked_extract
    _service.analyze_smart_fit = analyze_with_failure_code
    _service._model_failure_status_patch_installed = True


__all__ = ["install_model_failure_status_patch"]
