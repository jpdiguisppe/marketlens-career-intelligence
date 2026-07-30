from __future__ import annotations

import os
import re

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/deployment", tags=["deployment"])

_REVISION_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")


class DeploymentStatusResponse(BaseModel):
    status: str = Field(pattern="^ok$")
    service: str
    revision: str
    branch: str | None
    environment: str | None


def _safe_environment_value(name: str, *, max_length: int = 120) -> str | None:
    value = os.getenv(name)
    if not value:
        return None
    cleaned = "".join(character for character in value.strip() if character.isalnum() or character in "-_.")
    return cleaned[:max_length] or None


def deployment_revision() -> str:
    for name in ("RAILWAY_GIT_COMMIT_SHA", "GITHUB_SHA", "MARKETLENS_REVISION"):
        candidate = (os.getenv(name) or "").strip()
        if _REVISION_PATTERN.fullmatch(candidate):
            return candidate.lower()
    return "unknown"


@router.get("/status", response_model=DeploymentStatusResponse)
def deployment_status() -> DeploymentStatusResponse:
    """Expose non-secret deployment identity for exact-revision canaries."""

    return DeploymentStatusResponse(
        status="ok",
        service="marketlens-backend",
        revision=deployment_revision(),
        branch=_safe_environment_value("RAILWAY_GIT_BRANCH"),
        environment=_safe_environment_value("RAILWAY_ENVIRONMENT_NAME"),
    )


__all__ = ["DeploymentStatusResponse", "deployment_revision", "deployment_status", "router"]
