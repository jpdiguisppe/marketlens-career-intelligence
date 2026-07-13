import re

from app.analysis.schemas import DocumentKind, ParsedSection, SectionKind

_RESUME_HEADINGS: dict[str, SectionKind] = {
    "summary": SectionKind.SUMMARY,
    "professional summary": SectionKind.SUMMARY,
    "profile": SectionKind.SUMMARY,
    "objective": SectionKind.SUMMARY,
    "skills": SectionKind.SKILLS,
    "technical skills": SectionKind.SKILLS,
    "technical proficiencies": SectionKind.SKILLS,
    "core competencies": SectionKind.SKILLS,
    "technologies": SectionKind.SKILLS,
    "experience": SectionKind.EXPERIENCE,
    "work experience": SectionKind.EXPERIENCE,
    "professional experience": SectionKind.EXPERIENCE,
    "employment history": SectionKind.EXPERIENCE,
    "projects": SectionKind.PROJECTS,
    "technical projects": SectionKind.PROJECTS,
    "selected projects": SectionKind.PROJECTS,
    "education": SectionKind.EDUCATION,
    "coursework": SectionKind.COURSEWORK,
    "relevant coursework": SectionKind.COURSEWORK,
    "certifications": SectionKind.CERTIFICATIONS,
    "licenses and certifications": SectionKind.CERTIFICATIONS,
    "awards": SectionKind.AWARDS,
    "honors": SectionKind.AWARDS,
    "honors and awards": SectionKind.AWARDS,
}

_JOB_HEADINGS: dict[str, SectionKind] = {
    "about us": SectionKind.COMPANY,
    "who we are": SectionKind.COMPANY,
    "company overview": SectionKind.COMPANY,
    "about the company": SectionKind.COMPANY,
    "about the role": SectionKind.SUMMARY,
    "the role": SectionKind.SUMMARY,
    "role overview": SectionKind.SUMMARY,
    "position summary": SectionKind.SUMMARY,
    "job summary": SectionKind.SUMMARY,
    "overview": SectionKind.SUMMARY,
    "what you'll do": SectionKind.RESPONSIBILITIES,
    "what you will do": SectionKind.RESPONSIBILITIES,
    "what you’ll do": SectionKind.RESPONSIBILITIES,
    "responsibilities": SectionKind.RESPONSIBILITIES,
    "key responsibilities": SectionKind.RESPONSIBILITIES,
    "your impact": SectionKind.RESPONSIBILITIES,
    "what we're looking for": SectionKind.REQUIRED,
    "what we are looking for": SectionKind.REQUIRED,
    "what we’re looking for": SectionKind.REQUIRED,
    "requirements": SectionKind.REQUIRED,
    "qualifications": SectionKind.REQUIRED,
    "minimum qualifications": SectionKind.REQUIRED,
    "required qualifications": SectionKind.REQUIRED,
    "basic qualifications": SectionKind.REQUIRED,
    "what you'll bring": SectionKind.REQUIRED,
    "what you will bring": SectionKind.REQUIRED,
    "preferred qualifications": SectionKind.PREFERRED,
    "preferred skills": SectionKind.PREFERRED,
    "nice to have": SectionKind.PREFERRED,
    "nice-to-have": SectionKind.PREFERRED,
    "bonus points": SectionKind.PREFERRED,
    "desired qualifications": SectionKind.PREFERRED,
    "benefits": SectionKind.BENEFITS,
    "what we offer": SectionKind.BENEFITS,
    "compensation and benefits": SectionKind.BENEFITS,
}


def _normalize_heading(value: str) -> str:
    value = value.strip().strip(":").lower()
    value = value.replace("&", "and")
    value = re.sub(r"[^a-z0-9+'’\- ]", "", value)
    return re.sub(r"\s+", " ", value).strip()


def _detect_heading(line: str, heading_map: dict[str, SectionKind]) -> tuple[str, SectionKind, str] | None:
    normalized_line = _normalize_heading(line)
    if normalized_line in heading_map:
        return line.strip().strip(":"), heading_map[normalized_line], ""

    if ":" in line:
        possible_heading, remainder = line.split(":", maxsplit=1)
        normalized_heading = _normalize_heading(possible_heading)
        if normalized_heading in heading_map:
            return possible_heading.strip(), heading_map[normalized_heading], remainder.strip()

    return None


def parse_sections(text: str, document_kind: DocumentKind) -> list[ParsedSection]:
    heading_map = _RESUME_HEADINGS if document_kind == DocumentKind.RESUME else _JOB_HEADINGS
    lines = text.splitlines()
    sections: list[ParsedSection] = []

    current_kind = SectionKind.OTHER
    current_heading: str | None = None
    current_start_line = 1
    current_lines: list[str] = []

    def flush(end_line: int) -> None:
        nonlocal current_lines
        section_text = "\n".join(current_lines).strip()
        if section_text:
            sections.append(
                ParsedSection(
                    kind=current_kind,
                    heading=current_heading,
                    text=section_text,
                    start_line=current_start_line,
                    end_line=max(current_start_line, end_line),
                )
            )
        current_lines = []

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue

        heading = _detect_heading(line, heading_map)
        if heading is None:
            current_lines.append(line.strip())
            continue

        flush(line_number - 1)
        heading_text, current_kind, remainder = heading
        current_heading = heading_text
        current_start_line = line_number
        if remainder:
            current_lines.append(remainder)

    flush(len(lines))

    if not sections and text.strip():
        return [
            ParsedSection(
                kind=SectionKind.OTHER,
                heading=None,
                text=text.strip(),
                start_line=1,
                end_line=max(1, len(lines)),
            )
        ]

    return sections


def parse_resume_sections(text: str) -> list[ParsedSection]:
    return parse_sections(text, DocumentKind.RESUME)


def parse_job_sections(text: str) -> list[ParsedSection]:
    return parse_sections(text, DocumentKind.JOB_POSTING)
