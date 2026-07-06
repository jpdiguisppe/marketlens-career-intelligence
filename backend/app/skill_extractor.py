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
    "REST APIs": ["rest api", "rest apis", "restful api", "restful apis", "api development"],
    "Docker": ["docker", "containerization", "containers", "containerized"],
    "Kubernetes": ["kubernetes", "k8s"],
    "AWS": ["aws", "amazon web services"],
    "Azure": ["azure", "microsoft azure"],
    "Linux": ["linux", "unix"],
    "Windows Server": ["windows server"],
    "Git": ["git", "github", "version control"],
    "CI/CD": ["ci/cd", "continuous integration", "continuous deployment", "github actions"],
    "Agile": ["agile", "scrum"],
    "Testing": ["testing", "unit testing", "automated testing", "test automation"],
    "Machine Learning": ["machine learning", "ml", "artificial intelligence", "ai"],
    "Data Pipelines": ["data pipeline", "data pipelines", "etl"],
    "Scripting": ["scripting", "automation scripting", "script"],
}


def _contains_term(text: str, term: str) -> bool:
    escaped_term = re.escape(term.lower())
    pattern = rf"(?<![a-zA-Z0-9]){escaped_term}(?![a-zA-Z0-9])"
    return re.search(pattern, text.lower()) is not None


def extract_skills(text: str) -> list[str]:
    """Extract normalized skills from raw job posting or resume text."""
    detected_skills: list[str] = []

    for skill_name, patterns in SKILL_PATTERNS.items():
        if any(_contains_term(text, pattern) for pattern in patterns):
            detected_skills.append(skill_name)

    return sorted(detected_skills)


def count_skills(texts: Iterable[str]) -> dict[str, int]:
    """Count how often each normalized skill appears across a group of texts."""
    skill_counter: Counter[str] = Counter()

    for text in texts:
        skill_counter.update(extract_skills(text))

    return dict(skill_counter.most_common())
