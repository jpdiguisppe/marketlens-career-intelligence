import re
from collections import Counter
from typing import Iterable


SKILL_PATTERNS: dict[str, list[str]] = {
    "Python": ["python"],
    "Java": ["java"],
    "JavaScript": ["javascript", "js"],
    "TypeScript": ["typescript", "ts"],
    "SQL": ["sql", "relational database", "relational databases"],
    "PostgreSQL": ["postgresql", "postgres"],
    "MySQL": ["mysql"],
    "React": ["react", "react.js", "reactjs"],
    "Node.js": ["node.js", "nodejs", "node"],
    "FastAPI": ["fastapi"],
    "REST APIs": [
        "rest api",
        "rest apis",
        "restful api",
        "restful apis",
        "restful service",
        "restful services",
        "api development",
    ],
    "Docker": ["docker", "containerization", "containers", "containerized"],
    "Kubernetes": ["kubernetes", "k8s"],
    "AWS": ["aws", "amazon web services"],
    "Azure": ["azure", "microsoft azure"],
    "Linux": ["linux", "unix"],
    "Windows Server": ["windows server"],
    "Git": ["git", "github", "version control"],
    "CI/CD": ["ci/cd", "continuous integration", "continuous deployment", "github actions"],
    "Agile": ["agile", "scrum"],
    "Testing": [
        "testing",
        "unit testing",
        "automated test",
        "automated tests",
        "automated testing",
        "test automation",
    ],
    "Machine Learning": ["machine learning", "ml", "artificial intelligence", "ai"],
    "Data Pipelines": ["data pipeline", "data pipelines", "etl"],
    "Scripting": ["scripting", "automation scripting", "script"],
}


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


def extract_skills(text: str) -> list[str]:
    """Extract normalized skills from raw job posting or resume text."""
    detected_skills: list[str] = []

    for skill_name, patterns in SKILL_PATTERNS.items():
        if skill_name == "Git":
            if _detect_git_skill(text):
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