from __future__ import annotations

from fastapi.routing import APIRoute

from app.main import app
from app.security import enforce_expensive_rate_limit, enforce_public_rate_limit


def _route_dependency_calls(path: str, method: str) -> set[object]:
    route = next(
        candidate
        for candidate in app.routes
        if isinstance(candidate, APIRoute)
        and candidate.path == path
        and method.upper() in candidate.methods
    )
    return {
        dependency.call
        for dependency in route.dependant.dependencies
        if dependency.call is not None
    }


def test_expensive_public_operations_use_stricter_rate_policy() -> None:
    expensive_routes = {
        ("/analysis/resume-file/extract", "POST"),
        ("/jobs/search", "GET"),
        ("/analysis/custom", "POST"),
        ("/analysis/smart", "POST"),
        ("/analysis/smart/batch", "POST"),
    }

    for path, method in expensive_routes:
        dependencies = _route_dependency_calls(path, method)
        assert enforce_expensive_rate_limit in dependencies, (path, method, dependencies)
        assert enforce_public_rate_limit not in dependencies, (path, method, dependencies)


def test_lower_cost_public_analysis_keeps_standard_rate_policy() -> None:
    standard_routes = {
        ("/skills/extract", "POST"),
        ("/resume/analyze", "POST"),
        ("/analysis/resume", "POST"),
    }

    for path, method in standard_routes:
        dependencies = _route_dependency_calls(path, method)
        assert enforce_public_rate_limit in dependencies, (path, method, dependencies)
        assert enforce_expensive_rate_limit not in dependencies, (path, method, dependencies)
