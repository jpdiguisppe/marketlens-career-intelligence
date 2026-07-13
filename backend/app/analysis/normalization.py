import re
import unicodedata

_PAGE_NUMBER_PATTERN = re.compile(r"^(?:page\s+)?\d+(?:\s+of\s+\d+)?$", re.IGNORECASE)
_BULLET_PATTERN = re.compile(r"^\s*[\u2022\u2023\u25e6\u2043\u2219\u25aa\u25cf\uf0b7*]+\s*")


def normalize_document_text(text: str) -> str:
    """Normalize pasted or extracted document text while preserving section boundaries."""
    normalized = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")

    # Repair words split by a PDF line wrap, such as "develop-\nment".
    normalized = re.sub(r"(?<=\w)-\n(?=[a-z])", "", normalized)
    normalized = normalized.replace("\t", " ")

    cleaned_lines: list[str] = []
    previous_was_blank = False

    for raw_line in normalized.split("\n"):
        line = re.sub(r"\s+", " ", raw_line).strip()

        if not line:
            if cleaned_lines and not previous_was_blank:
                cleaned_lines.append("")
            previous_was_blank = True
            continue

        if len(line) <= 18 and _PAGE_NUMBER_PATTERN.fullmatch(line):
            continue

        if _BULLET_PATTERN.match(raw_line):
            line = f"- {_BULLET_PATTERN.sub('', raw_line).strip()}"
            line = re.sub(r"\s+", " ", line)

        cleaned_lines.append(line)
        previous_was_blank = False

    return "\n".join(cleaned_lines).strip()


def meaningful_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def split_text_fragments(text: str) -> list[str]:
    """Split bullets and prose into small evidence-bearing fragments."""
    fragments: list[str] = []

    for line in meaningful_lines(text):
        cleaned_line = line.removeprefix("- ").strip()
        sentence_parts = re.split(r"(?<=[.!?])\s+|\s*;\s*", cleaned_line)
        fragments.extend(part.strip() for part in sentence_parts if part.strip())

    return fragments
