import pytest

from app.auth import validate_auth_runtime_configuration


_DEPLOYMENT_MARKERS = (
    "RAILWAY_PROJECT_ID",
    "RAILWAY_SERVICE_ID",
    "RAILWAY_ENVIRONMENT_ID",
    "RAILWAY_ENVIRONMENT_NAME",
)


def _clear_runtime_markers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MARKETLENS_ENVIRONMENT", raising=False)
    for variable_name in _DEPLOYMENT_MARKERS:
        monkeypatch.delenv(variable_name, raising=False)


def test_development_auth_is_allowed_for_local_test_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_runtime_markers(monkeypatch)
    monkeypatch.setenv("AUTH_DEV_MODE", "true")

    validate_auth_runtime_configuration()


def test_development_auth_is_rejected_for_explicit_production_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_runtime_markers(monkeypatch)
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.setenv("AUTH_DEV_BEARER_TOKEN", "must-not-appear-in-errors")
    monkeypatch.setenv("MARKETLENS_ENVIRONMENT", "production")

    with pytest.raises(RuntimeError) as exc_info:
        validate_auth_runtime_configuration()

    message = str(exc_info.value)
    assert "Development authentication cannot be enabled" in message
    assert "must-not-appear-in-errors" not in message


@pytest.mark.parametrize("variable_name", _DEPLOYMENT_MARKERS)
def test_development_auth_is_rejected_for_any_railway_runtime_marker(
    variable_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_runtime_markers(monkeypatch)
    monkeypatch.setenv("AUTH_DEV_MODE", "1")
    monkeypatch.setenv(variable_name, "railway-value")

    with pytest.raises(RuntimeError, match="Development authentication cannot be enabled"):
        validate_auth_runtime_configuration()


def test_clerk_auth_mode_is_allowed_in_railway_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_runtime_markers(monkeypatch)
    monkeypatch.setenv("AUTH_DEV_MODE", "false")
    monkeypatch.setenv("RAILWAY_SERVICE_ID", "railway-service")

    validate_auth_runtime_configuration()
