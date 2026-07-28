"""Centralized operational log safety for MarketLens.

The filter removes configured credentials, bearer tokens, credential-bearing
URLs, obvious provider keys, request-scoped document lines, control characters,
and exception text before a record reaches any handler. It preserves bounded
machine codes and exception type names for operations without emitting raw
tracebacks or sensitive values.
"""

from __future__ import annotations

import logging
import os
import re
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

REDACTED = "[REDACTED]"
MAX_LOG_VALUE_LENGTH = 240

_SENSITIVE_ENVIRONMENT_VARIABLES = (
    "ADMIN_API_KEY",
    "AUTH_DEV_BEARER_TOKEN",
    "CLERK_SECRET_KEY",
    "DATABASE_URL",
    "OPENAI_API_KEY",
)
_SENSITIVE_VALUES: ContextVar[tuple[str, ...]] = ContextVar(
    "marketlens_sensitive_log_values",
    default=(),
)
_LOG_FACTORY_INSTALLED = False
_ORIGINAL_LOG_RECORD_FACTORY = logging.getLogRecordFactory()

_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]+")
_LINE_BREAKS = re.compile(r"[\r\n\t]+")
_BEARER_TOKEN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}")
_CREDENTIAL_URL = re.compile(
    r"(?i)\b(postgres(?:ql)?|mysql|mariadb|redis|mongodb(?:\+srv)?)://"
    r"([^\s:/@]+):([^\s@]+)@"
)
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(OPENAI_API_KEY|ADMIN_API_KEY|AUTH_DEV_BEARER_TOKEN|"
    r"CLERK_SECRET_KEY|DATABASE_URL)\s*[=:]\s*([^\s,;]+)"
)
_HIGH_CONFIDENCE_TOKENS = (
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)
_SAFE_FIELD_NAME = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_SAFE_EVENT_NAME = re.compile(r"^[a-z][a-z0-9_.]{0,95}$")


def _request_variants(values: tuple[str, ...]) -> tuple[str, ...]:
    variants: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        candidate = value.strip()
        if len(candidate) >= 8:
            variants.add(candidate)
        for line in candidate.splitlines()[:120]:
            cleaned = line.strip()
            if len(cleaned) >= 12:
                variants.add(cleaned[:1000])
    return tuple(sorted(variants, key=len, reverse=True))


def configured_sensitive_values() -> tuple[str, ...]:
    return tuple(
        value
        for name in _SENSITIVE_ENVIRONMENT_VARIABLES
        if (value := os.getenv(name))
    )


def sanitize_log_value(value: Any) -> str:
    """Return a bounded, single-line value safe for operational logs."""

    text = str(value)
    for sensitive in _SENSITIVE_VALUES.get():
        if sensitive:
            text = text.replace(sensitive, REDACTED)

    text = _BEARER_TOKEN.sub(f"Bearer {REDACTED}", text)
    text = _CREDENTIAL_URL.sub(
        lambda match: f"{match.group(1)}://{REDACTED}:{REDACTED}@",
        text,
    )
    text = _SECRET_ASSIGNMENT.sub(
        lambda match: f"{match.group(1)}={REDACTED}",
        text,
    )
    for pattern in _HIGH_CONFIDENCE_TOKENS:
        text = pattern.sub(REDACTED, text)

    text = _LINE_BREAKS.sub(" ", text)
    text = _CONTROL_CHARACTERS.sub("", text)
    text = " ".join(text.split())
    if len(text) > MAX_LOG_VALUE_LENGTH:
        return f"{text[: MAX_LOG_VALUE_LENGTH - 3]}..."
    return text


@contextmanager
def sensitive_log_context(*values: str) -> Iterator[None]:
    """Redact supplied request documents and configured credentials in this context."""

    inherited = _SENSITIVE_VALUES.get()
    combined = _request_variants(
        tuple(inherited) + configured_sensitive_values() + tuple(values)
    )
    token = _SENSITIVE_VALUES.set(combined)
    try:
        yield
    finally:
        _SENSITIVE_VALUES.reset(token)


def safe_log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    **fields: Any,
) -> None:
    """Write one bounded structured event using safe field names and values."""

    event_name = event if _SAFE_EVENT_NAME.fullmatch(event) else "invalid_event_name"
    rendered_fields = [
        f"{name}={sanitize_log_value(value)}"
        for name, value in sorted(fields.items())
        if _SAFE_FIELD_NAME.fullmatch(name)
    ]
    message = " ".join([event_name, *rendered_fields]).strip()
    logger.log(level, message)


def _safe_log_record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
    record = _ORIGINAL_LOG_RECORD_FACTORY(*args, **kwargs)
    try:
        message = sanitize_log_value(record.getMessage())
    except Exception:
        message = "log_message_unavailable"

    if record.exc_info:
        exception_type = getattr(record.exc_info[0], "__name__", "Exception")
        message = f"{message} exception_type={sanitize_log_value(exception_type)}"
        record.exc_info = None
        record.exc_text = None

    record.msg = message
    record.args = ()
    return record


def install_safe_log_record_factory() -> None:
    """Install one process-wide filter that also protects future handlers."""

    global _LOG_FACTORY_INSTALLED
    if _LOG_FACTORY_INSTALLED:
        return
    logging.setLogRecordFactory(_safe_log_record_factory)
    _LOG_FACTORY_INSTALLED = True


__all__ = [
    "REDACTED",
    "configured_sensitive_values",
    "install_safe_log_record_factory",
    "safe_log_event",
    "sanitize_log_value",
    "sensitive_log_context",
]
