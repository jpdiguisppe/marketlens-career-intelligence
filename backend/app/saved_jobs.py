from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.auth import AuthenticatedUser, get_current_user
from app.database import get_db
from app.models import SavedJobDB
from app.skill_extractor import extract_skills

MAX_SAVED_JOB_DESCRIPTION_LENGTH = 50_000

router = APIRouter(prefix="/saved-jobs", tags=["saved-jobs"])


class SavedJobCreate(BaseModel):
    source: str = Field(default="manual", min_length=1, max_length=100)
    source_job_id: str | None = Field(default=None, max_length=255)
    company: str = Field(..., min_length=1, max_length=255)
    title: str = Field(..., min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    description: str = Field(
        ...,
        min_length=1,
        max_length=MAX_SAVED_JOB_DESCRIPTION_LENGTH,
    )
    apply_url: str | None = Field(default=None, max_length=2048)


class SavedJob(SavedJobCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    extracted_skills: list[str] = Field(default_factory=list)
    created_at: datetime


def _to_saved_job_response(saved_job: SavedJobDB) -> SavedJob:
    return SavedJob.model_validate(saved_job)


def _get_owned_saved_job(
    db: Session,
    saved_job_id: int,
    user_id: str,
) -> SavedJobDB:
    saved_job = (
        db.query(SavedJobDB)
        .filter(
            SavedJobDB.id == saved_job_id,
            SavedJobDB.user_id == user_id,
        )
        .one_or_none()
    )

    if saved_job is None:
        raise HTTPException(status_code=404, detail="Saved job not found.")

    return saved_job


@router.post(
    "",
    response_model=SavedJob,
    status_code=status.HTTP_201_CREATED,
)
def create_saved_job(
    job: SavedJobCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedJob:
    if job.source_job_id:
        existing_saved_job = (
            db.query(SavedJobDB)
            .filter(
                SavedJobDB.user_id == current_user.user_id,
                SavedJobDB.source == job.source,
                SavedJobDB.source_job_id == job.source_job_id,
            )
            .one_or_none()
        )

        if existing_saved_job is not None:
            return _to_saved_job_response(existing_saved_job)

    saved_job = SavedJobDB(
        user_id=current_user.user_id,
        **job.model_dump(),
    )
    saved_job.extracted_skills = extract_skills(job.description)

    db.add(saved_job)
    db.commit()
    db.refresh(saved_job)

    return _to_saved_job_response(saved_job)


@router.get("", response_model=list[SavedJob])
def list_saved_jobs(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SavedJob]:
    saved_jobs = (
        db.query(SavedJobDB)
        .filter(SavedJobDB.user_id == current_user.user_id)
        .order_by(SavedJobDB.created_at.desc(), SavedJobDB.id.desc())
        .all()
    )

    return [_to_saved_job_response(saved_job) for saved_job in saved_jobs]


@router.get("/{saved_job_id}", response_model=SavedJob)
def get_saved_job(
    saved_job_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedJob:
    saved_job = _get_owned_saved_job(
        db,
        saved_job_id,
        current_user.user_id,
    )
    return _to_saved_job_response(saved_job)


@router.delete("/{saved_job_id}")
def delete_saved_job(
    saved_job_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    saved_job = _get_owned_saved_job(
        db,
        saved_job_id,
        current_user.user_id,
    )

    db.delete(saved_job)
    db.commit()

    return {"status": "deleted"}
