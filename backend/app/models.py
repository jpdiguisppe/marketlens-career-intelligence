import json
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class JobPostingDB(Base):
    __tablename__ = "job_postings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role_category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    experience_level: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_skills_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    @property
    def extracted_skills(self) -> list[str]:
        return json.loads(self.extracted_skills_json)

    @extracted_skills.setter
    def extracted_skills(self, skills: list[str]) -> None:
        self.extracted_skills_json = json.dumps(skills)


class SavedJobDB(Base):
    __tablename__ = "saved_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="manual")
    source_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    apply_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    extracted_skills_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    @property
    def extracted_skills(self) -> list[str]:
        return json.loads(self.extracted_skills_json)

    @extracted_skills.setter
    def extracted_skills(self, skills: list[str]) -> None:
        self.extracted_skills_json = json.dumps(skills)
