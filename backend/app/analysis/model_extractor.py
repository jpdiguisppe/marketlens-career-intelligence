"""Optional model-assisted extraction for Smart Fit.

This module is deliberately safe-by-default:
- disabled unless AI_ANALYSIS_ENABLED=true
- requires backend-only OPENAI_API_KEY and OPENAI_MODEL
- does not write resume/job text to the database
- redacts obvious contact details before provider transmission
- sends requests with store=false
- validates a versioned strict schema and quoted source grounding
- raises typed errors so the service can fall back to deterministic analysis
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from pydantic import ValidationError

from app.analysis.redaction import redact_sensitive_text
from app.analysis.semantic_contract import (
    MODEL_ASSISTED_SCHEMA_VERSION,
    ModelAssistedExtraction,
    ModelHardConstraintSignal,
    ModelJobRequirementSignal,
    ModelSkillSignal,
    ResumeEvidenceBasis,
    SemanticRequirementCategory,
    validate_extraction_grounding,
)

AI_ANALYSIS_ENABLED_ENV = "AI_ANALYSIS_ENABLED"
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_MODEL_ENV = "OPENAI_MODEL"
OPENAI_BASE_URL_ENV = "OPENAI_BASE_URL"
OPENAI_TIMEOUT_SECONDS_ENV = "OPENAI_TIMEOUT_SECONDS"

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_TIMEOUT_SECONDS = 12.0
MODEL_ASSISTED_PROMPT_VERSION = "8b.1"


class ModelAssistedUnavailable(RuntimeError):
    """Raised when model-assisted extraction is requested but not configured."""


class ModelAssistedExtractionError(RuntimeError):
    """Raised when a configured provider fails or returns invalid extraction output."""


def _env_enabled(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def is_model_assisted_configured() -> bool:
    return (
        _env_enabled(os.getenv(AI_ANALYSIS_ENABLED_ENV))
        and bool(os.getenv(OPENAI_API_KEY_ENV))
        and bool(os.getenv(OPENAI_MODEL_ENV))
    )


def _require_provider_config() -> tuple[str, str, str, float]:
    if not _env_enabled(os.getenv(AI_ANALYSIS_ENABLED_ENV)):
        raise ModelAssistedUnavailable("Model-assisted analysis is disabled for this deployment.")

    api_key = os.getenv(OPENAI_API_KEY_ENV)
    model = os.getenv(OPENAI_MODEL_ENV)
    base_url = os.getenv(OPENAI_BASE_URL_ENV, DEFAULT_OPENAI_BASE_URL).rstrip("/")
    timeout_raw = os.getenv(OPENAI_TIMEOUT_SECONDS_ENV)

    if not api_key:
        raise ModelAssistedUnavailable("OPENAI_API_KEY is not configured on the backend.")
    if not model:
        raise ModelAssistedUnavailable("OPENAI_MODEL is not configured on the backend.")

    try:
        timeout_seconds = float(timeout_raw) if timeout_raw else DEFAULT_TIMEOUT_SECONDS
    except ValueError as exc:
        raise ModelAssistedUnavailable("OPENAI_TIMEOUT_SECONDS must be a number.") from exc

    if timeout_seconds <= 0:
        raise ModelAssistedUnavailable("OPENAI_TIMEOUT_SECONDS must be greater than zero.")

    return api_key, model, base_url, timeout_seconds


def _structured_output_schema() -> dict[str, Any]:
    return ModelAssistedExtraction.model_json_schema()


_SYSTEM_PROMPT = f"""You extract structured career-fit signals from resume text and job descriptions.

Contract version: {MODEL_ASSISTED_SCHEMA_VERSION}
Prompt version: {MODEL_ASSISTED_PROMPT_VERSION}

Rules:
- Return schema_version exactly as {MODEL_ASSISTED_SCHEMA_VERSION!r}.
- Extract the smallest useful requirement or resume signal; do not write a fit score.
- Classify job signals as required qualification, preferred qualification, core responsibility, or supporting context.
- Classify semantic_category as tool_technology, credential_education, years_experience, responsibility, domain_knowledge, implied_capability, methodology_process, hard_constraint, or other.
- For resume skills, classify evidence_basis as direct_application, explicit_mention, academic_context, implied_by_tool, or related_experience.
- Do not invent skills, credentials, years of experience, responsibilities, or evidence that are not supported by the text.
- Preserve unknown technologies as named signals instead of dropping them.
- Never treat a technology mention as proof of a credential, years of experience, or domain expertise.
- Keep source_text to the smallest exact phrase copied from the corresponding document.
- Hard constraints include citizenship, clearance, degree, work authorization, years of experience, and travel. Do not guess whether the candidate meets them.
- Do not output names, emails, phone numbers, addresses, or other contact details.
- Return only schema-valid JSON with no extra fields.
"""


def _build_user_prompt(resume_text: str, job_description: str) -> str:
    redacted_resume_text = redact_sensitive_text(resume_text)
    redacted_job_description = redact_sensitive_text(job_description)

    return f"""Analyze this resume and job description for MarketLens Smart Fit.

Resume text:
{redacted_resume_text}

Job description:
{redacted_job_description}
"""


def _extract_output_text(response_json: dict[str, Any]) -> str:
    output_text = response_json.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    for output_item in response_json.get("output", []):
        if not isinstance(output_item, dict):
            continue
        for content_item in output_item.get("content", []):
            if not isinstance(content_item, dict):
                continue
            text = content_item.get("text")
            if isinstance(text, str) and text.strip():
                return text

    raise ModelAssistedExtractionError("Provider response did not include parseable output text.")


def _validate_provider_extraction(
    output_text: str,
    *,
    resume_text: str,
    job_description: str,
) -> ModelAssistedExtraction:
    try:
        extraction = ModelAssistedExtraction.model_validate_json(output_text)
    except ValidationError as exc:
        raise ModelAssistedExtractionError(
            "Provider output did not match the versioned extraction schema."
        ) from exc

    grounding_errors = validate_extraction_grounding(
        extraction,
        resume_text=resume_text,
        job_description=job_description,
    )
    if grounding_errors:
        detail = "; ".join(grounding_errors[:3])
        raise ModelAssistedExtractionError(
            f"Provider output included ungrounded source evidence: {detail}."
        )

    return extraction


def extract_model_assisted_signals(
    resume_text: str,
    job_description: str,
) -> ModelAssistedExtraction:
    """Call the configured provider and return grounded, schema-validated output."""

    api_key, model, base_url, timeout_seconds = _require_provider_config()

    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(resume_text, job_description)},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": f"marketlens_semantic_extraction_{MODEL_ASSISTED_SCHEMA_VERSION.replace('.', '_')}",
                "schema": _structured_output_schema(),
                "strict": True,
            }
        },
        "store": False,
    }

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(
                f"{base_url}/responses",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise ModelAssistedExtractionError("Provider request timed out.") from exc
    except httpx.HTTPStatusError as exc:
        raise ModelAssistedExtractionError(
            f"Provider returned HTTP {exc.response.status_code}."
        ) from exc
    except httpx.HTTPError as exc:
        raise ModelAssistedExtractionError("Provider request failed.") from exc

    try:
        response_json = response.json()
    except json.JSONDecodeError as exc:
        raise ModelAssistedExtractionError("Provider response was not valid JSON.") from exc

    output_text = _extract_output_text(response_json)
    return _validate_provider_extraction(
        output_text,
        resume_text=resume_text,
        job_description=job_description,
    )


__all__ = [
    "MODEL_ASSISTED_PROMPT_VERSION",
    "MODEL_ASSISTED_SCHEMA_VERSION",
    "ModelAssistedExtraction",
    "ModelAssistedExtractionError",
    "ModelAssistedUnavailable",
    "ModelHardConstraintSignal",
    "ModelJobRequirementSignal",
    "ModelSkillSignal",
    "ResumeEvidenceBasis",
    "SemanticRequirementCategory",
    "extract_model_assisted_signals",
    "is_model_assisted_configured",
]
