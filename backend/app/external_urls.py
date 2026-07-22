from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

MAX_EXTERNAL_URL_LENGTH = 2_048


def sanitize_external_https_url(value: str | None) -> str | None:
    """Return a safe HTTPS URL or None.

    External posting links are displayed to users but are never fetched by
    MarketLens. Reject credentials, local/private hosts, control characters,
    non-HTTPS schemes, and unusual ports before a link reaches the UI or DB.
    """

    if value is None:
        return None

    cleaned = value.strip()
    if not cleaned or len(cleaned) > MAX_EXTERNAL_URL_LENGTH:
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in cleaned):
        return None

    try:
        parsed = urlsplit(cleaned)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        return None

    if parsed.scheme.lower() != "https" or not hostname:
        return None
    if parsed.username or parsed.password:
        return None
    if port not in {None, 443}:
        return None

    normalized_hostname = hostname.rstrip(".").lower()
    if not normalized_hostname or len(normalized_hostname) > 253:
        return None
    if normalized_hostname == "localhost" or normalized_hostname.endswith(".localhost"):
        return None

    try:
        address = ipaddress.ip_address(normalized_hostname)
    except ValueError:
        address = None

    if address is not None and (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        return None

    return cleaned


def require_external_https_url(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None

    sanitized = sanitize_external_https_url(value)
    if sanitized is None:
        raise ValueError("External links must use a public HTTPS URL without embedded credentials.")
    return sanitized
