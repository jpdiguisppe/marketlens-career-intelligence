"""Lightweight text redaction before optional model-provider calls.

This is a best-effort safety layer, not a privacy guarantee. It removes obvious
contact details and URL-style identifiers while preserving technical content that
is useful for career-fit analysis.
"""

from __future__ import annotations

import re

_EMAIL_PATTERN = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
_PHONE_PATTERN = re.compile(
    r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b"
)
_URL_PATTERN = re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)
_LINKEDIN_GITHUB_PATTERN = re.compile(
    r"\b(?:linkedin\.com|github\.com)/\S+", re.IGNORECASE
)
_ADDRESS_LINE_PATTERN = re.compile(
    r"^\s*\d{1,6}\s+[A-Za-z0-9.'\-\s]+\s+"
    r"(?:street|st\.?|road|rd\.?|avenue|ave\.?|drive|dr\.?|lane|ln\.?|court|ct\.?|boulevard|blvd\.?)"
    r"(?:\s|,|$).*",
    re.IGNORECASE,
)


def redact_sensitive_text(text: str) -> str:
    """Redact obvious personal identifiers before provider transmission."""

    redacted_lines: list[str] = []
    for line in text.splitlines():
        if _ADDRESS_LINE_PATTERN.match(line):
            redacted_lines.append("[REDACTED_ADDRESS]")
            continue

        cleaned = _EMAIL_PATTERN.sub("[REDACTED_EMAIL]", line)
        cleaned = _PHONE_PATTERN.sub("[REDACTED_PHONE]", cleaned)
        cleaned = _URL_PATTERN.sub("[REDACTED_URL]", cleaned)
        cleaned = _LINKEDIN_GITHUB_PATTERN.sub("[REDACTED_URL]", cleaned)
        redacted_lines.append(cleaned)

    return "\n".join(redacted_lines)
