"""Safe default HTTP error handling for the MarketLens FastAPI application."""

from __future__ import annotations

import logging
from typing import Any

import fastapi
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.safe_logging import safe_log_event, sanitize_log_value

_logger = logging.getLogger(__name__)
_INSTALLED = False
_ORIGINAL_FASTAPI = fastapi.FastAPI


def _safe_location(location: Any) -> list[str | int]:
    if not isinstance(location, (list, tuple)):
        return []
    result: list[str | int] = []
    for part in location[:8]:
        if isinstance(part, int):
            result.append(part)
        elif isinstance(part, str):
            result.append(sanitize_log_value(part)[:80])
    return result


async def safe_request_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return validation metadata without echoing rejected request values."""

    errors = [
        {
            "type": sanitize_log_value(error.get("type", "validation_error"))[:80],
            "location": _safe_location(error.get("loc")),
        }
        for error in exc.errors()[:20]
    ]
    safe_log_event(
        _logger,
        logging.INFO,
        "http.request_validation_failed",
        method=request.method,
        path=request.url.path,
        error_count=len(errors),
    )
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Request validation failed.",
            "errors": errors,
        },
    )


async def safe_unhandled_exception(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Log only bounded metadata and return no internal exception details."""

    safe_log_event(
        _logger,
        logging.ERROR,
        "http.unhandled_exception",
        method=request.method,
        path=request.url.path,
        exception_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal service error occurred."},
    )


class SafeFastAPI(_ORIGINAL_FASTAPI):
    """FastAPI application with MarketLens-safe default exception handlers."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        exception_handlers = dict(kwargs.pop("exception_handlers", {}) or {})
        exception_handlers.setdefault(
            RequestValidationError,
            safe_request_validation_error,
        )
        exception_handlers.setdefault(Exception, safe_unhandled_exception)
        super().__init__(
            *args,
            exception_handlers=exception_handlers,
            **kwargs,
        )


def install_safe_fastapi_defaults() -> None:
    """Ensure ``from fastapi import FastAPI`` receives the safe subclass."""

    global _INSTALLED
    if _INSTALLED:
        return
    fastapi.FastAPI = SafeFastAPI
    _INSTALLED = True


__all__ = [
    "SafeFastAPI",
    "install_safe_fastapi_defaults",
    "safe_request_validation_error",
    "safe_unhandled_exception",
]
