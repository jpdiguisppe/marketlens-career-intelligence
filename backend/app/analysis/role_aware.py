import re
from dataclasses import dataclass

from app.analysis.schemas import DocumentQuality, FitBand, FitSummary, SmartFitAnalysisResponse
from app.analysis.service import analyze_smart_fit as _base_analyze_smart_fit

_ROLE_TERMS: dict[str, tuple[str, ...]] = {
    "software": (
        "software engineer",
        "software developer",
        "backend engineer",
        "frontend engineer",
        "full stack",
        "application developer",
        "web developer",
        "developer tools",
        "platform engineer",
    ),
    "data": (
        "analytics engineer",
        "data analyst",
        "data engineer",
        "data scientist",
        "business intelligence",
        "bi analyst",
        "data pipeline",
        "analytics model",
        "dashboard",
    ),
    "cybersecurity": (
        "insider threat",
        "security engineer",
        "security analyst",
        "vulnerability response",
        "incident response",
        "threat analyst",
        "cybersecurity",
        "information security",
        "soc analyst",
    ),
    "operations_admin": (
        "data entry",
        "administrative assistant",
        "office assistant",
        "coordinator",
        "customer support",
    ),
    "sales_marketing": (
        "sales",
        "account executive",
        "marketing",
        "social media",
        "growth specialist",
    ),
}

_RESUME_DOMAIN_TERMS: dict[str, tuple[str, ...]] = {
    "software": (
        "computer science",
        "software",
        "programming",
        "java",
        "python",
        "c,",
        " c ",
        "react",
        "node",
        "api",
        "github",
    ),
    "data": (
        "sql",
        "database",
        "data structures",
        "data science",
        "analytics",
        "machine learning",
        "probability",
    ),
    "cybersecurity": (
        "cybersecurity",
        "security",
        "incident response",
        "vulnerability",
        "siem",
        "threat",
        "soc",
    ),
}

_BOILERPLATE_TERMS = (
    "mission",
    "values",
    "benefits",
    "equal opportunity",
    "economic freedom",
    "about us",
    "who we are",
)

_COMPATIBLE_ROLE_DOMAINS = {
    ("software", "data"),
    ("data", "software"),
}

_SCORE_SUMMARY_PATTERN = re.compile(r"^Resume-proof score: (?P<score>\d+)%\.\s*(?P<rest>.*)$")


@dataclass(frozen=True)
class RoleContext:
    job_domain: str | None
    resume_domains: set[str]
    alignment: str
    score_adjustment: int
    confidence_cap: float | None
    note: str


def _contains_phrase(text: str, phrase: str) -> bool:
    escaped_words = [re.escape(part) for part in re.split(r"[\s,./()\-]+", phrase.lower()) if part]
    if not escaped_words:
        return False
    pattern = r"(?<![a-z0-9])" + r"[\s,./()\-]+".join(escaped_words) + r"(?![a-z0-9])"
    return bool(re.search(pattern, text.lower()))


def _first_meaningful_line(text: str) -> str:
    ignored = {
        "responsibilities",
        "requirements",
        "required qualifications",
        "preferred qualifications",
        "qualifications",
        "about the role",
        "what you'll do",
        "what we're looking for",
    }
    for line in text.splitlines():
        cleaned = line.strip().rstrip(":")
        if cleaned and cleaned.lower() not in ignored:
            return cleaned[:180]
    return ""


def _classify_job_domain(job_text: str) -> str | None:
    first_line = _first_meaningful_line(job_text).lower()
    searchable = f"{first_line}\n{job_text[:2500]}".lower()

    # Title/first-line signals are the most reliable, especially for ATS feeds
    # with boilerplate-heavy descriptions.
    for domain in ("cybersecurity", "data", "software", "operations_admin", "sales_marketing"):
        if any(_contains_phrase(first_line, term) for term in _ROLE_TERMS[domain]):
            return domain

    domain_hits = {
        domain: sum(1 for term in terms if _contains_phrase(searchable, term))
        for domain, terms in _ROLE_TERMS.items()
    }
    best_domain, best_hits = max(domain_hits.items(), key=lambda item: item[1])
    return best_domain if best_hits > 0 else None


def _resume_domains(resume_text: str) -> set[str]:
    normalized = f" {resume_text.lower()} "
    domains = {
        domain
        for domain, terms in _RESUME_DOMAIN_TERMS.items()
        if any(term in normalized for term in terms)
    }
    return domains or {"general"}


def _fit_band(score: int) -> FitBand:
    if score >= 80:
        return FitBand.STRONG_ALIGNMENT
    if score >= 65:
        return FitBand.CREDIBLE_ALIGNMENT
    if score >= 45:
        return FitBand.PARTIAL_ALIGNMENT
    return FitBand.LIMITED_ALIGNMENT


def _alignment_context(resume_text: str, job_text: str) -> RoleContext:
    job_domain = _classify_job_domain(job_text)
    resume_domains = _resume_domains(resume_text)

    if job_domain is None:
        return RoleContext(
            job_domain=None,
            resume_domains=resume_domains,
            alignment="unknown",
            score_adjustment=0,
            confidence_cap=0.78,
            note="MarketLens could not confidently classify this role family, so the fit score relies mostly on extracted requirements.",
        )

    if job_domain in resume_domains:
        return RoleContext(
            job_domain=job_domain,
            resume_domains=resume_domains,
            alignment="strong",
            score_adjustment=0,
            confidence_cap=None,
            note=f"Role-aware check: this looks like a {job_domain.replace('_', '/')} role, and the resume has matching domain evidence.",
        )

    if any((job_domain, resume_domain) in _COMPATIBLE_ROLE_DOMAINS for resume_domain in resume_domains):
        return RoleContext(
            job_domain=job_domain,
            resume_domains=resume_domains,
            alignment="adjacent",
            score_adjustment=-4,
            confidence_cap=0.82,
            note=f"Role-aware check: this is primarily a {job_domain.replace('_', '/')} role. The resume has adjacent CS/software/data evidence, but not a perfect role-family match.",
        )

    if job_domain == "cybersecurity":
        return RoleContext(
            job_domain=job_domain,
            resume_domains=resume_domains,
            alignment="weak",
            score_adjustment=-18,
            confidence_cap=0.68,
            note="Role-aware check: this appears to be primarily cybersecurity/threat-focused, but the resume does not yet show direct cybersecurity evidence. Skill overlap alone should not make it rank as the best fit.",
        )

    if job_domain in {"operations_admin", "sales_marketing"}:
        return RoleContext(
            job_domain=job_domain,
            resume_domains=resume_domains,
            alignment="weak",
            score_adjustment=-20,
            confidence_cap=0.65,
            note=f"Role-aware check: this looks more like a {job_domain.replace('_', '/')} role than a technical CS/software/data role, so technical keyword overlap is discounted.",
        )

    return RoleContext(
        job_domain=job_domain,
        resume_domains=resume_domains,
        alignment="weak",
        score_adjustment=-10,
        confidence_cap=0.72,
        note=f"Role-aware check: this role appears to be {job_domain.replace('_', '/')}, while the resume evidence points elsewhere.",
    )


def _job_quality_note(job_text: str, requirement_count: int) -> tuple[int, float | None, str | None]:
    normalized = job_text.lower()
    boilerplate_hits = sum(1 for term in _BOILERPLATE_TERMS if term in normalized)
    if requirement_count <= 2 and boilerplate_hits >= 2:
        return (
            -6,
            0.66,
            "Job-description quality note: this posting appears boilerplate-heavy with few concrete requirements, so MarketLens lowers confidence and avoids over-trusting a small number of keyword matches.",
        )
    if requirement_count <= 2:
        return (
            -3,
            0.74,
            "Job-description quality note: this posting exposes very few concrete requirements, so the ranking is lower-confidence.",
        )
    return 0, None, None


def _with_adjusted_summary(summary: FitSummary, score_adjustment: int, confidence_cap: float | None, note: str | None) -> FitSummary:
    adjusted_score = min(100, max(0, summary.score + score_adjustment))
    confidence = summary.confidence if confidence_cap is None else min(summary.confidence, confidence_cap)
    headline = summary.headline
    if score_adjustment < 0:
        headline += " Role-aware scoring discounted this result because the role context is not a clean match."
    if note and "boilerplate" in note.lower():
        headline += " The job description is also low-signal."

    return summary.model_copy(
        update={
            "score": adjusted_score,
            "band": _fit_band(adjusted_score),
            "confidence": round(confidence, 2),
            "headline": headline,
        }
    )


def _with_quality_warning(document_quality: DocumentQuality, note: str | None) -> DocumentQuality:
    if not note:
        return document_quality
    warnings = list(document_quality.warnings)
    if note not in warnings:
        warnings.append(note)
    return document_quality.model_copy(update={"warnings": warnings})


def _with_adjusted_report_score(
    items: list[str],
    original_score: int,
    adjusted_score: int,
) -> list[str]:
    if original_score == adjusted_score:
        return items

    updated_items: list[str] = []
    for item in items:
        match = _SCORE_SUMMARY_PATTERN.match(item)
        if not match:
            updated_items.append(item)
            continue

        rest = match.group("rest").strip()
        adjusted_item = (
            f"Role-adjusted resume-proof score: {adjusted_score}% "
            f"(base skill-evidence score before role/context adjustments was {original_score}%)."
        )
        if rest:
            adjusted_item += f" {rest}"
        updated_items.append(adjusted_item)

    return updated_items


def analyze_smart_fit(
    resume_text: str,
    job_description: str,
    use_model_assisted: bool = False,
) -> SmartFitAnalysisResponse:
    analysis = _base_analyze_smart_fit(
        resume_text=resume_text,
        job_description=job_description,
        use_model_assisted=use_model_assisted,
    )

    role_context = _alignment_context(resume_text, job_description)
    quality_adjustment, quality_confidence_cap, quality_note = _job_quality_note(
        job_description,
        len(analysis.requirement_assessments),
    )
    confidence_caps = [cap for cap in (role_context.confidence_cap, quality_confidence_cap) if cap is not None]
    confidence_cap = min(confidence_caps) if confidence_caps else None
    adjusted_summary = _with_adjusted_summary(
        analysis.fit_summary,
        role_context.score_adjustment + quality_adjustment,
        confidence_cap,
        quality_note,
    )

    report_summary = [role_context.note]
    if quality_note:
        report_summary.append(quality_note)
    report_summary.extend(
        _with_adjusted_report_score(
            analysis.report_summary,
            analysis.fit_summary.score,
            adjusted_summary.score,
        )
    )

    limitations = list(analysis.limitations)
    limitations.append(
        "Role-aware scoring is deterministic and conservative; it discounts jobs whose detected role family does not match the resume evidence even when a few keywords overlap."
    )

    return analysis.model_copy(
        update={
            "fit_summary": adjusted_summary,
            "document_quality": _with_quality_warning(analysis.document_quality, quality_note),
            "report_summary": report_summary[:7],
            "limitations": limitations,
        }
    )