"""Versioned structured-output contract for optional semantic Smart Fit extraction.

The provider may classify and surface signals, but it is not allowed to assign
final fit scores or claim stronger resume evidence than MarketLens can verify.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.analysis.redaction import redact_sensitive_text
from app.analysis.schemas import EvidenceStatus, RequirementType

MODEL_ASSISTED_SCHEMA_VERSION = "8b.1"


class SemanticRequirementCategory(str, Enum):
    TOOL_TECHNOLOGY = "tool_technology"
    CREDENTIAL_EDUCATION = "credential_education"
    YEARS_EXPERIENCE = "years_experience"
    RESPONSIBILITY = "responsibility"
    DOMAIN_KNOWLEDGE = "domain_knowledge"
    IMPLIED_CAPABILITY = "implied_capability"
    METHODOLOGY_PROCESS = "methodology_process"
    HARD_CONSTRAINT = "hard_constraint"
    OTHER = "other"


class ResumeEvidenceBasis(str, Enum):
    DIRECT_APPLICATION = "direct_application"
    EXPLICIT_MENTION = "explicit_mention"
    ACADEMIC_CONTEXT = "academic_context"
    IMPLIED_BY_TOOL = "implied_by_tool"
    RELATED_EXPERIENCE = "related_experience"


class ModelSkillSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    category: str | None = Field(default=None, max_length=80)
    semantic_category: SemanticRequirementCategory
    evidence_basis: ResumeEvidenceBasis
    evidence_status: EvidenceStatus
    confidence: float = Field(ge=0.0, le=1.0)
    context: str | None = Field(default=None, max_length=120)
    source_text: str = Field(min_length=1, max_length=500)


class ModelJobRequirementSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill: str = Field(min_length=1, max_length=100)
    category: str | None = Field(default=None, max_length=80)
    semantic_category: SemanticRequirementCategory
    requirement_type: RequirementType
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
    semantic_category: SemanticRequirementCategory
    requirement: str = Field(min_length=1, max_length=300)
    source_text: str = Field(min_length=1, max_length=500)
    confidence: float = Field(ge=0.0, le=1.0)


class ModelAssistedExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[MODEL_ASSISTED_SCHEMA_VERSION]
    resume_skills: list[ModelSkillSignal] = Field(default_factory=list)
    job_requirements: list[ModelJobRequirementSignal] = Field(default_factory=list)
    hard_constraints: list[ModelHardConstraintSignal] = Field(default_factory=list)
    unknown_resume_skills: list[str] = Field(default_factory=list)
    unknown_job_skills: list[str] = Field(default_factory=list)
    uncertainty_notes: list[str] = Field(default_factory=list)


_WHITESPACE = re.compile(r"\s+")


def _normalized_source(value: str) -> str:
    return _WHITESPACE.sub(" ", value.strip().strip('"\'`-• ')).casefold()


def _source_is_grounded(source_text: str, document_text: str) -> bool:
    source = _normalized_source(source_text)
    document = _normalized_source(document_text)
    return len(source) >= 2 and source in document


def validate_extraction_grounding(
    extraction: ModelAssistedExtraction,
    *,
    resume_text: str,
    job_description: str,
) -> list[str]:
    """Return grounding errors for provider signals whose quoted evidence is absent.

    Validation is performed against the same redacted text sent to the provider,
    preventing a model from introducing unsupported source snippets.
    """

    redacted_resume = redact_sensitive_text(resume_text)
    redacted_job = redact_sensitive_text(job_description)
    errors: list[str] = []

    for signal in extraction.resume_skills:
        if not _source_is_grounded(signal.source_text, redacted_resume):
            errors.append(f"resume skill {signal.name!r} has ungrounded source_text")

    for signal in extraction.job_requirements:
        if not _source_is_grounded(signal.source_text, redacted_job):
            errors.append(f"job requirement {signal.skill!r} has ungrounded source_text")

    for signal in extraction.hard_constraints:
        if not _source_is_grounded(signal.source_text, redacted_job):
            errors.append(f"hard constraint {signal.category!r} has ungrounded source_text")

    return errors
