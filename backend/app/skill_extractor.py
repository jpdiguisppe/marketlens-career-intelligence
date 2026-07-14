import re
from collections import Counter
from typing import Iterable

from app.analysis.skill_ontology import SKILL_PATTERNS


def _term_pattern(term: str) -> str:
    escaped_term = re.escape(term.lower())
    return rf"(?<![a-zA-Z0-9]){escaped_term}(?![a-zA-Z0-9])"


def _contains_term(text: str, term: str) -> bool:
    return re.search(_term_pattern(term), text.lower()) is not None


def _remove_term(text: str, term: str) -> str:
    return re.sub(_term_pattern(term), " ", text.lower())


def _detect_git_skill(text: str) -> bool:
    """Detect Git/source-control skill without treating GitHub Actions as Git by itself."""
    text_without_github_actions = _remove_term(text, "github actions")

    return any(
        _contains_term(text_without_github_actions, pattern)
        for pattern in SKILL_PATTERNS["Git"]
    )


def _detect_c_skill(text: str) -> bool:
    """Detect C without treating C# as C."""
    text_without_csharp = re.sub(_term_pattern("c#"), " ", text.lower())

    return any(
        _contains_term(text_without_csharp, pattern)
        for pattern in SKILL_PATTERNS["C"]
    )


def extract_skills(text: str) -> list[str]:
    """Extract normalized skills from raw job posting or resume text."""
    detected_skills: list[str] = []

    for skill_name, patterns in SKILL_PATTERNS.items():
        if skill_name == "Git":
            if _detect_git_skill(text):
                detected_skills.append(skill_name)
            continue

        if skill_name == "C":
            if _detect_c_skill(text):
                detected_skills.append(skill_name)
            continue

        if any(_contains_term(text, pattern) for pattern in patterns):
            detected_skills.append(skill_name)

    return sorted(detected_skills)


def count_skills(texts: Iterable[str]) -> dict[str, int]:
    """Count how often each normalized skill appears across a group of texts."""
    skill_counter: Counter[str] = Counter()

    for text in texts:
        skill_counter.update(extract_skills(text))

    return dict(skill_counter.most_common())
