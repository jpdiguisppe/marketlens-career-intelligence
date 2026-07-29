from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.career_plans.candidate_selector import CandidateSelectionResult
from app.career_plans.schemas import (
    CAREER_PLAN_SCHEMA_VERSION,
    CareerPlanAction,
    CareerPlanActionStatus,
    CareerPlanActionType,
    CareerPlanEvidenceRef,
    CareerPlanOpportunityCategory,
    CareerPlanPortfolioEntry,
    CareerPlanProposal,
    CareerPlanRecurringFinding,
)
from app.career_plans.tools.smart_fit_tool import CareerPlanSmartFitToolOutput

DETERMINISTIC_PLANNER_VERSION = "career.deterministic_planner.v1"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized[:70] or "item"


def _category_for_result(result: dict[str, Any]) -> tuple[CareerPlanOpportunityCategory, list[str]]:
    fit = result["fit_summary"]
    hard_requirements = result.get("hard_requirements", [])
    hard_failure = any(item.get("status") == "does_not_meet" for item in hard_requirements)
    score = int(fit["score"])
    confidence = float(fit["confidence"])

    if hard_failure:
        return CareerPlanOpportunityCategory.SKIP, ["confirmed_hard_requirement_failure"]
    if score >= 70 and confidence >= 0.60:
        return CareerPlanOpportunityCategory.STRONG_MATCH, ["strong_grounded_fit"]
    if score >= 50:
        return CareerPlanOpportunityCategory.BALANCED, ["credible_grounded_fit"]
    if score >= 30:
        return CareerPlanOpportunityCategory.STRETCH, ["partial_grounded_fit"]
    return CareerPlanOpportunityCategory.SKIP, ["limited_grounded_fit"]


def _evidence_by_capability(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    for item in result.get("evidence_refs", []):
        capability = str(item.get("capability") or "").strip()
        if capability:
            evidence[capability.casefold()] = item
    return evidence


def _collect_recurring_findings(
    results: list[dict[str, Any]],
    field_name: str,
    kind: str,
) -> list[CareerPlanRecurringFinding]:
    occurrences: dict[str, dict[str, Any]] = {}
    for result in results:
        job_ref = result["job_ref"]
        evidence_by_capability = _evidence_by_capability(result)
        for capability in result.get(field_name, []):
            label = str(capability).strip()
            if not label:
                continue
            key = label.casefold()
            entry = occurrences.setdefault(
                key,
                {
                    "label": label,
                    "job_refs": [],
                    "evidence_refs": [],
                },
            )
            if job_ref not in entry["job_refs"]:
                entry["job_refs"].append(job_ref)
            evidence = evidence_by_capability.get(key)
            if evidence and evidence["id"] not in entry["evidence_refs"]:
                entry["evidence_refs"].append(evidence["id"])

    findings: list[CareerPlanRecurringFinding] = []
    for entry in occurrences.values():
        job_count = len(entry["job_refs"])
        if job_count < 2:
            continue
        priority = None
        if kind == "gap":
            priority = "high" if job_count >= 3 else "medium"
        findings.append(
            CareerPlanRecurringFinding(
                capability=entry["label"],
                job_count=job_count,
                job_refs=entry["job_refs"],
                evidence_refs=entry["evidence_refs"],
                priority=priority,
                summary=(
                    f"{entry['label']} is supported across {job_count} analyzed opportunities."
                    if kind == "strength"
                    else f"{entry['label']} is a repeated evidence gap across {job_count} analyzed opportunities."
                ),
            )
        )

    return sorted(
        findings,
        key=lambda item: (-item.job_count, item.capability.casefold()),
    )[:30]


def _portfolio_entry(result: dict[str, Any]) -> CareerPlanPortfolioEntry:
    category, reason_codes = _category_for_result(result)
    evidence_refs = [
        item["id"]
        for item in result.get("evidence_refs", [])
        if item.get("assessment_status") not in {"missing", None}
    ][:50]
    gap_refs = [
        item["id"]
        for item in result.get("evidence_refs", [])
        if item.get("assessment_status") == "missing"
    ][:50]
    hard_flags = [
        f"{item.get('category', 'requirement')}:{item.get('status', 'unclear')}"
        for item in result.get("hard_requirements", [])
        if item.get("status") != "meets"
    ][:30]
    return CareerPlanPortfolioEntry(
        job_ref=result["job_ref"],
        category=category,
        rank=result["rank"],
        fit_score=result["fit_summary"]["score"],
        fit_band=result["fit_summary"]["band"],
        confidence=result["fit_summary"]["confidence"],
        company=result["company"],
        title=result["title"],
        location=result.get("location"),
        reason_codes=reason_codes,
        evidence_refs=evidence_refs,
        gap_refs=gap_refs,
        hard_requirement_flags=hard_flags,
        safe_apply_url=result.get("apply_url"),
    )


def _build_actions(
    portfolio: list[CareerPlanPortfolioEntry],
    recurring_gaps: list[CareerPlanRecurringFinding],
) -> list[CareerPlanAction]:
    actions: list[CareerPlanAction] = []

    for entry in portfolio:
        if entry.hard_requirement_flags:
            actions.append(
                CareerPlanAction(
                    id=f"verify-{entry.job_ref}",
                    action_type=CareerPlanActionType.VERIFY_HARD_REQUIREMENT,
                    priority="high",
                    title=f"Verify hard requirements for {entry.title}",
                    rationale=(
                        "MarketLens found a hard requirement that is not clearly met. Verify it before treating this opportunity as actionable."
                    ),
                    job_refs=[entry.job_ref],
                    evidence_refs=entry.gap_refs,
                    status=CareerPlanActionStatus.PROPOSED,
                )
            )

        if entry.category in {
            CareerPlanOpportunityCategory.STRONG_MATCH,
            CareerPlanOpportunityCategory.BALANCED,
        }:
            actions.append(
                CareerPlanAction(
                    id=f"apply-{entry.job_ref}",
                    action_type=CareerPlanActionType.APPLY_NOW,
                    priority="high" if entry.category == CareerPlanOpportunityCategory.STRONG_MATCH else "medium",
                    title=f"Review and apply to {entry.title}",
                    rationale=(
                        f"This opportunity is categorized as {entry.category.value.replace('_', ' ')} from grounded Smart Fit evidence."
                    ),
                    job_refs=[entry.job_ref],
                    evidence_refs=entry.evidence_refs,
                    status=CareerPlanActionStatus.PROPOSED,
                )
            )
        elif entry.category == CareerPlanOpportunityCategory.STRETCH:
            actions.append(
                CareerPlanAction(
                    id=f"later-{entry.job_ref}",
                    action_type=CareerPlanActionType.SAVE_FOR_LATER,
                    priority="medium",
                    title=f"Keep {entry.title} as a stretch option",
                    rationale="The role has partial alignment but meaningful evidence gaps remain.",
                    job_refs=[entry.job_ref],
                    evidence_refs=entry.evidence_refs + entry.gap_refs,
                    status=CareerPlanActionStatus.PROPOSED,
                )
            )
        else:
            actions.append(
                CareerPlanAction(
                    id=f"skip-{entry.job_ref}",
                    action_type=CareerPlanActionType.SKIP_OPPORTUNITY,
                    priority="low",
                    title=f"Deprioritize {entry.title}",
                    rationale="Current evidence or hard-requirement findings do not support prioritizing this role.",
                    job_refs=[entry.job_ref],
                    evidence_refs=entry.gap_refs,
                    status=CareerPlanActionStatus.PROPOSED,
                )
            )

    for finding in recurring_gaps:
        actions.append(
            CareerPlanAction(
                id=f"proof-{_slug(finding.capability)}",
                action_type=CareerPlanActionType.BUILD_PROOF,
                priority=finding.priority or "medium",
                title=f"Build proof for {finding.capability}",
                rationale=finding.summary,
                job_refs=finding.job_refs,
                evidence_refs=finding.evidence_refs,
                status=CareerPlanActionStatus.PROPOSED,
            )
        )

    unique_actions: list[CareerPlanAction] = []
    seen_ids: set[str] = set()
    priority_order = {"high": 0, "medium": 1, "low": 2}
    for action in sorted(actions, key=lambda item: (priority_order.get(item.priority, 3), item.id)):
        if action.id in seen_ids:
            continue
        seen_ids.add(action.id)
        unique_actions.append(action)
        if len(unique_actions) >= 20:
            break
    return unique_actions


def build_deterministic_proposal(
    run_id: int,
    search_summary: dict[str, Any],
    selection: CandidateSelectionResult,
    smart_fit_output: CareerPlanSmartFitToolOutput,
) -> CareerPlanProposal:
    safe_results = [result.safe_summary for result in smart_fit_output.results]
    if not safe_results:
        return CareerPlanProposal(
            schema_version=CAREER_PLAN_SCHEMA_VERSION,
            run_id=run_id,
            generated_at=_utcnow(),
            proposal_engine=DETERMINISTIC_PLANNER_VERSION,
            proposal_status="no_results",
            source_summary={
                "providers_searched": search_summary.get("providers_searched", []),
                "source_coverage": search_summary.get("source_coverage", []),
                "candidate_count": search_summary.get("candidate_count", 0),
                "selected_count": len(selection.selected),
                "excluded": [item.safe_summary() for item in selection.excluded],
            },
            portfolio=[],
            recurring_strengths=[],
            recurring_gaps=[],
            evidence_refs=[],
            actions=[
                CareerPlanAction(
                    id="save-search-for-later",
                    action_type=CareerPlanActionType.SAVE_FOR_LATER,
                    priority="low",
                    title="Broaden or retry this search later",
                    rationale="The configured public sources did not return an analyzable opportunity for this bounded run.",
                    status=CareerPlanActionStatus.PROPOSED,
                )
            ],
            limitations=[
                "No selected job was available for Smart Fit analysis in this run.",
                "A no-results run does not mean that no matching jobs exist outside the configured public sources.",
            ],
            warnings=search_summary.get("warnings", [])[:30],
            fallback_status="deterministic_complete",
        )

    portfolio = [_portfolio_entry(result) for result in safe_results]
    recurring_strengths = _collect_recurring_findings(safe_results, "strong_matches", "strength")
    recurring_gaps = _collect_recurring_findings(safe_results, "important_gaps", "gap")

    evidence_by_id: dict[str, CareerPlanEvidenceRef] = {}
    for result in safe_results:
        for item in result.get("evidence_refs", []):
            evidence = CareerPlanEvidenceRef.model_validate(item)
            evidence_by_id.setdefault(evidence.id, evidence)

    limitations: list[str] = [
        "Portfolio categories describe application strategy, not hiring probability.",
        "The plan evaluates only evidence present in the supplied resume and selected job postings.",
        "Unanalyzed search results are excluded by bounded workflow limits, not declared poor fits.",
    ]
    for result in safe_results:
        for limitation in result.get("limitations", []):
            if limitation not in limitations:
                limitations.append(limitation)
            if len(limitations) >= 30:
                break

    return CareerPlanProposal(
        schema_version=CAREER_PLAN_SCHEMA_VERSION,
        run_id=run_id,
        generated_at=_utcnow(),
        proposal_engine=DETERMINISTIC_PLANNER_VERSION,
        proposal_status="complete",
        source_summary={
            "providers_searched": search_summary.get("providers_searched", []),
            "source_coverage": search_summary.get("source_coverage", []),
            "candidate_count": search_summary.get("candidate_count", 0),
            "selected_count": len(selection.selected),
            "analyzed_count": len(safe_results),
            "excluded": [item.safe_summary() for item in selection.excluded],
        },
        portfolio=portfolio,
        recurring_strengths=recurring_strengths,
        recurring_gaps=recurring_gaps,
        evidence_refs=list(evidence_by_id.values())[:250],
        actions=_build_actions(portfolio, recurring_gaps),
        limitations=limitations[:30],
        warnings=search_summary.get("warnings", [])[:30],
        fallback_status="deterministic_complete",
    )
