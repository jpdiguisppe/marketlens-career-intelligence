from __future__ import annotations

import io
import logging

from uvicorn.logging import AccessFormatter

from app.safe_logging import (
    REDACTED,
    safe_log_event,
    sanitize_log_value,
    sensitive_log_context,
)


def _capture_logger(name: str) -> tuple[logging.Logger, io.StringIO, logging.Handler]:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger(name)
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    return logger, stream, handler


def test_sensitive_context_redacts_documents_credentials_and_exception_text(
    monkeypatch,
) -> None:
    resume_line = "CANARY RESUME: built a confidential medical scheduling system"
    job_line = "CANARY JOB: requires private clearance details and internal IDs"
    api_key = "audit-openai-secret-value-123456"
    bearer = "audit-bearer-token-value-123456"
    database_url = "postgresql://audit-user:" + "audit-password" + "@db.internal/marketlens"
    provider_body = "CANARY PROVIDER BODY: private rejected output"

    monkeypatch.setenv("OPENAI_API_KEY", api_key)
    monkeypatch.setenv("AUTH_DEV_BEARER_TOKEN", bearer)
    monkeypatch.setenv("DATABASE_URL", database_url)

    logger, stream, handler = _capture_logger("marketlens.tests.safe_logging")
    try:
        with sensitive_log_context(resume_line, job_line, provider_body):
            try:
                raise RuntimeError(
                    f"{provider_body}; Authorization: Bearer {bearer}; database={database_url}"
                )
            except RuntimeError:
                logger.exception(
                    "analysis failed resume=%s job=%s OPENAI_API_KEY=%s",
                    resume_line,
                    job_line,
                    api_key,
                )
    finally:
        handler.flush()
        logger.handlers = []

    output = stream.getvalue()
    for forbidden in (
        resume_line,
        job_line,
        api_key,
        bearer,
        database_url,
        "audit-password",
        provider_body,
        "RuntimeError:",
    ):
        assert forbidden not in output
    assert REDACTED in output
    assert "exception_type=RuntimeError" in output


def test_safe_log_event_bounds_fields_and_prevents_log_injection() -> None:
    logger, stream, handler = _capture_logger("marketlens.tests.safe_event")
    try:
        safe_log_event(
            logger,
            logging.WARNING,
            "provider.failure",
            code="provider_http_429",
            request_id="request-123\r\nFORGED_LOG=admin Bearer " + "token-value-123456789",
        )
    finally:
        handler.flush()
        logger.handlers = []

    output = stream.getvalue()
    assert output.count("\n") == 1
    assert "FORGED_LOG=admin" in output
    assert "token-value-123456789" not in output
    assert "Bearer [REDACTED]" in output
    assert "provider.failure" in output
    assert "provider_http_429" in output


def test_high_confidence_token_and_credential_url_redaction() -> None:
    openai_token = "sk-" + "A" * 28
    github_token = "ghp_" + "B" * 36
    database_url = "postgresql://user:" + "password" + "@localhost/database"

    sanitized = sanitize_log_value(
        f"{openai_token} {github_token} {database_url}"
    )

    assert openai_token not in sanitized
    assert github_token not in sanitized
    assert "password" not in sanitized
    assert sanitized.count(REDACTED) >= 3


def test_safe_log_factory_preserves_uvicorn_access_formatter_contract() -> None:
    logger, stream, handler = _capture_logger("uvicorn.access")
    handler.setFormatter(
        AccessFormatter('%(client_addr)s - "%(request_line)s" %(status_code)s')
    )

    try:
        logger.info(
            '%s - "%s %s HTTP/%s" %d',
            "127.0.0.1:43120",
            "GET",
            "/health?check=runtime",
            "1.1",
            200,
        )
    finally:
        handler.flush()
        logger.handlers = []

    output = stream.getvalue()
    assert '127.0.0.1:43120 - "GET /health?check=runtime HTTP/1.1" 200' in output
