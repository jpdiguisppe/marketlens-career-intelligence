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


def _is_context_heading(value: str) -> bool:
    heading = value.strip()
    if not heading or len(heading) > 80:
        return False
    normalized = heading.lower().rstrip(":")
    return (
        heading.endswith(":")
        or heading.isupper()
        or normalized
        in {
            "skills",
            "technical skills",
            "required skills",
            "required qualifications",
            "preferred qualifications",
            "qualifications",
            "responsibilities",
            "coursework",
            "certifications",
            "certificates",
        }
    )


def _matched_segments(
    text: str,
    pattern: str,
    *,
    flags: int = re.IGNORECASE,
) -> list[str]:
    """Return the sentence/line containing each match plus a nearby heading."""
    segments: list[str] = []
    boundary_chars = "\n.!?;"
    for match in re.finditer(pattern, text, flags):
        previous_boundaries = [text.rfind(char, 0, match.start()) for char in boundary_chars]
        start = max(previous_boundaries) + 1

        following_boundaries = [
            position
            for char in boundary_chars
            if (position := text.find(char, match.end())) >= 0
        ]
        end = min(following_boundaries) if following_boundaries else len(text)
        segment = text[start:end].strip()

        line_start = text.rfind("\n", 0, start) + 1
        if start <= line_start:
            previous_line_end = max(0, line_start - 1)
            previous_line_start = text.rfind("\n", 0, previous_line_end) + 1
            previous_line = text[previous_line_start:previous_line_end].strip()
            if _is_context_heading(previous_line):
                segment = f"{previous_line} {segment}"

        segments.append(segment.lower())
    return segments


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
_C_LICENSE_PATTERNS = (
    r"\b(?:class|type|category|grade)\s+c\b",
    r"\bc\s+(?:driver'?s?\s+)?licen[cs]e\b",
)


def _detect_c_skill(text: str) -> bool:
    """Detect programming-language C without treating licenses or C# as C."""
    sanitized = re.sub(
        r"(?<![A-Za-z0-9])C#(?![A-Za-z0-9])",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    for license_pattern in _C_LICENSE_PATTERNS:
        sanitized = re.sub(license_pattern, " ", sanitized, flags=re.IGNORECASE)

    if _contains_term(sanitized, "c language") or _contains_term(
        sanitized,
        "programming in c",
    ):
        return True

    c_pattern = r"(?<![A-Za-z0-9+#])C(?![A-Za-z0-9+#])"
    for segment in _matched_segments(sanitized, c_pattern, flags=0):
        if "license" in segment or "licence" in segment:
            continue
        if any(anchor in segment for anchor in _C_PROGRAMMING_CONTEXT):
            return True
        if any(language in segment for language in _OTHER_PROGRAMMING_LANGUAGES):
            return True
    return False


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
    "automation",
    "automated",
    "test case",
    "test cases",
    "ci/cd",
    "python",
    "java",
    "javascript",
    "typescript",
    "react",
    "database",
)
_PHYSICAL_TESTING_CONTEXT = (
    "electrical equipment",
    "equipment",
    "installation",
    "standardized testing",
    "classroom",
    "assessment",
    "assessments",
    "laboratory",
    "manufacturing",
    "materials",
    "mechanical",
    "field testing",
    "inspection",
)


def _document_has_software_context(text: str) -> bool:
    normalized = f" {text.lower()} "
    return any(anchor in normalized for anchor in _SOFTWARE_TESTING_CONTEXT)


def _detect_testing_skill(text: str) -> bool:
    """Keep software-testing evidence while rejecting physical/classroom testing."""
    software_document = _document_has_software_context(text)
    patterns = sorted(SKILL_PATTERNS["Testing"], key=len, reverse=True)
    for term in patterns:
        for segment in _matched_segments(text, _term_pattern(term)):
            if any(anchor in segment for anchor in _PHYSICAL_TESTING_CONTEXT):
                continue
            if any(anchor in f" {segment} " for anchor in _SOFTWARE_TESTING_CONTEXT):
                return True
            if software_document and term != "testing":
                return True
    return False


_MACHINE_LEARNING_TERMS = (
    "machine learning",
    "artificial intelligence",
)
_MACHINE_LEARNING_TECHNICAL_CONTEXT = (
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
    "prototyping",
)
_MACHINE_LEARNING_EVIDENCE_CONTEXT = (
    "experience",
    "experienced",
    "proficiency",
    "proficient",
    "knowledge",
    "certificate",
    "certification",
    "coursework",
    "skills",
    "required",
    "preferred",
    "qualification",
    "qualifications",
    "responsibility",
    "responsibilities",
    "must",
)
_COMPANY_MARKETING_CONTEXT = (
    "our company",
    "company builds",
    "company uses",
    "company develops",
    "our products",
    "company products",
    "our platform",
    "our mission",
)
_AI_ML_PATTERNS = (
    r"(?<![A-Za-z0-9])AI\s*/\s*ML(?![A-Za-z0-9])",
    r"(?<![A-Za-z0-9])AI\s*(?:&|and)\s*ML(?![A-Za-z0-9])",
    r"(?<![A-Za-z0-9])(?:AI|ML)(?![A-Za-z0-9])",
)


def _machine_learning_segment_is_grounded(segment: str) -> bool:
    if any(anchor in segment for anchor in _MACHINE_LEARNING_TECHNICAL_CONTEXT):
        return True
    if any(anchor in segment for anchor in _MACHINE_LEARNING_EVIDENCE_CONTEXT):
        return not any(marker in segment for marker in _COMPANY_MARKETING_CONTEXT)
    if re.search(r"\buse\b", segment):
        return True
    return False


def _detect_machine_learning_skill(text: str) -> bool:
    """Require role-level evidence, not incidental company AI/ML marketing."""
    for term in _MACHINE_LEARNING_TERMS:
        for segment in _matched_segments(text, _term_pattern(term)):
            if _machine_learning_segment_is_grounded(segment):
                return True

    for pattern in _AI_ML_PATTERNS:
        for segment in _matched_segments(text, pattern, flags=0):
            if _machine_learning_segment_is_grounded(segment):
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
