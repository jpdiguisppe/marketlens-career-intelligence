"""Compatibility exports for the dependency-light shared skill ontology.

The canonical definitions live at ``app.skill_ontology`` so foundational skill
extraction does not initialize the full analysis pipeline. Existing analysis
imports retain the same public names through this module.
"""

from app.skill_ontology import (
    RELATED_SKILLS,
    SKILL_CATEGORIES,
    SKILL_ONTOLOGY,
    SKILL_PATTERNS,
    SkillDefinition,
)

__all__ = [
    "RELATED_SKILLS",
    "SKILL_CATEGORIES",
    "SKILL_ONTOLOGY",
    "SKILL_PATTERNS",
    "SkillDefinition",
]
