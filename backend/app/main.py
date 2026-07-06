from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.skill_extractor import count_skills, extract_skills

app = FastAPI(
    title="MarketLens API",
    description="Backend API for analyzing job postings and career skill signals.",
    version="0.2.0",
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
    extracted_skills: list[str] = []


class SkillExtractionRequest(BaseModel):
    text: str = Field(..., examples=["Experience with Python, SQL, Docker, AWS, and REST APIs preferred."])


class SkillExtractionResponse(BaseModel):
    skills: list[str]


job_postings: List[JobPosting] = []
next_job_posting_id = 1


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
    global next_job_posting_id

    created_posting = JobPosting(
        id=next_job_posting_id,
        extracted_skills=extract_skills(posting.description),
        **posting.model_dump(),
    )
    job_postings.append(created_posting)
    next_job_posting_id += 1

    return created_posting


@app.get("/job-postings", response_model=list[JobPosting])
def list_job_postings() -> list[JobPosting]:
    return job_postings


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
