"""Safe public status formatting for optional provider failures."""

from __future__ import annotations

import re

_SAFE_FAILURE_CODE = re.compile(r"^[a-z][a-z0-9_]{1,79}$")


def safe_failure_code(code: str | None, *, fallback: str) -> str:
    candidate = (code or "").strip().lower()
    if _SAFE_FAILURE_CODE.fullmatch(candidate):
        return candidate
    return fallback


def fallback_failed_status(code: str | None, *, fallback: str) -> str:
    """Return a stable status containing only a bounded machine-readable code."""

    return f"fallback_failed: {safe_failure_code(code, fallback=fallback)}"


__all__ = ["fallback_failed_status", "safe_failure_code"]
