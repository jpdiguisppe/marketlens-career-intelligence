import os
import secrets
from dataclasses import dataclass
from typing import Annotated

import httpx
from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions
from fastapi import Header, HTTPException, Request

AUTH_DEV_MODE_ENV = "AUTH_DEV_MODE"
AUTH_DEV_BEARER_TOKEN_ENV = "AUTH_DEV_BEARER_TOKEN"
AUTH_DEV_USER_ID_ENV = "AUTH_DEV_USER_ID"
AUTH_PROVIDER_ENV = "AUTH_PROVIDER"

CLERK_SECRET_KEY_ENV = "CLERK_SECRET_KEY"
CLERK_AUTHORIZED_PARTIES_ENV = "CLERK_AUTHORIZED_PARTIES"


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


def _get_clerk_authorized_parties() -> list[str]:
    configured_parties = os.getenv(CLERK_AUTHORIZED_PARTIES_ENV, "")

    return [
        party.strip().rstrip("/")
        for party in configured_parties.split(",")
        if party.strip()
    ]


def _get_clerk_authenticated_user(
    request: Request,
    token: str,
) -> AuthenticatedUser:
    secret_key = os.getenv(CLERK_SECRET_KEY_ENV)
    if not secret_key:
        raise HTTPException(
            status_code=503,
            detail="Clerk secret key is not configured.",
        )

    authorized_parties = _get_clerk_authorized_parties()
    if not authorized_parties:
        raise HTTPException(
            status_code=503,
            detail="Clerk authorized parties are not configured.",
        )

    headers = dict(request.headers)
    headers["authorization"] = f"Bearer {token}"

    clerk_request = httpx.Request(
        method=request.method,
        url=str(request.url),
        headers=headers,
    )

    try:
        with Clerk(bearer_auth=secret_key) as clerk:
            request_state = clerk.authenticate_request(
                clerk_request,
                AuthenticateRequestOptions(
                    authorized_parties=authorized_parties,
                ),
            )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Authentication service is temporarily unavailable.",
        ) from exc

    if not request_state.is_signed_in:
        raise HTTPException(status_code=401, detail="Invalid or expired session token.")

    payload = request_state.payload or {}
    user_id = payload.get("sub") if isinstance(payload, dict) else getattr(payload, "sub", None)

    if not isinstance(user_id, str) or not user_id.strip():
        raise HTTPException(status_code=401, detail="Authenticated user ID is missing.")

    return AuthenticatedUser(
        user_id=user_id,
        auth_provider="clerk",
    )


def get_current_user(
    request: Request,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> AuthenticatedUser:
    """Verify and return the current user for private MarketLens endpoints."""

    token = _extract_bearer_token(authorization)

    if _is_enabled(os.getenv(AUTH_DEV_MODE_ENV)):
        return _get_dev_authenticated_user(token)

    provider = (os.getenv(AUTH_PROVIDER_ENV) or "clerk").strip().lower()
    if provider == "clerk":
        return _get_clerk_authenticated_user(request, token)

    raise HTTPException(status_code=503, detail="Authentication is not configured.")
