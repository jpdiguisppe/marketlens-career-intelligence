import csv
import io
import os
import secrets
import time
from collections import defaultdict
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import JobPostingDB
from app.skill_extractor import count_skills, extract_skills

Base.metadata.create_all(bind=engine)

ADMIN_API_KEY_ENV = "ADMIN_API_KEY"
MAX_CSV_FILE_SIZE_BYTES = 1_000_000
MAX_CSV_ROWS = 250
MAX_FREE_TEXT_LENGTH = 10_000
MAX_POSTING_DESCRIPTION_LENGTH = 5_000
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 30

REQUIRED_CSV_COLUMNS = {"company", "title", "description"}
OPTIONAL_CSV_COLUMNS = {"location", "role_category", "experience_level"}
SUPPORTED_CSV_COLUMNS = REQUIRED_CSV_COLUMNS | OPTIONAL_CSV_COLUMNS

_rate_limit_buckets: dict[str, list[float]] = {}


def _get_allowed_origins() -> list[str]:
    configured_origins = os.getenv("CORS_ALLOWED_ORIGINS")

    if configured_origins:
        return [
            origin.strip().rstrip("/")
            for origin in configured_origins.split(",")
            if origin.strip()
        ]

    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def require_admin_api_key(
    x_admin_api_key: Annotated[str | None, Header(alias="X-Admin-API-Key")] = None,
) -> None:
    """Protect admin-only write endpoints with a server-side API key."""
    expected_api_key = os.getenv(ADMIN_API_KEY_ENV)

    if not expected_api_key:
        raise HTTPException(
            status_code=503,
            detail="Admin API key is not configured for this deployment.",
        )

    if x_admin_api_key is None or not secrets.compare_digest(x_admin_api_key, expected_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing admin API key.")


def _get_rate_limit_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()

    if request.client and request.client.host:
        return request.client.host

    return "unknown-client"


def enforce_public_rate_limit(request: Request) -> None:
    """Small in-memory fixed-window rate limit for public analysis endpoints."""
    identifier = _get_rate_limit_identifier(request)
    now = time.monotonic()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS

    request_timestamps = _rate_limit_buckets.setdefault(identifier, [])
    request_timestamps[:] = [
        timestamp for timestamp in request_timestamps if timestamp >= window_start
    ]

    if len(request_timestamps) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait before trying again.",
        )

    request_timestamps.append(now)


app = FastAPI(
    title="MarketLens API",
    description="Backend API for analyzing job postings and career skill signals.",
    version="0.7.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class JobPostingCreate(BaseModel):
    company: str = Field(..., min_length=1, max_length=100, examples=["Lockheed Martin"])
    title: str = Field(..., min_length=1, max_length=150, examples=["Software Engineer Associate"])
    location: Optional[str] = Field(default=None, max_length=120, examples=["Philadelphia, PA"])
    role_category: Optional[str] = Field(default=None, max_length=80, examples=["Backend SWE"])
    experience_level: Optional[str] = Field(default=None, max_length=80, examples=["Entry-Level"])
    description: str = Field(
        ...,
        min_length=1,
        max_length=MAX_POSTING_DESCRIPTION_LENGTH,
        examples=["We are looking for a software engineer with Python, SQL, and Docker experience."],
    )


class JobPosting(JobPostingCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    extracted_skills: list[str] = Field(default_factory=list)


class SkillExtractionRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=MAX_FREE_TEXT_LENGTH,
        examples=["Experience with Python, SQL, Docker, AWS, and REST APIs preferred."],
    )


class SkillExtractionResponse(BaseModel):
    skills: list[str]


class CSVImportResponse(BaseModel):
    imported_count: int
    failed_count: int
    created_postings: list[JobPosting]
    errors: list[str]


class ResumeAnalysisRequest(BaseModel):
    resume_text: str = Field(
        ...,
        min_length=1,
        max_length=MAX_FREE_TEXT_LENGTH,
        examples=["Python, Java, SQL, React, Git, Agile, and REST API project experience."],
    )
    target_role_category: Optional[str] = Field(
        default=None,
        max_length=80,
        examples=["Backend SWE"],
        description="Optional role category to compare against. If omitted, all saved postings are used.",
    )


class ResumeAnalysisResponse(BaseModel):
    resume_skills: list[str]
    target_skills: list[str]
    matched_skills: list[str]
    missing_skills: list[str]
    match_percentage: float
    learning_priorities: list[str]
    postings_analyzed: int
    target_role_category: Optional[str]


def _to_api_job_posting(posting: JobPostingDB) -> JobPosting:
    return JobPosting.model_validate(posting)


def _create_job_posting(db: Session, posting: JobPostingCreate) -> JobPosting:
    db_posting = JobPostingDB(
        company=posting.company,
        title=posting.title,
        location=posting.location,
        role_category=posting.role_category,
        experience_level=posting.experience_level,
        description=posting.description,
    )
    db_posting.extracted_skills = extract_skills(posting.description)

    db.add(db_posting)
    db.commit()
    db.refresh(db_posting)

    return _to_api_job_posting(db_posting)


def _list_db_postings(db: Session) -> list[JobPostingDB]:
    return db.query(JobPostingDB).order_by(JobPostingDB.id).all()


def _group_skill_counts_by_posting_field(db: Session, field_name: str) -> dict[str, dict[str, int]]:
    grouped_descriptions: dict[str, list[str]] = defaultdict(list)

    for posting in _list_db_postings(db):
        group_name = getattr(posting, field_name) or "Uncategorized"
        grouped_descriptions[group_name].append(posting.description)

    return {
        group_name: count_skills(descriptions)
        for group_name, descriptions in grouped_descriptions.items()
    }


def _sort_skills_by_target_frequency(skills: set[str], target_skill_counts: dict[str, int]) -> list[str]:
    return sorted(
        skills,
        key=lambda skill: (-target_skill_counts.get(skill, 0), skill.lower()),
    )


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


@app.post(
    "/job-postings",
    response_model=JobPosting,
    status_code=201,
    dependencies=[Depends(require_admin_api_key)],
)
def create_job_posting(posting: JobPostingCreate, db: Session = Depends(get_db)) -> JobPosting:
    return _create_job_posting(db, posting)


@app.get("/job-postings", response_model=list[JobPosting])
def list_job_postings(db: Session = Depends(get_db)) -> list[JobPosting]:
    return [_to_api_job_posting(posting) for posting in _list_db_postings(db)]


@app.post(
    "/job-postings/import-csv",
    response_model=CSVImportResponse,
    status_code=201,
    dependencies=[Depends(require_admin_api_key)],
)
async def import_job_postings_from_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> CSVImportResponse:
    file_contents = await file.read()

    if not file_contents:
        raise HTTPException(status_code=400, detail="Uploaded CSV file is empty")

    if len(file_contents) > MAX_CSV_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"CSV file is too large. Maximum size is {MAX_CSV_FILE_SIZE_BYTES} bytes.",
        )

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
    non_empty_row_count = 0

    for row_number, row in enumerate(reader, start=2):
        if not any(value and value.strip() for value in row.values()):
            continue

        non_empty_row_count += 1
        if non_empty_row_count > MAX_CSV_ROWS:
            raise HTTPException(
                status_code=400,
                detail=f"CSV file may include at most {MAX_CSV_ROWS} non-empty data rows.",
            )

        try:
            posting_create = _posting_from_csv_row(row, normalized_fieldnames, row_number)
            created_postings.append(_create_job_posting(db, posting_create))
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
def get_job_posting(posting_id: int, db: Session = Depends(get_db)) -> JobPosting:
    posting = db.get(JobPostingDB, posting_id)

    if posting is None:
        raise HTTPException(status_code=404, detail="Job posting not found")

    return _to_api_job_posting(posting)


@app.delete(
    "/job-postings",
    status_code=204,
    dependencies=[Depends(require_admin_api_key)],
)
def delete_all_job_postings(db: Session = Depends(get_db)) -> None:
    db.query(JobPostingDB).delete()
    db.commit()


@app.post(
    "/skills/extract",
    response_model=SkillExtractionResponse,
    dependencies=[Depends(enforce_public_rate_limit)],
)
def extract_skills_from_text(request: SkillExtractionRequest) -> SkillExtractionResponse:
    return SkillExtractionResponse(skills=extract_skills(request.text))


@app.get("/skills/top")
def get_top_skills(db: Session = Depends(get_db)) -> dict[str, int]:
    descriptions = [posting.description for posting in _list_db_postings(db)]
    return count_skills(descriptions)


@app.get("/skills/top-by-company")
def get_top_skills_by_company(db: Session = Depends(get_db)) -> dict[str, dict[str, int]]:
    return _group_skill_counts_by_posting_field(db, "company")


@app.get("/skills/top-by-role")
def get_top_skills_by_role(db: Session = Depends(get_db)) -> dict[str, dict[str, int]]:
    return _group_skill_counts_by_posting_field(db, "role_category")


@app.post(
    "/resume/analyze",
    response_model=ResumeAnalysisResponse,
    dependencies=[Depends(enforce_public_rate_limit)],
)
def analyze_resume(request: ResumeAnalysisRequest, db: Session = Depends(get_db)) -> ResumeAnalysisResponse:
    all_postings = _list_db_postings(db)
    target_postings = all_postings

    if request.target_role_category:
        target_postings = [
            posting
            for posting in all_postings
            if posting.role_category == request.target_role_category
        ]

    if not target_postings:
        raise HTTPException(
            status_code=400,
            detail="No saved job postings found for that target role category.",
        )

    resume_skills = extract_skills(request.resume_text)
    resume_skill_set = set(resume_skills)

    target_descriptions = [posting.description for posting in target_postings]
    target_skill_counts = count_skills(target_descriptions)
    target_skills = list(target_skill_counts.keys())
    target_skill_set = set(target_skills)

    matched_skill_set = resume_skill_set & target_skill_set
    missing_skill_set = target_skill_set - resume_skill_set

    matched_skills = _sort_skills_by_target_frequency(matched_skill_set, target_skill_counts)
    missing_skills = _sort_skills_by_target_frequency(missing_skill_set, target_skill_counts)

    match_percentage = 0.0
    if target_skills:
        match_percentage = round((len(matched_skills) / len(target_skills)) * 100, 1)

    return ResumeAnalysisResponse(
        resume_skills=resume_skills,
        target_skills=target_skills,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        match_percentage=match_percentage,
        learning_priorities=missing_skills[:5],
        postings_analyzed=len(target_postings),
        target_role_category=request.target_role_category,
    )
