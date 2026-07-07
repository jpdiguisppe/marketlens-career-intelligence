import json

from sqlalchemy import Integer, String, Text
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
