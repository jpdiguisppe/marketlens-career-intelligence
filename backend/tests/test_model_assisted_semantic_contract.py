from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from app.analysis import model_extractor
from app.analysis.model_extractor import (
    MODEL_ASSISTED_SCHEMA_VERSION,
    ModelAssistedExtraction,
    ModelAssistedExtractionError,
    extract_model_assisted_signals,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "model_assisted_extraction_v8b1.json"
)
RESUME_TEXT = """PROJECTS
Built a FastAPI service in Python and deployed it with Terraform.
SKILLS
Terraform
"""
JOB_TEXT = """Backend Data Engineer
REQUIRED QUALIFICATIONS
Python is required.
Bachelor's degree in computer science.
PREFERRED QUALIFICATIONS
Kubernetes is preferred.
RESPONSIBILITIES
Build reliable data pipelines.
"""


def _fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


class _FakeResponse:
    status_code = 200

    def __init__(self, output_text: str):
        self._output_text = output_text

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"output_text": self._output_text}


class _FakeClient:
    captured: dict = {}

    def __init__(self, *, timeout: float):
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def post(self, url: str, *, headers: dict, json: dict):
        self.__class__.captured = {
            "url": url,
            "headers": headers,
            "payload": json,
            "timeout": self.timeout,
        }
        return _FakeResponse(output_text=__import__("json").dumps(_fixture()))


def _configure_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "backend-secret")
    monkeypatch.setenv("OPENAI_MODEL", "fixture-model")
    monkeypatch.setenv("OPENAI_TIMEOUT_SECONDS", "4.5")


def test_semantic_contract_is_versioned_and_forbids_extra_fields() -> None:
    fixture = _fixture()
    extraction = ModelAssistedExtraction.model_validate(fixture)

    assert extraction.schema_version == MODEL_ASSISTED_SCHEMA_VERSION
    assert extraction.job_requirements[0].semantic_category.value == "tool_technology"
    assert extraction.resume_skills[0].evidence_basis.value == "direct_application"

    fixture["unexpected"] = True
    with pytest.raises(ValidationError):
        ModelAssistedExtraction.model_validate(fixture)


def test_provider_fixture_uses_strict_schema_redaction_and_no_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_provider(monkeypatch)
    monkeypatch.setattr(model_extractor.httpx, "Client", _FakeClient)

    extraction = extract_model_assisted_signals(
        resume_text=f"James Example | james@example.com\n{RESUME_TEXT}",
        job_description=JOB_TEXT,
    )

    captured = _FakeClient.captured
    payload = captured["payload"]
    user_prompt = payload["input"][1]["content"]

    assert extraction.schema_version == MODEL_ASSISTED_SCHEMA_VERSION
    assert captured["url"].endswith("/responses")
    assert captured["headers"]["Authorization"] == "Bearer backend-secret"
    assert captured["timeout"] == 4.5
    assert payload["store"] is False
    assert payload["text"]["format"]["strict"] is True
    assert "james@example.com" not in user_prompt
    assert "[REDACTED EMAIL]" in user_prompt


def test_ungrounded_source_text_is_rejected() -> None:
    fixture = _fixture()
    fixture["job_requirements"][0]["source_text"] = "Ten years of Rust leadership"

    with pytest.raises(ModelAssistedExtractionError, match="ungrounded source evidence"):
        model_extractor._validate_provider_extraction(
            json.dumps(fixture),
            resume_text=RESUME_TEXT,
            job_description=JOB_TEXT,
        )


def test_wrong_schema_version_is_rejected() -> None:
    fixture = _fixture()
    fixture["schema_version"] = "8b.0"

    with pytest.raises(ModelAssistedExtractionError, match="versioned extraction schema"):
        model_extractor._validate_provider_extraction(
            json.dumps(fixture),
            resume_text=RESUME_TEXT,
            job_description=JOB_TEXT,
        )


def test_timeout_becomes_typed_fallback_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_provider(monkeypatch)

    class TimeoutClient(_FakeClient):
        def post(self, url: str, *, headers: dict, json: dict):
            request = httpx.Request("POST", url)
            raise httpx.ReadTimeout("timed out", request=request)

    monkeypatch.setattr(model_extractor.httpx, "Client", TimeoutClient)

    with pytest.raises(ModelAssistedExtractionError, match="timed out"):
        extract_model_assisted_signals(RESUME_TEXT, JOB_TEXT)
