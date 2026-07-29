from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.career_plans.schemas import CareerPlanGoal
from app.job_search import ExternalJobResult, JobSearchResults, search_external_jobs
from app.skill_extractor import extract_skills

SEARCH_TOOL_NAME = "career.search_jobs.v1"
SEARCH_RESULT_LIMIT = 15


@dataclass(frozen=True)
class CareerPlanSearchCandidate:
    job_ref: str
    search_rank: int
    job: ExternalJobResult

    def safe_metadata(self) -> dict[str, Any]:
        return {
            "job_ref": self.job_ref,
            "search_rank": self.search_rank,
            "source": self.job.source,
            "source_job_id": self.job.id,
            "company": self.job.company,
            "title": self.job.title,
            "location": self.job.location,
            "apply_url": self.job.apply_url,
            "updated_at": self.job.updated_at,
            "extracted_skills": extract_skills(self.job.description)[:50],
        }


@dataclass(frozen=True)
class CareerPlanSearchToolOutput:
    raw: JobSearchResults
    candidates: list[CareerPlanSearchCandidate]
    safe_summary: dict[str, Any]
    safe_status_code: str


def _search_query(goal: CareerPlanGoal) -> str:
    occupation = goal.target_occupation.strip()
    industry = (goal.industry or "").strip()
    if industry and industry.lower() not in occupation.lower():
        return f"{industry} {occupation}".strip()
    return occupation


def _search_location(goal: CareerPlanGoal) -> str | None:
    if goal.location and goal.location.strip():
        return goal.location.strip()
    if goal.work_mode.value == "remote":
        return "Remote"
    return None


def run_job_search_tool(goal: CareerPlanGoal) -> CareerPlanSearchToolOutput:
    results = search_external_jobs(
        query=_search_query(goal),
        location=_search_location(goal),
        level=goal.experience_level.value,
        limit=SEARCH_RESULT_LIMIT,
    )
    candidates = [
        CareerPlanSearchCandidate(job_ref=f"job-{index}", search_rank=index, job=job)
        for index, job in enumerate(results.results, start=1)
    ]

    provider_statuses = [coverage.status for coverage in results.source_coverage]
    if candidates:
        safe_status_code = (
            "partial_provider_failure"
            if any(status == "failed" for status in provider_statuses)
            else "ok"
        )
    else:
        safe_status_code = (
            "provider_failure"
            if provider_statuses and all(status == "failed" for status in provider_statuses)
            else "no_results"
        )

    safe_summary: dict[str, Any] = {
        "tool_name": SEARCH_TOOL_NAME,
        "query": results.query,
        "location": results.location,
        "level": results.level,
        "role_family": results.role_family,
        "industry": results.industry,
        "providers_searched": results.providers_searched,
        "source_coverage": [
            {
                "provider": coverage.provider,
                "label": coverage.label,
                "status": coverage.status,
                "fetched_count": coverage.fetched_count,
                "matched_count": coverage.matched_count,
                "notes": coverage.notes[:10],
            }
            for coverage in results.source_coverage
        ],
        "candidate_count": len(candidates),
        "candidates": [candidate.safe_metadata() for candidate in candidates],
        "warnings": results.warnings[:20],
        "search_suggestions": results.search_suggestions[:20],
        "safe_status_code": safe_status_code,
    }
    return CareerPlanSearchToolOutput(
        raw=results,
        candidates=candidates,
        safe_summary=safe_summary,
        safe_status_code=safe_status_code,
    )
