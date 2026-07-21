from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.analysis.schemas import CategoryCoverage, CoachingActionType, FitSummary, GapGroup
from app.auth import AuthenticatedUser, get_current_user
from app.database import get_db
from app.models import SavedReportDB

router = APIRouter(prefix="/saved-reports", tags=["saved-reports"])


class SavedCoachingAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: CoachingActionType
    priority: str = Field(..., min_length=1, max_length=20)
    title: str = Field(..., min_length=1, max_length=255)
    skill: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=255)
    advice: str = Field(..., min_length=1, max_length=5_000)


class SavedReportSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fit_summary: FitSummary
    report_summary: list[str] = Field(default_factory=list, max_length=20)
    category_coverage: list[CategoryCoverage] = Field(default_factory=list, max_length=30)
    coaching_actions: list[SavedCoachingAction] = Field(default_factory=list, max_length=30)
    gap_groups: list[GapGroup] = Field(default_factory=list, max_length=30)
    strong_matches: list[str] = Field(default_factory=list, max_length=100)
    related_matches: list[str] = Field(default_factory=list, max_length=100)
    important_gaps: list[str] = Field(default_factory=list, max_length=100)
    recommendations: list[str] = Field(default_factory=list, max_length=100)
    limitations: list[str] = Field(default_factory=list, max_length=100)
    analysis_engine: Literal["deterministic", "model_assisted"]
    model_assisted_status: str = Field(..., min_length=1, max_length=255)


class SavedReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(default="manual", min_length=1, max_length=100)
    source_job_id: str | None = Field(default=None, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    title: str = Field(..., min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    apply_url: str | None = Field(default=None, max_length=2048)
    summary: SavedReportSummary


class SavedReport(SavedReportCreate):
    id: int
    created_at: datetime


def _to_saved_report_response(saved_report: SavedReportDB) -> SavedReport:
    return SavedReport(
        id=saved_report.id,
        source=saved_report.source,
        source_job_id=saved_report.source_job_id,
        company=saved_report.company,
        title=saved_report.title,
        location=saved_report.location,
        apply_url=saved_report.apply_url,
        summary=SavedReportSummary.model_validate(saved_report.summary),
        created_at=saved_report.created_at,
    )


def _get_owned_saved_report(db: Session, saved_report_id: int, user_id: str) -> SavedReportDB:
    saved_report = (
        db.query(SavedReportDB)
        .filter(SavedReportDB.id == saved_report_id, SavedReportDB.user_id == user_id)
        .one_or_none()
    )
    if saved_report is None:
        raise HTTPException(status_code=404, detail="Saved report not found.")
    return saved_report


@router.post("", response_model=SavedReport, status_code=status.HTTP_201_CREATED)
def create_saved_report(
    report: SavedReportCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedReport:
    saved_report = SavedReportDB(
        user_id=current_user.user_id,
        source=report.source,
        source_job_id=report.source_job_id,
        company=report.company,
        title=report.title,
        location=report.location,
        apply_url=report.apply_url,
        summary_json="{}",
    )
    saved_report.summary = report.summary.model_dump(mode="json")
    db.add(saved_report)
    db.commit()
    db.refresh(saved_report)
    return _to_saved_report_response(saved_report)


@router.get("", response_model=list[SavedReport])
def list_saved_reports(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SavedReport]:
    saved_reports = (
        db.query(SavedReportDB)
        .filter(SavedReportDB.user_id == current_user.user_id)
        .order_by(SavedReportDB.created_at.desc(), SavedReportDB.id.desc())
        .all()
    )
    return [_to_saved_report_response(report) for report in saved_reports]


@router.get("/{saved_report_id}", response_model=SavedReport)
def get_saved_report(
    saved_report_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedReport:
    return _to_saved_report_response(_get_owned_saved_report(db, saved_report_id, current_user.user_id))


@router.delete("/{saved_report_id}")
def delete_saved_report(
    saved_report_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    saved_report = _get_owned_saved_report(db, saved_report_id, current_user.user_id)
    db.delete(saved_report)
    db.commit()
    return {"status": "deleted"}
