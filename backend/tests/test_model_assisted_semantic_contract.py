from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

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


def _object_schemas(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        if value.get("type") == "object":
            yield value
        for item in value.values():
            yield from _object_schemas(item)
    elif isinstance(value, list):
        for item in value:
            yield from _object_schemas(item)


class _FakeResponse:
    status_code = 200
    headers: dict[str, str] = {}

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

    schema = model_extractor._structured_output_schema()
    assert "schema_version" in schema["required"]

    fixture["unexpected"] = True
    with pytest.raises(ValidationError):
        ModelAssistedExtraction.model_validate(fixture)


def test_provider_schema_matches_strict_structured_output_subset() -> None:
    schema = model_extractor._structured_output_schema()
    encoded_schema = json.dumps(schema)

    assert '"default"' not in encoded_schema
    assert '"title"' not in encoded_schema

    for object_schema in _object_schemas(schema):
        properties = object_schema.get("properties", {})
        assert object_schema["additionalProperties"] is False
        assert set(object_schema["required"]) == set(properties)

    skill_schema = schema["$defs"]["ModelSkillSignal"]
    assert {"category", "context"} <= set(skill_schema["required"])
    assert {"type": "null"} in skill_schema["properties"]["category"]["anyOf"]
    assert {"type": "null"} in skill_schema["properties"]["context"]["anyOf"]


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
    assert "[REDACTED_EMAIL]" in user_prompt


def test_legacy_internal_payload_is_not_accepted_as_provider_output() -> None:
    legacy = _fixture()
    legacy.pop("schema_version")
    legacy["resume_skills"][0].pop("semantic_category")
    legacy["resume_skills"][0].pop("evidence_basis")
    legacy["job_requirements"][0].pop("semantic_category")
    legacy["job_requirements"][0]["weight"] = 1.0

    with pytest.raises(
        ModelAssistedExtractionError,
        match="versioned extraction schema",
    ) as error:
        model_extractor._validate_provider_extraction(
            json.dumps(legacy),
            resume_text=RESUME_TEXT,
            job_description=JOB_TEXT,
        )

    assert error.value.code == "provider_schema_mismatch"


def test_ungrounded_source_text_is_rejected() -> None:
    fixture = _fixture()
    fixture["job_requirements"][0]["source_text"] = "Ten years of Rust leadership"

    with pytest.raises(
        ModelAssistedExtractionError,
        match="ungrounded source evidence",
    ) as error:
        model_extractor._validate_provider_extraction(
            json.dumps(fixture),
            resume_text=RESUME_TEXT,
            job_description=JOB_TEXT,
        )

    assert error.value.code == "provider_ungrounded_evidence"


def test_wrong_schema_version_is_rejected() -> None:
    fixture = _fixture()
    fixture["schema_version"] = "8b.0"

    with pytest.raises(
        ModelAssistedExtractionError,
        match="versioned extraction schema",
    ) as error:
        model_extractor._validate_provider_extraction(
            json.dumps(fixture),
            resume_text=RESUME_TEXT,
            job_description=JOB_TEXT,
        )

    assert error.value.code == "provider_schema_mismatch"


def test_timeout_becomes_typed_fallback_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_provider(monkeypatch)

    class TimeoutClient(_FakeClient):
        def post(self, url: str, *, headers: dict, json: dict):
            request = httpx.Request("POST", url)
            raise httpx.ReadTimeout("timed out", request=request)

    monkeypatch.setattr(model_extractor.httpx, "Client", TimeoutClient)

    with pytest.raises(ModelAssistedExtractionError, match="timed out") as error:
        extract_model_assisted_signals(RESUME_TEXT, JOB_TEXT)

    assert error.value.code == "provider_timeout"
