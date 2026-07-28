from __future__ import annotations

import json

from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.http_safety import SafeFastAPI


class ExampleRequest(BaseModel):
    secret_text: str = Field(min_length=5, max_length=20)


def _test_app() -> SafeFastAPI:
    app = SafeFastAPI()

    @app.post("/validate")
    def validate(payload: ExampleRequest) -> dict[str, bool]:
        return {"ok": bool(payload.secret_text)}

    @app.get("/explode")
    def explode() -> None:
        raise RuntimeError(
            "CANARY INTERNAL EXCEPTION with database password and provider body"
        )

    return app


def test_validation_response_does_not_echo_rejected_input() -> None:
    canary = "CANARY REJECTED INPUT THAT MUST NEVER BE RETURNED"
    client = TestClient(_test_app(), raise_server_exceptions=False)

    response = client.post("/validate", json={"secret_text": canary})

    assert response.status_code == 422
    response_text = response.text
    assert canary not in response_text
    payload = response.json()
    assert payload["detail"] == "Request validation failed."
    assert payload["errors"]
    assert "input" not in json.dumps(payload).lower()


def test_unhandled_error_response_contains_no_exception_details() -> None:
    client = TestClient(_test_app(), raise_server_exceptions=False)

    response = client.get("/explode")

    assert response.status_code == 500
    assert response.json() == {"detail": "An internal service error occurred."}
    assert "CANARY INTERNAL EXCEPTION" not in response.text
    assert "password" not in response.text.lower()
