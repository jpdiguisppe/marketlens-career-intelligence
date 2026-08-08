from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _location_block(nginx: str, location: str) -> str:
    marker = f"location = {location} {{"
    start = nginx.index(marker)
    end = nginx.index("\n        }", start)
    return nginx[start:end]


def test_frontend_entrypoint_has_executable_shebang_and_dynamic_csp_origin() -> None:
    entrypoint = (REPO_ROOT / "frontend" / "docker-entrypoint.sh").read_bytes()
    assert entrypoint.startswith(b"#!/bin/sh\n")

    text = entrypoint.decode()
    assert "__API_ORIGIN__" in text
    assert "API_ORIGIN=" in text
    assert "exec nginx" in text


def test_nginx_security_headers_are_inherited_by_html_and_runtime_config() -> None:
    nginx = (REPO_ROOT / "frontend" / "nginx.conf").read_text()

    assert nginx.startswith("pid /tmp/nginx.pid;\n")
    assert "connect-src 'self' __API_ORIGIN__" in nginx
    assert 'add_header Cache-Control "no-store, max-age=0" always;' in nginx
    assert 'add_header Pragma "no-cache" always;' in nginx
    assert "frame-ancestors 'none'" in nginx
    assert "object-src 'none'" in nginx

    for location in ("/index.html", "/config.js"):
        block = _location_block(nginx, location)
        assert "add_header" not in block


def test_compose_exposes_the_unprivileged_frontend_port() -> None:
    compose = (REPO_ROOT / "docker-compose.yml").read_text()
    assert 'PORT: "8080"' in compose
    assert '"5173:8080"' in compose
    assert '"5173:80"' not in compose
