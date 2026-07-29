from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.career_plans.tools.job_search_tool import CareerPlanSearchCandidate


@dataclass(frozen=True)
class CandidateExclusion:
    job_ref: str
    search_rank: int
    company: str
    title: str
    reason_code: str

    def safe_summary(self) -> dict[str, Any]:
        return {
            "job_ref": self.job_ref,
            "search_rank": self.search_rank,
            "company": self.company,
            "title": self.title,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True)
class CandidateSelectionResult:
    selected: list[CareerPlanSearchCandidate]
    excluded: list[CandidateExclusion]

    def safe_summary(self) -> dict[str, Any]:
        return {
            "selected_count": len(self.selected),
            "excluded_count": len(self.excluded),
            "selected": [candidate.safe_metadata() for candidate in self.selected],
            "excluded": [item.safe_summary() for item in self.excluded],
        }


def select_candidates(
    candidates: list[CareerPlanSearchCandidate],
    max_jobs: int,
) -> CandidateSelectionResult:
    if max_jobs < 1 or max_jobs > 5:
        raise ValueError("Career Plan candidate selection requires a bound from 1 to 5.")

    deduplicated: list[CareerPlanSearchCandidate] = []
    excluded: list[CandidateExclusion] = []
    seen_postings: set[tuple[str, str]] = set()

    for candidate in candidates:
        posting_key = (candidate.job.source.lower(), candidate.job.id)
        if posting_key in seen_postings:
            excluded.append(
                CandidateExclusion(
                    job_ref=candidate.job_ref,
                    search_rank=candidate.search_rank,
                    company=candidate.job.company,
                    title=candidate.job.title,
                    reason_code="duplicate_posting",
                )
            )
            continue
        seen_postings.add(posting_key)
        deduplicated.append(candidate)

    selected: list[CareerPlanSearchCandidate] = []
    selected_refs: set[str] = set()
    selected_companies: set[str] = set()

    # First pass preserves search order while adding company diversity.
    for candidate in deduplicated:
        company_key = candidate.job.company.strip().lower()
        if company_key in selected_companies:
            continue
        selected.append(candidate)
        selected_refs.add(candidate.job_ref)
        selected_companies.add(company_key)
        if len(selected) >= max_jobs:
            break

    # Fill remaining slots in original search order when fewer distinct companies exist.
    if len(selected) < max_jobs:
        for candidate in deduplicated:
            if candidate.job_ref in selected_refs:
                continue
            selected.append(candidate)
            selected_refs.add(candidate.job_ref)
            if len(selected) >= max_jobs:
                break

    for candidate in deduplicated:
        if candidate.job_ref in selected_refs:
            continue
        excluded.append(
            CandidateExclusion(
                job_ref=candidate.job_ref,
                search_rank=candidate.search_rank,
                company=candidate.job.company,
                title=candidate.job.title,
                reason_code="outside_analysis_limit",
            )
        )

    excluded.sort(key=lambda item: (item.search_rank, item.job_ref))
    return CandidateSelectionResult(selected=selected, excluded=excluded)
