"""Optional model-assisted extraction for Smart Fit.

This module is deliberately safe-by-default:
- disabled unless AI_ANALYSIS_ENABLED=true
- requires backend-only OPENAI_API_KEY and OPENAI_MODEL
- does not write resume/job text to the database
- sends requests with store=false
- raises typed errors so the service can fall back to deterministic analysis
"""

from __future__ import annotations

import json
import os
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.analysis.schemas import EvidenceStatus, RequirementType

AI_ANALYSIS_ENABLED_ENV = "AI_ANALYSIS_ENABLED"
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_MODEL_ENV = "OPENAI_MODEL"
OPENAI_BASE_URL_ENV = "OPENAI_BASE_URL"
OPENAI_TIMEOUT_SECONDS_ENV = "OPENAI_TIMEOUT_SECONDS"

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_TIMEOUT_SECONDS = 12.0


class ModelAssistedUnavailable(RuntimeError):
    """Raised when model-assisted extraction is requested but not configured."""


class ModelAssistedExtractionError(RuntimeError):
    """Raised when a configured provider fails or returns invalid extraction output."""


class ModelSkillSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    category: str | None = Field(default=None, max_length=80)
    evidence_status: EvidenceStatus
    confidence: float = Field(ge=0.0, le=1.0)
    context: str | None = Field(default=None, max_length=120)
    source_text: str = Field(min_length=1, max_length=500)


class ModelJobRequirementSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill: str = Field(min_length=1, max_length=100)
    category: str | None = Field(default=None, max_length=80)
    requirement_type: RequirementType
    weight: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    context: str | None = Field(default=None, max_length=120)
    source_text: str = Field(min_length=1, max_length=500)


class ModelHardConstraintSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Literal[
        "citizenship",
        "security_clearance",
        "degree",
        "work_authorization",
        "years_experience",
        "travel",
        "other",
    ]
    requirement: str = Field(min_length=1, max_length=300)
    source_text: str = Field(min_length=1, max_length=500)
    confidence: float = Field(ge=0.0, le=1.0)


class ModelAssistedExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resume_skills: list[ModelSkillSignal] = Field(default_factory=list)
    job_requirements: list[ModelJobRequirementSignal] = Field(default_factory=list)
    hard_constraints: list[ModelHardConstraintSignal] = Field(default_factory=list)
    unknown_resume_skills: list[str] = Field(default_factory=list)
    unknown_job_skills: list[str] = Field(default_factory=list)
    uncertainty_notes: list[str] = Field(default_factory=list)


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

    return api_key, model, base_url, timeout_seconds


def _structured_output_schema() -> dict[str, Any]:
    return ModelAssistedExtraction.model_json_schema()


_SYSTEM_PROMPT = """You extract structured career-fit signals from resume text and job descriptions.

Rules:
- Extract skills, tools, platforms, frameworks, methodologies, and hard constraints.
- Do not invent skills or experience that are not supported by the text.
- Preserve unknown technologies as skill names instead of dropping them.
- Separate direct evidence from mentioned, academic, implied, or related evidence.
- Distinguish context: frontend, backend, database, devops, systems, cloud, data, AI/ML, productivity tools, academic, IT support, security, process.
- Keep source_text short and quote only the smallest useful phrase.
- Do not output names, emails, phone numbers, addresses, or other contact details.
- Return only schema-valid JSON.
"""


def _build_user_prompt(resume_text: str, job_description: str) -> str:
    return f"""Analyze this resume and job description for MarketLens Smart Fit.

Resume text:
{resume_text}

Job description:
{job_description}
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


def extract_model_assisted_signals(resume_text: str, job_description: str) -> ModelAssistedExtraction:
    """Call the configured model provider and return schema-validated extraction output."""

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
                "name": "marketlens_model_assisted_extraction",
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
    try:
        return ModelAssistedExtraction.model_validate_json(output_text)
    except ValidationError as exc:
        raise ModelAssistedExtractionError("Provider output did not match the extraction schema.") from exc
