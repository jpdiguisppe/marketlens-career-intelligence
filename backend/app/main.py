import csv
import io
from collections import defaultdict
from typing import List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field, ValidationError

from app.skill_extractor import count_skills, extract_skills

app = FastAPI(
    title="MarketLens API",
    description="Backend API for analyzing job postings and career skill signals.",
    version="0.4.0",
)


class JobPostingCreate(BaseModel):
    company: str = Field(..., examples=["Lockheed Martin"])
    title: str = Field(..., examples=["Software Engineer Associate"])
    location: Optional[str] = Field(default=None, examples=["Philadelphia, PA"])
    role_category: Optional[str] = Field(default=None, examples=["Backend SWE"])
    experience_level: Optional[str] = Field(default=None, examples=["Entry-Level"])
    description: str = Field(..., examples=["We are looking for a software engineer with Python, SQL, and Docker experience."])


class JobPosting(JobPostingCreate):
    id: int
    extracted_skills: list[str] = Field(default_factory=list)


class SkillExtractionRequest(BaseModel):
    text: str = Field(..., examples=["Experience with Python, SQL, Docker, AWS, and REST APIs preferred."])


class SkillExtractionResponse(BaseModel):
    skills: list[str]


class CSVImportResponse(BaseModel):
    imported_count: int
    failed_count: int
    created_postings: list[JobPosting]
    errors: list[str]


job_postings: List[JobPosting] = []
next_job_posting_id = 1

REQUIRED_CSV_COLUMNS = {"company", "title", "description"}
OPTIONAL_CSV_COLUMNS = {"location", "role_category", "experience_level"}
SUPPORTED_CSV_COLUMNS = REQUIRED_CSV_COLUMNS | OPTIONAL_CSV_COLUMNS


def _create_job_posting(posting: JobPostingCreate) -> JobPosting:
    global next_job_posting_id

    created_posting = JobPosting(
        id=next_job_posting_id,
        extracted_skills=extract_skills(posting.description),
        **posting.model_dump(),
    )
    job_postings.append(created_posting)
    next_job_posting_id += 1

    return created_posting


def _group_skill_counts_by_posting_field(field_name: str) -> dict[str, dict[str, int]]:
    grouped_descriptions: dict[str, list[str]] = defaultdict(list)

    for posting in job_postings:
        group_name = getattr(posting, field_name) or "Uncategorized"
        grouped_descriptions[group_name].append(posting.description)

    return {
        group_name: count_skills(descriptions)
        for group_name, descriptions in grouped_descriptions.items()
    }


def _normalize_csv_fieldnames(fieldnames: list[str]) -> dict[str, str]:
    return {
        fieldname.strip().lower(): fieldname
        for fieldname in fieldnames
        if fieldname and fieldname.strip()
    }


def _get_csv_value(row: dict[str, str], normalized_fieldnames: dict[str, str], field_name: str) -> str | None:
    original_fieldname = normalized_fieldnames.get(field_name)
    if original_fieldname is None:
        return None

    value = row.get(original_fieldname)
    if value is None:
        return None

    cleaned_value = value.strip()
    return cleaned_value or None


def _get_required_csv_value(row: dict[str, str], normalized_fieldnames: dict[str, str], field_name: str, row_number: int) -> str:
    value = _get_csv_value(row, normalized_fieldnames, field_name)
    if value is None:
        raise ValueError(f"Row {row_number}: missing required field '{field_name}'")

    return value


def _posting_from_csv_row(row: dict[str, str], normalized_fieldnames: dict[str, str], row_number: int) -> JobPostingCreate:
    return JobPostingCreate(
        company=_get_required_csv_value(row, normalized_fieldnames, "company", row_number),
        title=_get_required_csv_value(row, normalized_fieldnames, "title", row_number),
        description=_get_required_csv_value(row, normalized_fieldnames, "description", row_number),
        location=_get_csv_value(row, normalized_fieldnames, "location"),
        role_category=_get_csv_value(row, normalized_fieldnames, "role_category"),
        experience_level=_get_csv_value(row, normalized_fieldnames, "experience_level"),
    )


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Welcome to the MarketLens API",
        "docs": "/docs",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/job-postings", response_model=JobPosting, status_code=201)
def create_job_posting(posting: JobPostingCreate) -> JobPosting:
    return _create_job_posting(posting)


@app.get("/job-postings", response_model=list[JobPosting])
def list_job_postings() -> list[JobPosting]:
    return job_postings


@app.post("/job-postings/import-csv", response_model=CSVImportResponse, status_code=201)
async def import_job_postings_from_csv(file: UploadFile = File(...)) -> CSVImportResponse:
    file_contents = await file.read()

    if not file_contents:
        raise HTTPException(status_code=400, detail="Uploaded CSV file is empty")

    try:
        csv_text = file_contents.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV file must be UTF-8 encoded") from exc

    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames is None:
        raise HTTPException(status_code=400, detail="CSV file must include a header row")

    normalized_fieldnames = _normalize_csv_fieldnames(reader.fieldnames)
    missing_required_columns = sorted(REQUIRED_CSV_COLUMNS - set(normalized_fieldnames.keys()))

    if missing_required_columns:
        raise HTTPException(
            status_code=400,
            detail=f"CSV file is missing required columns: {', '.join(missing_required_columns)}",
        )

    unsupported_columns = sorted(set(normalized_fieldnames.keys()) - SUPPORTED_CSV_COLUMNS)
    created_postings: list[JobPosting] = []
    errors: list[str] = []

    for row_number, row in enumerate(reader, start=2):
        if not any(value and value.strip() for value in row.values()):
            continue

        try:
            posting_create = _posting_from_csv_row(row, normalized_fieldnames, row_number)
            created_postings.append(_create_job_posting(posting_create))
        except (ValueError, ValidationError) as exc:
            errors.append(str(exc))

    if unsupported_columns:
        errors.insert(
            0,
            f"Ignored unsupported columns: {', '.join(unsupported_columns)}",
        )

    return CSVImportResponse(
        imported_count=len(created_postings),
        failed_count=len(errors),
        created_postings=created_postings,
        errors=errors,
    )


@app.get("/job-postings/{posting_id}", response_model=JobPosting)
def get_job_posting(posting_id: int) -> JobPosting:
    for posting in job_postings:
        if posting.id == posting_id:
            return posting

    raise HTTPException(status_code=404, detail="Job posting not found")


@app.post("/skills/extract", response_model=SkillExtractionResponse)
def extract_skills_from_text(request: SkillExtractionRequest) -> SkillExtractionResponse:
    return SkillExtractionResponse(skills=extract_skills(request.text))


@app.get("/skills/top")
def get_top_skills() -> dict[str, int]:
    descriptions = [posting.description for posting in job_postings]
    return count_skills(descriptions)


@app.get("/skills/top-by-company")
def get_top_skills_by_company() -> dict[str, dict[str, int]]:
    return _group_skill_counts_by_posting_field("company")


@app.get("/skills/top-by-role")
def get_top_skills_by_role() -> dict[str, dict[str, int]]:
    return _group_skill_counts_by_posting_field("role_category")
