import os
import secrets
from dataclasses import dataclass
from typing import Annotated

from fastapi import Header, HTTPException

AUTH_DEV_MODE_ENV = "AUTH_DEV_MODE"
AUTH_DEV_BEARER_TOKEN_ENV = "AUTH_DEV_BEARER_TOKEN"
AUTH_DEV_USER_ID_ENV = "AUTH_DEV_USER_ID"
AUTH_PROVIDER_ENV = "AUTH_PROVIDER"


@dataclass(frozen=True)
class AuthenticatedUser:
    """Verified user identity for private MarketLens endpoints."""

    user_id: str
    auth_provider: str


def _is_enabled(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Invalid authorization header.")

    return token.strip()


def _get_dev_authenticated_user(token: str) -> AuthenticatedUser:
    expected_token = os.getenv(AUTH_DEV_BEARER_TOKEN_ENV)
    if not expected_token:
        raise HTTPException(
            status_code=503,
            detail="Development auth token is not configured.",
        )

    if not secrets.compare_digest(token, expected_token):
        raise HTTPException(status_code=401, detail="Invalid bearer token.")

    return AuthenticatedUser(
        user_id=os.getenv(AUTH_DEV_USER_ID_ENV, "dev-user"),
        auth_provider="dev",
    )


def get_current_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> AuthenticatedUser:
    """Return the current authenticated user for private endpoints.

    Milestone 5 starts with a fail-closed dependency and a dev/test token path.
    Real Clerk JWT verification will replace the production branch before any
    deployed private-data features are enabled.
    """

    token = _extract_bearer_token(authorization)

    if _is_enabled(os.getenv(AUTH_DEV_MODE_ENV)):
        return _get_dev_authenticated_user(token)

    provider = (os.getenv(AUTH_PROVIDER_ENV) or "clerk").strip().lower()
    if provider == "clerk":
        raise HTTPException(
            status_code=503,
            detail="Clerk token verification is not configured yet.",
        )

    raise HTTPException(status_code=503, detail="Authentication is not configured.")
