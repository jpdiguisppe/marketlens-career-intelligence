from __future__ import annotations

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from pypdf import PdfWriter

from app.resume_files import (
    MAX_DOCX_ARCHIVE_ENTRIES,
    MAX_PDF_PAGES,
    ResumeFileExtractionError,
    extract_resume_text_from_upload,
)


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def test_docx_rejects_high_compression_ratio_before_document_parse() -> None:
    contents = _zip_bytes(
        {
            "[Content_Types].xml": b"<Types/>",
            "word/document.xml": b"A" * 1_000_000,
        }
    )
    with pytest.raises(ResumeFileExtractionError, match="compression ratio"):
        extract_resume_text_from_upload("resume.docx", contents)


def test_docx_rejects_excessive_archive_entry_count() -> None:
    entries = {
        "[Content_Types].xml": b"<Types/>",
        "word/document.xml": b"<document/>",
    }
    entries.update(
        {f"word/media/item-{index}.bin": b"x" for index in range(MAX_DOCX_ARCHIVE_ENTRIES)}
    )
    contents = _zip_bytes(entries)
    with pytest.raises(ResumeFileExtractionError, match="too many internal files"):
        extract_resume_text_from_upload("resume.docx", contents)


def test_docx_rejects_xml_entity_declarations() -> None:
    contents = _zip_bytes(
        {
            "[Content_Types].xml": b"<Types/>",
            "word/document.xml": b'<!DOCTYPE x [<!ENTITY y "boom">]><document>&y;</document>',
        }
    )
    with pytest.raises(ResumeFileExtractionError, match="XML entity"):
        extract_resume_text_from_upload("resume.docx", contents)


def test_pdf_rejects_excessive_page_count_before_text_extraction() -> None:
    writer = PdfWriter()
    for _ in range(MAX_PDF_PAGES + 1):
        writer.add_blank_page(width=612, height=792)
    buffer = BytesIO()
    writer.write(buffer)

    with pytest.raises(ResumeFileExtractionError, match="too many pages"):
        extract_resume_text_from_upload("resume.pdf", buffer.getvalue())


def test_file_extension_does_not_override_invalid_pdf_signature() -> None:
    with pytest.raises(ResumeFileExtractionError, match="structure is invalid"):
        extract_resume_text_from_upload("resume.pdf", b"this is not a pdf")
