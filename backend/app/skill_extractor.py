import re
from collections import Counter
from typing import Iterable

from app.skill_ontology import SKILL_PATTERNS


def _term_pattern(term: str) -> str:
    escaped_term = re.escape(term.lower())
    return rf"(?<![a-zA-Z0-9]){escaped_term}(?![a-zA-Z0-9])"


def _contains_term(text: str, term: str) -> bool:
    return re.search(_term_pattern(term), text.lower()) is not None


def _remove_term(text: str, term: str) -> str:
    return re.sub(_term_pattern(term), " ", text.lower())


def _context_windows(
    text: str,
    pattern: str,
    *,
    flags: int = re.IGNORECASE,
    radius: int = 120,
) -> list[str]:
    """Return bounded context around each match without exposing whole documents."""
    windows: list[str] = []
    for match in re.finditer(pattern, text, flags):
        start = max(0, match.start() - radius)
        end = min(len(text), match.end() + radius)
        windows.append(text[start:end].lower())
    return windows


def _detect_git_skill(text: str) -> bool:
    """Detect Git/source-control skill without treating GitHub Actions as Git by itself."""
    text_without_github_actions = _remove_term(text, "github actions")

    return any(
        _contains_term(text_without_github_actions, pattern)
        for pattern in SKILL_PATTERNS["Git"]
    )


_C_PROGRAMMING_CONTEXT = (
    "programming",
    "programmer",
    "language",
    "languages",
    "software",
    "developer",
    "development",
    "embedded",
    "firmware",
    "compiler",
    "coding",
    "codebase",
    "computer science",
)
_OTHER_PROGRAMMING_LANGUAGES = (
    "python",
    "java",
    "javascript",
    "typescript",
    "sql",
    "c++",
    "rust",
    "golang",
)


def _detect_c_skill(text: str) -> bool:
    """Detect programming-language C without treating ordinary letter C as a skill."""
    text_without_csharp = re.sub(
        r"(?<![A-Za-z0-9])C#(?![A-Za-z0-9])",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    if _contains_term(text_without_csharp, "c language") or _contains_term(
        text_without_csharp,
        "programming in c",
    ):
        return True

    # Bare C is accepted only when it is capitalized and grounded in an
    # unmistakable programming context or a list of programming languages.
    c_pattern = r"(?<![A-Za-z0-9+#])C(?![A-Za-z0-9+#])"
    for window in _context_windows(
        text_without_csharp,
        c_pattern,
        flags=0,
        radius=100,
    ):
        if any(anchor in window for anchor in _C_PROGRAMMING_CONTEXT):
            return True
        if any(language in window for language in _OTHER_PROGRAMMING_LANGUAGES):
            return True
    return False


_TESTING_STRONG_PATTERNS = tuple(
    pattern for pattern in SKILL_PATTERNS["Testing"] if pattern != "testing"
)
_SOFTWARE_TESTING_CONTEXT = (
    "software",
    "application",
    "applications",
    "api",
    "apis",
    "code",
    "developer",
    "development",
    "quality assurance",
    " qa ",
    "frontend",
    "backend",
    "web",
    "mobile",
    "regression",
    "integration",
    "unit",
    "automation",
    "automated",
    "test case",
    "test cases",
    "ci/cd",
)


def _detect_testing_skill(text: str) -> bool:
    """Keep software-testing evidence while rejecting generic field/classroom testing."""
    if any(_contains_term(text, pattern) for pattern in _TESTING_STRONG_PATTERNS):
        return True

    for window in _context_windows(text, _term_pattern("testing"), radius=100):
        padded = f" {window} "
        if any(anchor in padded for anchor in _SOFTWARE_TESTING_CONTEXT):
            return True
    return False


_MACHINE_LEARNING_TERMS = (
    "machine learning",
    "artificial intelligence",
)
_MACHINE_LEARNING_CONTEXT = (
    "experience",
    "experienced",
    "proficiency",
    "proficient",
    "knowledge",
    "certificate",
    "certification",
    "coursework",
    "skills",
    "prototyping",
    "required",
    "preferred",
    "qualification",
    "qualifications",
    "responsibility",
    "responsibilities",
    "must",
    "alerts",
    "experiments",
    "engineer",
    "engineering",
    "scientist",
    "research",
    "model",
    "models",
    "modeling",
    "algorithm",
    "algorithms",
    "training",
    "inference",
    "prediction",
    "classification",
    "neural",
    "pytorch",
    "tensorflow",
    "scikit-learn",
    "data science",
    "llm",
    "large language model",
)
_AI_ML_ACRONYM_PATTERN = r"(?<![A-Za-z0-9])(?:AI|ML)(?![A-Za-z0-9])"


def _detect_machine_learning_skill(text: str) -> bool:
    """Require role-level technical evidence, not incidental company AI language."""
    normalized = text.lower()
    if "ai/ml" in normalized or "ai & ml" in normalized or "ai and ml" in normalized:
        return True

    for term in _MACHINE_LEARNING_TERMS:
        for window in _context_windows(text, _term_pattern(term), radius=140):
            if any(anchor in window for anchor in _MACHINE_LEARNING_CONTEXT):
                return True

    # Acronyms are especially ambiguous, so require original uppercase spelling
    # plus nearby technical evidence.
    for window in _context_windows(
        text,
        _AI_ML_ACRONYM_PATTERN,
        flags=0,
        radius=120,
    ):
        if any(anchor in window for anchor in _MACHINE_LEARNING_CONTEXT):
            return True
    return False


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

        if skill_name == "Testing":
            if _detect_testing_skill(text):
                detected_skills.append(skill_name)
            continue

        if skill_name == "Machine Learning":
            if _detect_machine_learning_skill(text):
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
