import csv
import io
import os
import secrets
import time
from collections import defaultdict
from typing import Annotated, Literal, Optional

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from app.analysis import (
    AnalysisInputError,
    SmartFitAnalysisRequest,
    SmartFitAnalysisResponse,
    analyze_smart_fit,
)
from app.analysis.model_extractor import is_model_assisted_configured
from app.database import Base, engine, get_db
from app.job_search import ExternalJobResult, JobSearchResults, search_external_jobs
from app.models import JobPostingDB
from app.resume_files import ResumeFileExtractionError, extract_resume_text_from_upload
from app.skill_extractor import count_skills, extract_skills

Base.metadata.create_all(bind=engine)

ADMIN_API_KEY_ENV = "ADMIN_API_KEY"
MAX_CSV_FILE_SIZE_BYTES = 1_000_000
MAX_CSV_ROWS = 250
MAX_FREE_TEXT_LENGTH = 10_000
MAX_POSTING_DESCRIPTION_LENGTH = 5_000
MAX_CUSTOM_JOB_DESCRIPTIONS = 10
MAX_SMART_JOB_DESCRIPTION_LENGTH = 50_000
MAX_SMART_BATCH_JOBS = 10
MAX_RESUME_UPLOAD_BYTES = 1_500_000
MAX_EXTRACTED_RESUME_TEXT_LENGTH = 25_000
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 30

REQUIRED_CSV_COLUMNS = {"company", "title", "description"}
OPTIONAL_CSV_COLUMNS = {"location", "role_category", "experience_level"}
SUPPORTED_CSV_COLUMNS = REQUIRED_CSV_COLUMNS | OPTIONAL_CSV_COLUMNS

JobSearchLevel = Literal["any", "intern", "entry", "mid", "senior"]

CustomJobDescription = Annotated[
    str,
    Field(min_length=1, max_length=MAX_POSTING_DESCRIPTION_LENGTH),
]
SmartJobDescription = Annotated[
    str,
    Field(min_length=1, max_length=MAX_SMART_JOB_DESCRIPTION_LENGTH),
]

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
    version="0.9.0",
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


class CustomAnalysisRequest(BaseModel):
    resume_text: str = Field(
        ...,
        min_length=1,
        max_length=MAX_FREE_TEXT_LENGTH,
        examples=["Python, SQL, Git, Agile, REST APIs, and Docker project experience."],
    )
    job_descriptions: list[CustomJobDescription] = Field(
        ...,
        min_length=1,
        max_length=MAX_CUSTOM_JOB_DESCRIPTIONS,
        examples=[[
            "Backend role requiring Python, SQL, REST APIs, Docker, and Agile experience.",
            "Cloud role requiring AWS, Linux, CI/CD, scripting, and automation.",
        ]],
        description="One or more pasted job descriptions to analyze without saving to the database.",
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


class ResumeFileExtractionResponse(BaseModel):
    filename: str
    text: str
    character_count: int
    warnings: list[str] = Field(default_factory=list)


class ModelAssistedStatusResponse(BaseModel):
    enabled: bool
    status: str
    required_backend_settings: list[str]
    safety_notes: list[str]


class ExternalJobPostingResponse(BaseModel):
    id: str
    source: str
    company: str
    title: str
    location: str | None
    description: str
    apply_url: str
    updated_at: str | None
    extracted_skills: list[str]


class SourceCoverageResponse(BaseModel):
    provider: str
    label: str
    status: str
    fetched_count: int
    matched_count: int
    notes: list[str]


class ExternalSearchLinkResponse(BaseModel):
    label: str
    url: str
    note: str


class ExternalJobSearchResponse(BaseModel):
    query: str
    location: str | None
    level: JobSearchLevel
    role_family: str | None
    providers_searched: list[str]
    result_count: int
    results: list[ExternalJobPostingResponse]
    warnings: list[str]
    source_coverage: list[SourceCoverageResponse]
    search_suggestions: list[str]
    external_search_links: list[ExternalSearchLinkResponse]


class SmartFitBatchJobDescription(BaseModel):
    title: str | None = Field(default=None, max_length=150)
    job_description: SmartJobDescription


class SmartFitBatchAnalysisRequest(BaseModel):
    resume_text: str = Field(
        ...,
        min_length=1,
        max_length=MAX_EXTRACTED_RESUME_TEXT_LENGTH,
        description="Resume text to compare against each job description. It is not saved to the shared database.",
    )
    job_descriptions: list[SmartFitBatchJobDescription] = Field(
        ...,
        min_length=1,
        max_length=MAX_SMART_BATCH_JOBS,
        description="One to ten job descriptions. Each job is analyzed and ranked independently.",
    )
    use_model_assisted: bool = Field(
        default=False,
        description="When true, the backend may use the configured model-assisted extractor for each job. If unavailable, deterministic analysis is used.",
    )


class SmartFitBatchResult(BaseModel):
    rank: int
    job_index: int
    title: str
    analysis: SmartFitAnalysisResponse


class SmartFitBatchAnalysisResponse(BaseModel):
    analyzed_count: int
    results: list[SmartFitBatchResult]
    best_job: SmartFitBatchResult


def _model_assisted_status_response() -> ModelAssistedStatusResponse:
    enabled = is_model_assisted_configured()
    return ModelAssistedStatusResponse(
        enabled=enabled,
        status="configured" if enabled else "not_configured",
        required_backend_settings=[
            "AI_ANALYSIS_ENABLED=true",
            "OPENAI_API_KEY",
            "OPENAI_MODEL",
        ],
        safety_notes=[
            "Provider keys must stay in backend environment variables only.",
            "MarketLens redacts obvious contact details before model-provider calls.",
            "Raw resume and job text are not saved to the shared database.",
            "Model-assisted extraction falls back to deterministic analysis when unavailable.",
        ],
    )


def _infer_batch_job_title(job: SmartFitBatchJobDescription, index: int) -> str:
    if job.title and job.title.strip():
        return job.title.strip()

    ignored_headings = {
        "responsibilities",
        "requirements",
        "required qualifications",
        "preferred qualifications",
        "qualifications",
        "about the role",
        "what you'll do",
        "what we're looking for",
    }
    for line in job.job_description.splitlines():
        cleaned_line = line.strip()
        if cleaned_line and cleaned_line.lower().rstrip(":") not in ignored_headings:
            return cleaned_line[:90]

    return f"Job {index + 1}"


def _rank_smart_fit_batch_results(results: list[SmartFitBatchResult]) -> list[SmartFitBatchResult]:
    ranked_results = sorted(
        results,
        key=lambda result: (
            -result.analysis.fit_summary.score,
            -result.analysis.fit_summary.confidence,
            result.job_index,
        ),
    )

    return [
        SmartFitBatchResult(
            rank=index + 1,
            job_index=result.job_index,
            title=result.title,
            analysis=result.analysis,
        )
        for index, result in enumerate(ranked_results)
    ]


def _to_api_job_posting(posting: JobPostingDB) -> JobPosting:
    return JobPosting.model_validate(posting)


def _to_external_job_response(job: ExternalJobResult) -> ExternalJobPostingResponse:
    return ExternalJobPostingResponse(
        id=job.id,
        source=job.source,
        company=job.company,
        title=job.title,
        location=job.location,
        description=job.description,
        apply_url=job.apply_url,
        updated_at=job.updated_at,
        extracted_skills=extract_skills(job.description),
    )


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


def _build_resume_analysis_response(
    resume_text: str,
    target_descriptions: list[str],
    postings_analyzed: int,
    target_role_category: Optional[str] = None,
) -> ResumeAnalysisResponse:
    resume_skills = extract_skills(resume_text)
    resume_skill_set = set(resume_skills)

    target_skill_counts = count_skills(target_descriptions)
    target_skills = list(target_skill_counts.keys())
    target_skill_set = set(target_skills)

    matched_skills = _sort_skills_by_target_frequency(
        resume_skill_set & target_skill_set,
        target_skill_counts,
    )
    missing_skills = _sort_skills_by_target_frequency(
        target_skill_set - resume_skill_set,
        target_skill_counts,
    )

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
        postings_analyzed=postings_analyzed,
        target_role_category=target_role_category,
    )


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/analysis/model-status", response_model=ModelAssistedStatusResponse)
def model_assisted_status() -> ModelAssistedStatusResponse:
    return _model_assisted_status_response()


@app.post("/postings", response_model=JobPosting, dependencies=[Depends(require_admin_api_key)])
def create_job_posting(posting: JobPostingCreate, db: Session = Depends(get_db)) -> JobPosting:
    return _create_job_posting(db, posting)


@app.get("/postings", response_model=list[JobPosting])
def list_job_postings(db: Session = Depends(get_db)) -> list[JobPosting]:
    postings = _list_db_postings(db)
    return [_to_api_job_posting(posting) for posting in postings]


@app.get("/skills/top", response_model=dict[str, int])
def top_skills(db: Session = Depends(get_db)) -> dict[str, int]:
    descriptions = [posting.description for posting in _list_db_postings(db)]
    return count_skills(descriptions)


@app.get("/skills/by-company", response_model=dict[str, dict[str, int]])
def skills_by_company(db: Session = Depends(get_db)) -> dict[str, dict[str, int]]:
    return _group_skill_counts_by_posting_field(db, "company")


@app.get("/skills/by-role", response_model=dict[str, dict[str, int]])
def skills_by_role(db: Session = Depends(get_db)) -> dict[str, dict[str, int]]:
    return _group_skill_counts_by_posting_field(db, "role_category")


@app.get("/postings/{posting_id}", response_model=JobPosting)
def get_job_posting(posting_id: int, db: Session = Depends(get_db)) -> JobPosting:
    posting = db.get(JobPostingDB, posting_id)
    if posting is None:
        raise HTTPException(status_code=404, detail="Job posting not found.")

    return _to_api_job_posting(posting)


@app.delete("/postings/{posting_id}", dependencies=[Depends(require_admin_api_key)])
def delete_job_posting(posting_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    posting = db.get(JobPostingDB, posting_id)
    if posting is None:
        raise HTTPException(status_code=404, detail="Job posting not found.")

    db.delete(posting)
    db.commit()

    return {"status": "deleted"}


@app.post("/skills/extract", response_model=SkillExtractionResponse)
def extract_skills_endpoint(request: SkillExtractionRequest) -> SkillExtractionResponse:
    return SkillExtractionResponse(skills=extract_skills(request.text))


@app.post("/import/csv", response_model=CSVImportResponse, dependencies=[Depends(require_admin_api_key)])
async def import_postings_csv(file: UploadFile = File(...), db: Session = Depends(get_db)) -> CSVImportResponse:
    content = await file.read(MAX_CSV_FILE_SIZE_BYTES + 1)

    if len(content) > MAX_CSV_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="CSV file is too large. Maximum size is 1 MB.")

    try:
        decoded_content = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded.") from exc

    reader = csv.DictReader(io.StringIO(decoded_content))
    if reader.fieldnames is None:
        raise HTTPException(status_code=400, detail="CSV must include a header row.")

    csv_columns = {column.strip() for column in reader.fieldnames if column is not None}
    missing_columns = REQUIRED_CSV_COLUMNS - csv_columns
    unsupported_columns = csv_columns - SUPPORTED_CSV_COLUMNS

    if missing_columns:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {sorted(missing_columns)}")

    if unsupported_columns:
        raise HTTPException(status_code=400, detail=f"Unsupported columns: {sorted(unsupported_columns)}")

    created_postings: list[JobPosting] = []
    errors: list[str] = []

    for row_number, row in enumerate(reader, start=2):
        if row_number - 1 > MAX_CSV_ROWS:
            errors.append(f"Row {row_number}: skipped because the maximum row limit is {MAX_CSV_ROWS}.")
            break

        try:
            posting = JobPostingCreate(
                company=(row.get("company") or "").strip(),
                title=(row.get("title") or "").strip(),
                location=(row.get("location") or "").strip() or None,
                role_category=(row.get("role_category") or "").strip() or None,
                experience_level=(row.get("experience_level") or "").strip() or None,
                description=(row.get("description") or "").strip(),
            )
        except ValidationError as exc:
            errors.append(f"Row {row_number}: {exc.errors()[0]['msg']}")
            continue

        created_postings.append(_create_job_posting(db, posting))

    return CSVImportResponse(
        imported_count=len(created_postings),
        failed_count=len(errors),
        created_postings=created_postings,
        errors=errors,
    )


@app.post("/analysis/resume", response_model=ResumeAnalysisResponse)
def analyze_resume(request: ResumeAnalysisRequest, db: Session = Depends(get_db)) -> ResumeAnalysisResponse:
    query = db.query(JobPostingDB)
    if request.target_role_category:
        query = query.filter(JobPostingDB.role_category == request.target_role_category)

    postings = query.all()
    if not postings:
        raise HTTPException(status_code=404, detail="No job postings found for the requested analysis.")

    return _build_resume_analysis_response(
        resume_text=request.resume_text,
        target_descriptions=[posting.description for posting in postings],
        postings_analyzed=len(postings),
        target_role_category=request.target_role_category,
    )


@app.post(
    "/analysis/resume-file/extract",
    response_model=ResumeFileExtractionResponse,
    dependencies=[Depends(enforce_public_rate_limit)],
)
async def extract_resume_file(file: UploadFile = File(...)) -> ResumeFileExtractionResponse:
    try:
        result = await extract_resume_text_from_upload(
            file=file,
            max_upload_bytes=MAX_RESUME_UPLOAD_BYTES,
            max_extracted_characters=MAX_EXTRACTED_RESUME_TEXT_LENGTH,
        )
    except ResumeFileExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ResumeFileExtractionResponse(
        filename=result.filename,
        text=result.text,
        character_count=result.character_count,
        warnings=result.warnings,
    )


@app.get(
    "/jobs/search",
    response_model=ExternalJobSearchResponse,
    dependencies=[Depends(enforce_public_rate_limit)],
)
def search_external_job_postings(
    query: Annotated[str, Query(min_length=1, max_length=100)],
    location: Annotated[str | None, Query(max_length=120)] = None,
    level: Annotated[
        JobSearchLevel | None,
        Query(description="Optional experience level filter: any, intern, entry, mid, or senior."),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 15,
) -> ExternalJobSearchResponse:
    search_results: JobSearchResults = search_external_jobs(query=query, location=location, level=level, limit=limit)
    api_results = [_to_external_job_response(job) for job in search_results.results]
    return ExternalJobSearchResponse(
        query=search_results.query,
        location=search_results.location,
        level=search_results.level,
        role_family=search_results.role_family,
        providers_searched=search_results.providers_searched,
        result_count=len(api_results),
        results=api_results,
        warnings=search_results.warnings,
        source_coverage=[
            SourceCoverageResponse(
                provider=coverage.provider,
                label=coverage.label,
                status=coverage.status,
                fetched_count=coverage.fetched_count,
                matched_count=coverage.matched_count,
                notes=coverage.notes,
            )
            for coverage in search_results.source_coverage
        ],
        search_suggestions=search_results.search_suggestions,
        external_search_links=[
            ExternalSearchLinkResponse(label=link.label, url=link.url, note=link.note)
            for link in search_results.external_search_links
        ],
    )


@app.post(
    "/analysis/custom",
    response_model=ResumeAnalysisResponse,
    dependencies=[Depends(enforce_public_rate_limit)],
)
def analyze_custom_job_descriptions(request: CustomAnalysisRequest) -> ResumeAnalysisResponse:
    return _build_resume_analysis_response(
        resume_text=request.resume_text,
        target_descriptions=request.job_descriptions,
        postings_analyzed=len(request.job_descriptions),
    )


@app.post(
    "/analysis/smart",
    response_model=SmartFitAnalysisResponse,
    dependencies=[Depends(enforce_public_rate_limit)],
)
def analyze_smart_fit_endpoint(request: SmartFitAnalysisRequest) -> SmartFitAnalysisResponse:
    try:
        return analyze_smart_fit(request)
    except AnalysisInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/analysis/smart/batch",
    response_model=SmartFitBatchAnalysisResponse,
    dependencies=[Depends(enforce_public_rate_limit)],
)
def analyze_smart_fit_batch_endpoint(request: SmartFitBatchAnalysisRequest) -> SmartFitBatchAnalysisResponse:
    results: list[SmartFitBatchResult] = []

    for index, job in enumerate(request.job_descriptions):
        try:
            analysis = analyze_smart_fit(
                SmartFitAnalysisRequest(
                    resume_text=request.resume_text,
                    job_description=job.job_description,
                    use_model_assisted=request.use_model_assisted,
                )
            )
        except AnalysisInputError as exc:
            raise HTTPException(status_code=400, detail=f"Job {index + 1}: {exc}") from exc

        results.append(
            SmartFitBatchResult(
                rank=index + 1,
                job_index=index,
                title=_infer_batch_job_title(job, index),
                analysis=analysis,
            )
        )

    ranked_results = _rank_smart_fit_batch_results(results)
    return SmartFitBatchAnalysisResponse(
        analyzed_count=len(ranked_results),
        results=ranked_results,
        best_job=ranked_results[0],
    )
