import json

import pytest

from app.analysis.model_extractor import (
    ModelAssistedExtraction,
    _build_user_prompt,
    extract_model_assisted_signals,
)
from app.analysis.redaction import redact_sensitive_text
from app.analysis.schemas import RequirementType
from app.analysis.service import analyze_smart_fit


SENSITIVE_RESUME = """
JP Candidate
123 Market Street
Philadelphia, PA 19103
jp@example.com
(215) 555-1212
https://github.com/example/profile

SKILLS
Python, FastAPI, SQL, RabbitMQ

PROJECTS
Built a FastAPI service using RabbitMQ queues.
"""

JOB_TEXT = """
Required Qualifications
Build backend APIs with Python and message queues such as RabbitMQ.
"""


def test_redact_sensitive_text_removes_obvious_contact_details() -> None:
    redacted = redact_sensitive_text(SENSITIVE_RESUME)

    assert "jp@example.com" not in redacted
    assert "215" not in redacted
    assert "123 Market Street" not in redacted
    assert "github.com" not in redacted
    assert "Python" in redacted
    assert "RabbitMQ" in redacted


def test_model_prompt_uses_redacted_text() -> None:
    prompt = _build_user_prompt(SENSITIVE_RESUME, JOB_TEXT)

    assert "jp@example.com" not in prompt
    assert "123 Market Street" not in prompt
    assert "github.com" not in prompt
    assert "[REDACTED_EMAIL]" in prompt
    assert "RabbitMQ" in prompt


def test_model_assisted_disabled_falls_back_without_provider_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AI_ANALYSIS_ENABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    analysis = analyze_smart_fit(
        resume_text=SENSITIVE_RESUME,
        job_description=JOB_TEXT,
        use_model_assisted=True,
    )

    assert analysis.analysis_engine == "deterministic"
    assert analysis.model_assisted_status.startswith("fallback_unavailable")
    assert analysis.resume_skills_found


def test_model_assisted_extraction_requires_backend_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_ANALYSIS_ENABLED", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")

    with pytest.raises(Exception) as exc_info:
        extract_model_assisted_signals(SENSITIVE_RESUME, JOB_TEXT)

    assert "OPENAI_API_KEY" in str(exc_info.value)


def test_model_assisted_extraction_schema_accepts_unknown_skills() -> None:
    extraction = ModelAssistedExtraction.model_validate(
        {
            "resume_skills": [
                {
                    "name": "RabbitMQ",
                    "category": "backend",
                    "evidence_status": "demonstrated",
                    "confidence": 0.9,
                    "context": "backend messaging",
                    "source_text": "Built a FastAPI service using RabbitMQ queues.",
                }
            ],
            "job_requirements": [
                {
                    "skill": "RabbitMQ",
                    "category": "backend",
                    "requirement_type": RequirementType.REQUIRED_QUALIFICATION.value,
                    "weight": 0.85,
                    "confidence": 0.9,
                    "context": "backend messaging",
                    "source_text": "message queues such as RabbitMQ",
                }
            ],
            "hard_constraints": [],
            "unknown_resume_skills": ["RabbitMQ"],
            "unknown_job_skills": ["RabbitMQ"],
            "uncertainty_notes": [],
        }
    )

    assert extraction.unknown_resume_skills == ["RabbitMQ"]
    assert extraction.job_requirements[0].skill == "RabbitMQ"
    assert json.loads(extraction.model_dump_json())["resume_skills"][0]["name"] == "RabbitMQ"
