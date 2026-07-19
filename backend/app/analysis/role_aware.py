import re
from dataclasses import dataclass

from app.analysis.schemas import (
    CategoryCoverage,
    CoachingAction,
    CoachingActionType,
    DocumentQuality,
    FitBand,
    FitSummary,
    GapGroup,
    SmartFitAnalysisResponse,
)
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
    "finance": (
        "financial analyst",
        "finance analyst",
        "accounting",
        "accountant",
        "audit",
        "auditor",
        "tax",
        "treasury",
        "fp&a",
        "fpa",
        "credit analyst",
        "risk analyst",
        "portfolio analyst",
        "investment analyst",
    ),
    "product": (
        "product manager",
        "product analyst",
        "product owner",
        "roadmap",
        "user research",
        "product strategy",
    ),
    "healthcare": (
        "healthcare",
        "clinical",
        "patient",
        "medical",
        "ehr",
        "electronic health record",
        "epic",
        "cerner",
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
    "finance": (
        "finance",
        "accounting",
        "audit",
        "tax",
        "financial modeling",
        "valuation",
        "excel",
    ),
    "product": (
        "product",
        "roadmap",
        "user research",
        "requirements gathering",
    ),
    "healthcare": (
        "healthcare",
        "clinical",
        "patient",
        "medical",
        "ehr",
        "epic",
        "cerner",
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
    ("finance", "data"),
    ("product", "software"),
    ("product", "data"),
    ("healthcare", "software"),
    ("healthcare", "data"),
}

_SCORE_SUMMARY_PATTERN = re.compile(r"^Resume-proof score: (?P<score>\d+)%\.\s*(?P<rest>.*)$")
_NOISY_FORMAT_WARNING_PREFIXES = (
    "No standard resume section headings were detected.",
    "No standard job-posting headings were detected.",
)
_SOFT_FORMAT_WARNING = "Some resume/job-posting formatting was unclear, so requirement priorities may be approximate."
_CATEGORY_LABELS = {
    "ai_ml": "AI / ML",
    "programming_language": "Programming Language",
    "software_architecture": "Software Architecture",
    "software_design": "Software Design",
    "software_engineering": "Software Engineering",
    "sales_marketing": "Sales / Marketing",
    "operations_admin": "Operations / Admin",
}


@dataclass(frozen=True)
class RoleContext:
    job_domain: str | None
    resume_domains: set[str]
    alignment: str
    score_adjustment: int
    confidence_cap: float | None
    note: str


@dataclass(frozen=True)
class CapabilityGroupDefinition:
    domains: tuple[str, ...]
    title: str
    category: str
    skills: tuple[str, ...]
    job_terms: tuple[str, ...]
    resume_terms: tuple[str, ...]
    summary: str


_CAPABILITY_GROUPS: tuple[CapabilityGroupDefinition, ...] = (
    CapabilityGroupDefinition(
        domains=("software",),
        title="Backend/API implementation",
        category="backend",
        skills=("REST APIs", "backend services"),
        job_terms=("backend", "api", "apis", "endpoint", "service", "microservice", "server-side"),
        resume_terms=("backend", "api", "apis", "endpoint", "fastapi", "node", "flask", "server-side"),
        summary="The posting points to backend or API implementation work, but the resume does not clearly prove applied backend/API delivery for this role context.",
    ),
    CapabilityGroupDefinition(
        domains=("software",),
        title="Frontend/web application delivery",
        category="frontend",
        skills=("frontend", "web applications"),
        job_terms=("frontend", "front-end", "react", "angular", "web application", "ui", "responsive"),
        resume_terms=("frontend", "front-end", "react", "angular", "web app", "ui", "html", "css"),
        summary="The posting asks for frontend or web-application delivery, but the resume does not show direct project proof in that area yet.",
    ),
    CapabilityGroupDefinition(
        domains=("software", "data"),
        title="Testing and quality validation",
        category="quality",
        skills=("Testing", "quality validation"),
        job_terms=("testing", "test", "qa", "validation", "validated", "data quality", "quality checks"),
        resume_terms=("testing", "unit test", "test suite", "qa", "validation", "verified", "quality checks"),
        summary="The posting emphasizes testing or validation, but the resume does not clearly show applied testing/quality evidence for this role.",
    ),
    CapabilityGroupDefinition(
        domains=("software",),
        title="Cloud/DevOps deployment",
        category="devops",
        skills=("cloud", "deployment", "CI/CD"),
        job_terms=("aws", "azure", "cloud", "docker", "kubernetes", "ci/cd", "deployment", "infrastructure"),
        resume_terms=("aws", "azure", "cloud", "docker", "kubernetes", "ci/cd", "deployment", "github actions"),
        summary="The posting signals cloud, infrastructure, or deployment ownership, but the resume does not yet show direct proof for that capability.",
    ),
    CapabilityGroupDefinition(
        domains=("data",),
        title="Data pipelines and analytics engineering",
        category="data",
        skills=("Data Pipelines", "analytics engineering"),
        job_terms=("data pipeline", "data pipelines", "etl", "elt", "dbt", "airflow", "data warehouse", "warehouse", "data model", "analytics engineering"),
        resume_terms=("data pipeline", "data pipelines", "etl", "elt", "dbt", "airflow", "warehouse", "data model"),
        summary="The posting asks for data-pipeline or analytics-engineering work, but the resume does not show direct project or work proof for that capability.",
    ),
    CapabilityGroupDefinition(
        domains=("data",),
        title="Metrics, dashboards, and business analytics",
        category="data",
        skills=("dashboards", "metrics", "business analytics"),
        job_terms=("dashboard", "dashboards", "metrics", "kpi", "reporting", "business intelligence", "insights", "analytics"),
        resume_terms=("dashboard", "dashboards", "metrics", "kpi", "reporting", "business intelligence", "analytics"),
        summary="The posting includes metrics, reporting, or dashboard work, but the resume does not clearly prove applied analytics delivery in that context.",
    ),
    CapabilityGroupDefinition(
        domains=("data",),
        title="Statistical or machine-learning analysis",
        category="ai_ml",
        skills=("Machine Learning", "statistical analysis"),
        job_terms=("machine learning", "ml", "statistical", "statistics", "experiment", "predictive", "modeling", "forecast"),
        resume_terms=("machine learning", "ml", "statistics", "probability", "model", "classifier", "scikit-learn"),
        summary="The posting points to statistical or machine-learning analysis; strengthen direct evidence only if that work is accurate for the resume.",
    ),
    CapabilityGroupDefinition(
        domains=("cybersecurity",),
        title="Security operations and incident response",
        category="cybersecurity",
        skills=("security operations", "incident response", "SIEM"),
        job_terms=("security operations", "security incident", "security incidents", "incident response", "soc", "siem", "alert triage", "alerts"),
        resume_terms=("security operations", "security incident", "incident response", "soc", "siem", "alert triage"),
        summary="The posting asks for security-operations or incident-response work, but the resume does not yet show direct cybersecurity operations evidence.",
    ),
    CapabilityGroupDefinition(
        domains=("cybersecurity",),
        title="Threat investigation and fraud analysis",
        category="cybersecurity",
        skills=("insider threat", "threat investigation", "fraud detection"),
        job_terms=("insider threat", "threat investigation", "threat analyst", "investigation", "investigations", "fraud detection", "account misuse", "abuse investigation"),
        resume_terms=("insider threat", "threat investigation", "fraud detection", "investigation", "account misuse"),
        summary="The posting is investigation-heavy, but the resume does not show direct insider-threat, fraud, or abuse-investigation evidence.",
    ),
    CapabilityGroupDefinition(
        domains=("cybersecurity",),
        title="Detection tooling and log analysis",
        category="cybersecurity",
        skills=("log analysis", "endpoint detection", "DLP", "UBA"),
        job_terms=("log analysis", "logs", "endpoint detection", "edr", "dlp", "uba", "behavioral signals", "detection tooling"),
        resume_terms=("log analysis", "logs", "endpoint detection", "edr", "dlp", "uba", "behavioral signals"),
        summary="The posting mentions detection tools, logs, or behavioral signals, but the resume does not show direct tool-based security analysis evidence.",
    ),
    CapabilityGroupDefinition(
        domains=("cybersecurity",),
        title="Vulnerability response and remediation",
        category="cybersecurity",
        skills=("vulnerability response", "remediation"),
        job_terms=("vulnerability", "vulnerability response", "remediation", "patching", "cve", "risk remediation"),
        resume_terms=("vulnerability", "vulnerability response", "remediation", "patching", "cve"),
        summary="The posting asks for vulnerability response or remediation evidence, but the resume does not show direct proof in that area.",
    ),
    CapabilityGroupDefinition(
        domains=("finance",),
        title="Financial modeling and analysis",
        category="finance",
        skills=("financial modeling", "variance analysis", "forecasting"),
        job_terms=("financial model", "financial modeling", "forecast", "forecasting", "budget", "budgeting", "variance analysis", "valuation"),
        resume_terms=("financial model", "financial modeling", "forecast", "forecasting", "budget", "variance analysis", "valuation"),
        summary="The posting asks for finance-analysis or modeling work, but the resume does not show direct finance-domain proof yet.",
    ),
    CapabilityGroupDefinition(
        domains=("finance",),
        title="Accounting, audit, and tax workflows",
        category="finance",
        skills=("accounting", "audit", "tax"),
        job_terms=("accounting", "audit", "auditor", "tax", "close process", "reconciliation", "reconciliations", "journal entry"),
        resume_terms=("accounting", "audit", "tax", "reconciliation", "journal entry"),
        summary="The posting includes accounting, audit, or tax workflow expectations, but the resume does not document direct evidence for those workflows.",
    ),
    CapabilityGroupDefinition(
        domains=("finance",),
        title="Risk, controls, and compliance reporting",
        category="finance",
        skills=("risk reporting", "controls", "compliance"),
        job_terms=("risk", "controls", "compliance", "regulatory", "sox", "audit support", "reporting"),
        resume_terms=("risk", "controls", "compliance", "regulatory", "sox"),
        summary="The posting points to risk, controls, or compliance reporting, but the resume does not show direct finance/compliance proof.",
    ),
    CapabilityGroupDefinition(
        domains=("product",),
        title="Product strategy and roadmap ownership",
        category="product",
        skills=("roadmap", "product strategy"),
        job_terms=("roadmap", "product strategy", "product requirements", "prioritization", "backlog", "product owner"),
        resume_terms=("roadmap", "product strategy", "product requirements", "prioritization", "backlog", "product owner"),
        summary="The posting asks for product-strategy or roadmap work, but the resume does not show direct product ownership evidence.",
    ),
    CapabilityGroupDefinition(
        domains=("product",),
        title="User research and requirements discovery",
        category="product",
        skills=("user research", "requirements discovery"),
        job_terms=("user research", "customer research", "requirements gathering", "discovery", "user interviews", "stakeholder interviews"),
        resume_terms=("user research", "customer research", "requirements gathering", "discovery", "user interviews"),
        summary="The posting includes research or requirements-discovery work, but the resume does not document direct evidence for that capability.",
    ),
    CapabilityGroupDefinition(
        domains=("operations_admin",),
        title="Administrative coordination and scheduling",
        category="operations",
        skills=("administrative coordination", "scheduling"),
        job_terms=("administrative", "scheduling", "calendar", "coordination", "office operations", "organizing"),
        resume_terms=("administrative", "scheduling", "calendar", "coordination", "office operations"),
        summary="The posting is coordination-heavy, but the resume does not clearly prove administrative coordination or scheduling work.",
    ),
    CapabilityGroupDefinition(
        domains=("operations_admin",),
        title="Records, data entry, and process accuracy",
        category="operations",
        skills=("data entry", "records management", "process accuracy"),
        job_terms=("data entry", "records", "database", "accuracy", "process", "documentation"),
        resume_terms=("data entry", "records", "database", "accuracy", "documentation"),
        summary="The posting emphasizes records, data-entry, or process accuracy, but the resume does not show direct proof for that operations capability.",
    ),
    CapabilityGroupDefinition(
        domains=("sales_marketing",),
        title="Customer, sales, or revenue ownership",
        category="sales_marketing",
        skills=("customer ownership", "sales", "pipeline"),
        job_terms=("sales", "pipeline", "quota", "customer", "client", "account", "revenue"),
        resume_terms=("sales", "pipeline", "quota", "customer", "client", "account", "revenue"),
        summary="The posting is customer or revenue oriented, but the resume does not show direct sales/customer ownership evidence.",
    ),
    CapabilityGroupDefinition(
        domains=("sales_marketing",),
        title="Marketing channels and campaign execution",
        category="sales_marketing",
        skills=("campaigns", "content", "marketing channels"),
        job_terms=("marketing", "campaign", "content", "social media", "seo", "brand", "channel"),
        resume_terms=("marketing", "campaign", "content", "social media", "seo", "brand", "channel"),
        summary="The posting asks for marketing-channel or campaign execution, but the resume does not document direct marketing evidence.",
    ),
    CapabilityGroupDefinition(
        domains=("healthcare",),
        title="Healthcare systems and clinical workflow context",
        category="healthcare",
        skills=("clinical workflows", "EHR", "patient data"),
        job_terms=("clinical", "patient", "ehr", "electronic health record", "epic", "cerner", "healthcare workflow"),
        resume_terms=("clinical", "patient", "ehr", "electronic health record", "epic", "cerner", "healthcare workflow"),
        summary="The posting depends on healthcare-system or clinical-workflow context, but the resume does not show direct healthcare-domain evidence.",
    ),
    CapabilityGroupDefinition(
        domains=("healthcare",),
        title="Healthcare privacy, compliance, and data handling",
        category="healthcare",
        skills=("healthcare compliance", "HIPAA", "patient data"),
        job_terms=("hipaa", "privacy", "patient data", "compliance", "protected health information", "phi"),
        resume_terms=("hipaa", "privacy", "patient data", "compliance", "protected health information", "phi"),
        summary="The posting includes healthcare privacy or compliance expectations, but the resume does not show direct evidence for that context.",
    ),
)


def _contains_phrase(text: str, phrase: str) -> bool:
    escaped_words = [re.escape(part) for part in re.split(r"[\s,./()\-]+", phrase.lower()) if part]
    if not escaped_words:
        return False
    pattern = r"(?<![a-z0-9])" + r"[\s,./()\-]+".join(escaped_words) + r"(?![a-z0-9])"
    return bool(re.search(pattern, text.lower()))


def _matches_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(_contains_phrase(text, phrase) for phrase in phrases)


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
    for domain in ("cybersecurity", "data", "software", "finance", "product", "healthcare", "operations_admin", "sales_marketing"):
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


def _role_label(domain: str) -> str:
    labels = {
        "operations_admin": "operations/admin",
        "sales_marketing": "sales/marketing",
        "cybersecurity": "cybersecurity/threat-focused",
    }
    return labels.get(domain, domain.replace("_", "/"))


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
            note=f"Role-aware check: this looks like a {_role_label(job_domain)} role, and the resume has matching domain evidence.",
        )

    if any((job_domain, resume_domain) in _COMPATIBLE_ROLE_DOMAINS for resume_domain in resume_domains):
        return RoleContext(
            job_domain=job_domain,
            resume_domains=resume_domains,
            alignment="adjacent",
            score_adjustment=-4,
            confidence_cap=0.82,
            note=f"Role-aware check: this is primarily a {_role_label(job_domain)} role. The resume has adjacent evidence, but not a perfect role-family match.",
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
            note=f"Role-aware check: this looks more like a {_role_label(job_domain)} role than a technical CS/software/data role, so technical keyword overlap is discounted.",
        )

    return RoleContext(
        job_domain=job_domain,
        resume_domains=resume_domains,
        alignment="weak",
        score_adjustment=-10,
        confidence_cap=0.72,
        note=f"Role-aware check: this role appears to be {_role_label(job_domain)}, while the resume evidence points elsewhere.",
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


def _is_noisy_format_warning(warning: str) -> bool:
    return warning.startswith(_NOISY_FORMAT_WARNING_PREFIXES)


def _with_quality_warning(document_quality: DocumentQuality, note: str | None) -> DocumentQuality:
    base_warnings = list(document_quality.warnings)
    substantive_warnings = [warning for warning in base_warnings if not _is_noisy_format_warning(warning)]
    had_format_warning = len(substantive_warnings) != len(base_warnings)

    warnings = substantive_warnings
    if note and note not in warnings:
        warnings.append(note)

    if not warnings and had_format_warning:
        warnings = [_SOFT_FORMAT_WARNING]

    return document_quality.model_copy(update={"warnings": warnings})


def _existing_gap_tokens(gap_groups: list[GapGroup]) -> set[str]:
    tokens: set[str] = set()
    for group in gap_groups:
        tokens.add(group.title.lower())
        tokens.update(skill.lower() for skill in group.skills)
    return tokens


def _capability_gaps(
    role_context: RoleContext,
    resume_text: str,
    job_text: str,
    existing_gap_groups: list[GapGroup],
) -> list[GapGroup]:
    existing_tokens = _existing_gap_tokens(existing_gap_groups)
    gaps: list[GapGroup] = []

    for capability in _CAPABILITY_GROUPS:
        if role_context.job_domain is not None and role_context.job_domain not in capability.domains:
            continue
        if not _matches_any(job_text, capability.job_terms):
            continue
        if _matches_any(resume_text, capability.resume_terms):
            continue
        if capability.title.lower() in existing_tokens:
            continue
        if any(skill.lower() in existing_tokens for skill in capability.skills):
            continue

        gaps.append(
            GapGroup(
                title=capability.title,
                category=capability.category,
                priority="high" if role_context.alignment in {"weak", "adjacent"} else "medium",
                skills=list(capability.skills),
                summary=capability.summary,
            )
        )

    return gaps[:3]


def _with_capability_gap_groups(base_gap_groups: list[GapGroup], capability_gaps: list[GapGroup]) -> list[GapGroup]:
    if not capability_gaps:
        return base_gap_groups
    return [*capability_gaps, *base_gap_groups][:5]


def _capability_coaching_actions(capability_gaps: list[GapGroup]) -> list[CoachingAction]:
    return [
        CoachingAction(
            action_type=CoachingActionType.LEARNING_FOCUS,
            priority=gap.priority,
            title=gap.title,
            category=gap.category,
            advice=gap.summary,
        )
        for gap in capability_gaps
    ]


def _with_capability_actions(
    existing_actions: list[CoachingAction],
    capability_gaps: list[GapGroup],
) -> list[CoachingAction]:
    if not capability_gaps:
        return existing_actions

    existing_titles = {action.title.lower() for action in existing_actions}
    added_actions = [
        action
        for action in _capability_coaching_actions(capability_gaps)
        if action.title.lower() not in existing_titles
    ]
    return [*added_actions, *existing_actions][:6]


def _capability_summary(capability_gaps: list[GapGroup]) -> str | None:
    if not capability_gaps:
        return None
    titles = ", ".join(gap.title for gap in capability_gaps[:3])
    return f"Capability gap check: the posting also signals broader role capabilities not fully captured by exact skill matching: {titles}."


def _with_capability_important_gaps(base_gaps: list[str], capability_gaps: list[GapGroup]) -> list[str]:
    ordered_gaps = [gap.title for gap in capability_gaps]
    ordered_gaps.extend(base_gaps)

    deduped: list[str] = []
    seen: set[str] = set()
    for gap in ordered_gaps:
        key = gap.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(gap)

    return deduped[:8]


def _with_polished_category_labels(category_coverage: list[CategoryCoverage]) -> list[CategoryCoverage]:
    return [
        coverage.model_copy(update={"category": _CATEGORY_LABELS.get(coverage.category, coverage.category)})
        for coverage in category_coverage
    ]


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
    capability_gaps = _capability_gaps(
        role_context,
        resume_text,
        job_description,
        analysis.gap_groups,
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
    capability_note = _capability_summary(capability_gaps)
    if capability_note:
        report_summary.append(capability_note)
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
    limitations.append(
        "Capability gap detection looks for broader role expectations beyond the curated skill ontology, so missing capability groups should be treated as directionally useful coaching signals."
    )

    return analysis.model_copy(
        update={
            "fit_summary": adjusted_summary,
            "document_quality": _with_quality_warning(analysis.document_quality, quality_note),
            "report_summary": report_summary[:8],
            "gap_groups": _with_capability_gap_groups(analysis.gap_groups, capability_gaps),
            "coaching_actions": _with_capability_actions(analysis.coaching_actions, capability_gaps),
            "category_coverage": _with_polished_category_labels(analysis.category_coverage),
            "important_gaps": _with_capability_important_gaps(analysis.important_gaps, capability_gaps),
            "limitations": limitations,
        }
    )
