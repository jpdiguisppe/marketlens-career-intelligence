"""Resume file text extraction helpers.

This module extracts text from supported resume upload formats without saving
uploaded files or extracted text. It intentionally returns plain text only so
callers can decide whether to analyze, redact, or discard it.
"""

from __future__ import annotations

import os
from io import BytesIO

from docx import Document
from pypdf import PdfReader
from pypdf.errors import PdfReadError

SUPPORTED_RESUME_UPLOAD_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}


class ResumeFileExtractionError(ValueError):
    """Raised when uploaded resume text cannot be extracted safely."""


def _normalize_extracted_text(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()


def _extract_text_file(contents: bytes) -> str:
    try:
        return contents.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ResumeFileExtractionError("Resume text file must be UTF-8 encoded.") from exc


def _extract_docx_text(contents: bytes) -> str:
    try:
        document = Document(BytesIO(contents))
    except Exception as exc:  # python-docx raises package-specific errors from zip/xml parsing.
        raise ResumeFileExtractionError("Could not read text from this DOCX resume file.") from exc

    paragraphs = [paragraph.text for paragraph in document.paragraphs]

    table_cells: list[str] = []
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    table_cells.append(cell.text)

    return "\n".join(paragraphs + table_cells)


def _extract_pdf_text(contents: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(contents))
    except (PdfReadError, ValueError, OSError) as exc:
        raise ResumeFileExtractionError("Could not read text from this PDF resume file.") from exc

    page_text: list[str] = []
    for page in reader.pages:
        extracted_page_text = page.extract_text() or ""
        if extracted_page_text.strip():
            page_text.append(extracted_page_text)

    return "\n".join(page_text)


def extract_resume_text_from_upload(filename: str, contents: bytes) -> tuple[str, list[str]]:
    """Extract readable text and warnings from a supported resume upload."""

    extension = os.path.splitext(filename.lower())[1]
    warnings = [
        "Uploaded resume text is returned for this request and is not saved to the shared database."
    ]

    if extension not in SUPPORTED_RESUME_UPLOAD_EXTENSIONS:
        raise ResumeFileExtractionError(
            "Resume upload supports .txt, .md, .pdf, and .docx files."
        )

    if extension in {".txt", ".md"}:
        raw_text = _extract_text_file(contents)
    elif extension == ".docx":
        raw_text = _extract_docx_text(contents)
    elif extension == ".pdf":
        raw_text = _extract_pdf_text(contents)
        warnings.append(
            "PDF extraction depends on whether the PDF contains selectable text; scanned/image-only PDFs may not work."
        )
    else:
        raise ResumeFileExtractionError(
            "Resume upload supports .txt, .md, .pdf, and .docx files."
        )

    text = _normalize_extracted_text(raw_text)
    if not text:
        raise ResumeFileExtractionError(
            "Uploaded resume file did not contain readable text. Try exporting it as DOCX or plain text."
        )

    return text, warnings
