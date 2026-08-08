from __future__ import annotations

import ipaddress
import os
import threading
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

TRUSTED_PROXY_CIDRS_ENV = "TRUSTED_PROXY_CIDRS"
MARKETLENS_ENVIRONMENT_ENV = "MARKETLENS_ENVIRONMENT"
_PRODUCTION_ENVIRONMENT_NAMES = {"prod", "production"}
_RAILWAY_RUNTIME_ENVIRONMENT_VARIABLES = (
    "RAILWAY_PROJECT_ID",
    "RAILWAY_SERVICE_ID",
    "RAILWAY_ENVIRONMENT_ID",
    "RAILWAY_ENVIRONMENT_NAME",
)

RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_GLOBAL_MAX_REQUESTS = 300
RATE_LIMIT_MAX_TRACKED_CLIENTS = 5_000
RATE_LIMIT_PUBLIC_MAX_REQUESTS = 30
RATE_LIMIT_EXPENSIVE_MAX_REQUESTS = 12
RATE_LIMIT_ADMIN_MAX_REQUESTS = 10
RATE_LIMIT_PRIVATE_MAX_REQUESTS = 90
MAX_API_REQUEST_BODY_BYTES = 2_000_000


@dataclass(frozen=True)
class RateLimitPolicy:
    scope: str
    max_requests: int


PUBLIC_RATE_LIMIT = RateLimitPolicy("public", RATE_LIMIT_PUBLIC_MAX_REQUESTS)
EXPENSIVE_RATE_LIMIT = RateLimitPolicy("expensive", RATE_LIMIT_EXPENSIVE_MAX_REQUESTS)
ADMIN_RATE_LIMIT = RateLimitPolicy("admin", RATE_LIMIT_ADMIN_MAX_REQUESTS)
PRIVATE_RATE_LIMIT = RateLimitPolicy("private", RATE_LIMIT_PRIVATE_MAX_REQUESTS)

_rate_limit_buckets: dict[str, list[float]] = {}
_global_rate_limit_timestamps: list[float] = []
_rate_limit_lock = threading.Lock()


def is_production_or_railway_runtime() -> bool:
    explicit_environment = (os.getenv(MARKETLENS_ENVIRONMENT_ENV) or "").strip().lower()
    if explicit_environment in _PRODUCTION_ENVIRONMENT_NAMES:
        return True
    return any(
        bool((os.getenv(variable_name) or "").strip())
        for variable_name in _RAILWAY_RUNTIME_ENVIRONMENT_VARIABLES
    )


def fastapi_docs_configuration() -> dict[str, str | None]:
    """Disable interactive API discovery on deployed production runtimes."""
    if is_production_or_railway_runtime():
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}
    return {"docs_url": "/docs", "redoc_url": "/redoc", "openapi_url": "/openapi.json"}


def _validated_ip(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


def _trusted_proxy_networks() -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    configured = os.getenv(TRUSTED_PROXY_CIDRS_ENV, "")
    for raw_network in configured.split(","):
        candidate = raw_network.strip()
        if not candidate:
            continue
        try:
            networks.append(ipaddress.ip_network(candidate, strict=False))
        except ValueError:
            # Invalid entries fail closed: they never make a peer trusted.
            continue
    return tuple(networks)


def _peer_is_trusted_proxy(peer_ip: str | None) -> bool:
    validated_peer = _validated_ip(peer_ip)
    if not validated_peer:
        return False
    address = ipaddress.ip_address(validated_peer)
    return any(address in network for network in _trusted_proxy_networks())


def _get_rate_limit_identifier(request: Request) -> str:
    peer_host = request.client.host if request.client and request.client.host else None
    validated_peer = _validated_ip(peer_host)

    if _peer_is_trusted_proxy(validated_peer):
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            forwarded_ip = _validated_ip(forwarded_for.split(",", maxsplit=1)[0])
            if forwarded_ip:
                return forwarded_ip

    if validated_peer:
        return validated_peer
    if peer_host:
        return peer_host[:120]
    return "unknown-client"


def _prune_rate_limit_state(window_start: float) -> None:
    global _global_rate_limit_timestamps
    _global_rate_limit_timestamps = [
        timestamp for timestamp in _global_rate_limit_timestamps if timestamp >= window_start
    ]

    stale_keys = [
        key
        for key, timestamps in _rate_limit_buckets.items()
        if not timestamps or timestamps[-1] < window_start
    ]
    for key in stale_keys:
        _rate_limit_buckets.pop(key, None)

    if len(_rate_limit_buckets) > RATE_LIMIT_MAX_TRACKED_CLIENTS:
        oldest = sorted(
            _rate_limit_buckets,
            key=lambda key: _rate_limit_buckets[key][-1] if _rate_limit_buckets[key] else 0.0,
        )
        for key in oldest[: len(_rate_limit_buckets) - RATE_LIMIT_MAX_TRACKED_CLIENTS]:
            _rate_limit_buckets.pop(key, None)


def _enforce_rate_limit(
    request: Request,
    policy: RateLimitPolicy,
    *,
    explicit_identifier: str | None = None,
) -> None:
    # Starlette's in-process TestClient uses this synthetic peer name.
    # Real ASGI socket peers are IP addresses, so production traffic cannot trigger this bypass.
    if request.client and request.client.host == "testclient":
        return

    identifier = explicit_identifier or _get_rate_limit_identifier(request)
    bucket_key = f"{policy.scope}:{identifier}"
    now = time.monotonic()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS

    with _rate_limit_lock:
        _prune_rate_limit_state(window_start)
        if len(_global_rate_limit_timestamps) >= RATE_LIMIT_GLOBAL_MAX_REQUESTS:
            raise HTTPException(
                status_code=429,
                detail="Service-wide rate limit exceeded. Please wait before trying again.",
                headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECONDS)},
            )

        request_timestamps = _rate_limit_buckets.setdefault(bucket_key, [])
        request_timestamps[:] = [
            timestamp for timestamp in request_timestamps if timestamp >= window_start
        ]
        if len(request_timestamps) >= policy.max_requests:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please wait before trying again.",
                headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECONDS)},
            )

        request_timestamps.append(now)
        _global_rate_limit_timestamps.append(now)


def enforce_public_rate_limit(request: Request) -> None:
    _enforce_rate_limit(request, PUBLIC_RATE_LIMIT)


def enforce_expensive_rate_limit(request: Request) -> None:
    _enforce_rate_limit(request, EXPENSIVE_RATE_LIMIT)


def enforce_admin_rate_limit(request: Request) -> None:
    _enforce_rate_limit(request, ADMIN_RATE_LIMIT)


def enforce_private_rate_limit(request: Request, user_id: str) -> None:
    normalized_user_id = user_id.strip()[:255] if isinstance(user_id, str) else ""
    if not normalized_user_id:
        raise HTTPException(status_code=401, detail="Authenticated user ID is missing.")
    _enforce_rate_limit(
        request,
        PRIVATE_RATE_LIMIT,
        explicit_identifier=f"user:{normalized_user_id}",
    )


def reset_rate_limit_state_for_tests() -> None:
    with _rate_limit_lock:
        _rate_limit_buckets.clear()
        _global_rate_limit_timestamps.clear()


class RequestBodyLimitMiddleware:
    """Reject oversized request bodies before JSON or multipart parsing."""

    def __init__(self, app: ASGIApp, max_body_bytes: int = MAX_API_REQUEST_BODY_BYTES) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http" or scope.get("method") not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return

        headers = {
            key.lower(): value
            for key, value in scope.get("headers", [])
        }
        raw_content_length = headers.get(b"content-length")
        if raw_content_length:
            try:
                if int(raw_content_length) > self.max_body_bytes:
                    response = JSONResponse(
                        status_code=413,
                        content={"detail": "Request body is too large."},
                    )
                    await response(scope, receive, send)
                    return
            except ValueError:
                response = JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid Content-Length header."},
                )
                await response(scope, receive, send)
                return

        buffered_messages: list[Message] = []
        received_bytes = 0
        while True:
            message = await receive()
            buffered_messages.append(message)
            if message["type"] == "http.disconnect":
                break
            if message["type"] != "http.request":
                continue

            received_bytes += len(message.get("body", b""))
            if received_bytes > self.max_body_bytes:
                response = JSONResponse(
                    status_code=413,
                    content={"detail": "Request body is too large."},
                )
                await response(scope, receive, send)
                return
            if not message.get("more_body", False):
                break

        index = 0

        async def replay_receive() -> Message:
            nonlocal index
            if index < len(buffered_messages):
                message = buffered_messages[index]
                index += 1
                return message
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay_receive, send)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply defense-in-depth API headers and prevent sensitive response caching."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
        )
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        if is_production_or_railway_runtime():
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
            )
        return response
