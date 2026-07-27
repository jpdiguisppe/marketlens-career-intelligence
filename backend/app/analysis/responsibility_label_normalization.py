"""Canonical labels for grounded model responsibility phrases.

Model-assisted extraction may return an exact imperative responsibility as the
``skill`` label. The source quote is valuable provenance, but the display label
should be a concise capability name. This module normalizes only exact known
aliases and leaves source evidence and unknown labels untouched.
"""

from __future__ import annotations

import re

import app.analysis.skill_ontology as _ontology

_CANONICAL_LABEL = "Backend API Reliability"
_CATEGORY = "backend"
_RELATED_CONCEPTS = ["REST APIs", "Testing"]
_ALIASES = (
    "backend api reliability",
    "reliable backend api",
    "reliable backend apis",
    "build reliable backend api",
    "build reliable backend apis",
)

_WHITESPACE = re.compile(r"\s+")
_EDGE_PUNCTUATION = " \t\r\n.,;:!?\"'`()[]{}-•"


def _normalized_alias(value: str) -> str:
    return _WHITESPACE.sub(" ", value.strip(_EDGE_PUNCTUATION)).casefold()


_ALIAS_TO_CANONICAL = {
    _normalized_alias(alias): _CANONICAL_LABEL
    for alias in (*_ALIASES, _CANONICAL_LABEL)
}


def _canonical_for_exact_alias(value: str) -> str | None:
    return _ALIAS_TO_CANONICAL.get(_normalized_alias(value))


def canonicalize_model_skill_label(value: str) -> str:
    """Return a canonical capability label for an exact known alias.

    The function intentionally avoids fuzzy matching. A model-only technology or
    an unfamiliar responsibility remains unchanged except for whitespace cleanup.
    """

    cleaned = _WHITESPACE.sub(" ", value.strip())
    if not cleaned:
        return ""
    return _canonical_for_exact_alias(cleaned) or cleaned


def canonicalize_grounded_model_skill_label(label: str, source_text: str) -> str:
    """Canonicalize from the grounded quote before trusting the model label.

    The provider may summarize the same responsibility with a shorter label such
    as ``backend APIs``. When its exact grounded quote is a known alias, the quote
    determines the canonical capability so deterministic and model extraction
    merge into one requirement. Unknown quotes still fall back to conservative
    exact-label normalization.
    """

    source_canonical = _canonical_for_exact_alias(source_text)
    if source_canonical is not None:
        return source_canonical
    return canonicalize_model_skill_label(label)


def install_responsibility_label_normalization() -> None:
    """Register the capability with deterministic extraction and categorization."""

    existing_patterns = _ontology.SKILL_PATTERNS.setdefault(_CANONICAL_LABEL, [])
    for alias in _ALIASES:
        if alias not in existing_patterns:
            existing_patterns.append(alias)

    _ontology.SKILL_CATEGORIES[_CANONICAL_LABEL] = _CATEGORY
    _ontology.RELATED_SKILLS[_CANONICAL_LABEL] = list(_RELATED_CONCEPTS)


__all__ = [
    "canonicalize_grounded_model_skill_label",
    "canonicalize_model_skill_label",
    "install_responsibility_label_normalization",
]
