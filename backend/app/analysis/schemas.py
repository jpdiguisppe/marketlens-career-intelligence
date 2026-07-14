from enum import Enum

from pydantic import BaseModel, Field

SMART_RESUME_MAX_LENGTH = 25_000
SMART_JOB_MAX_LENGTH = 50_000


class DocumentKind(str, Enum):
    RESUME = "resume"
    JOB_POSTING = "job_posting"


class SectionKind(str, Enum):
    SUMMARY = "summary"
    SKILLS = "skills"
    EXPERIENCE = "experience"
    PROJECTS = "projects"
    EDUCATION = "education"
    COURSEWORK = "coursework"
    CERTIFICATIONS = "certifications"
    AWARDS = "awards"
    RESPONSIBILITIES = "responsibilities"
    REQUIRED = "required_qualifications"
    PREFERRED = "preferred_qualifications"
    COMPANY = "company_description"
    BENEFITS = "benefits"
    OTHER = "other"


class RequirementType(str, Enum):
    REQUIRED_QUALIFICATION = "required_qualification"
    CORE_RESPONSIBILITY = "core_responsibility"
    PREFERRED_QUALIFICATION = "preferred_qualification"
    SUPPORTING_CONTEXT = "supporting_context"


class EvidenceStatus(str, Enum):
    DEMONSTRATED = "demonstrated"
    EXPLICIT = "explicit"
    MENTIONED = "mentioned"
    IMPLIED = "implied"
    RELATED = "related"
    MISSING = "missing"


class HardRequirementStatus(str, Enum):
    MEETS = "meets"
    DOES_NOT_MEET = "does_not_meet"
    UNCLEAR = "unclear"


class FitBand(str, Enum):
    STRONG_ALIGNMENT = "strong_alignment"
    CREDIBLE_ALIGNMENT = "credible_alignment"
    PARTIAL_ALIGNMENT = "partial_alignment"
    LIMITED_ALIGNMENT = "limited_alignment"


class CoachingActionType(str, Enum):
    RESUME_REWRITE = "resume_rewrite"
    INTERVIEW_PREP = "interview_prep"
    LEARNING_FOCUS = "learning_focus"
    LOWER_PRIORITY = "lower_priority"
    HARD_REQUIREMENT_CHECK = "hard_requirement_check"


class ParsedSection(BaseModel):
    kind: SectionKind
    heading: str | None = None
    text: str
    start_line: int
    end_line: int


class JobRequirement(BaseModel):
    skill: str
    requirement_type: RequirementType
    weight: float = Field(ge=0.0, le=1.0)
    source_text: str
    source_section: SectionKind
    mention_count: int = Field(default=1, ge=1)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class ResumeEvidence(BaseModel):
    skill: str
    status: EvidenceStatus
    strength: float = Field(ge=0.0, le=1.0)
    source_text: str
    source_section: SectionKind
    explanation: str


class RequirementAssessment(BaseModel):
    skill: str
    requirement_type: RequirementType
    weight: float = Field(ge=0.0, le=1.0)
    status: EvidenceStatus
    strength: float = Field(ge=0.0, le=1.0)
    resume_evidence: list[str] = Field(default_factory=list)
    job_evidence: str
    explanation: str


class HardRequirementAssessment(BaseModel):
    category: str
    requirement: str
    status: HardRequirementStatus
    source_text: str
    resume_evidence: str | None = None
    explanation: str


class DocumentQuality(BaseModel):
    resume_extraction_confidence: float = Field(ge=0.0, le=1.0)
    job_extraction_confidence: float = Field(ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)


class FitSummary(BaseModel):
    score: int = Field(ge=0, le=100)
    band: FitBand
    confidence: float = Field(ge=0.0, le=1.0)
    headline: str


class CategoryCoverage(BaseModel):
    category: str
    score: int = Field(ge=0, le=100)
    priority_weight: float = Field(ge=0.0)
    strong_skills: list[str] = Field(default_factory=list)
    weak_or_missing_skills: list[str] = Field(default_factory=list)
    summary: str


class GapGroup(BaseModel):
    title: str
    category: str
    priority: str
    skills: list[str] = Field(default_factory=list)
    summary: str


class CoachingAction(BaseModel):
    action_type: CoachingActionType
    priority: str
    title: str
    skill: str | None = None
    category: str | None = None
    source_evidence: list[str] = Field(default_factory=list)
    job_evidence: str | None = None
    advice: str


class SmartFitAnalysisRequest(BaseModel):
    resume_text: str = Field(
        ...,
        min_length=1,
        max_length=SMART_RESUME_MAX_LENGTH,
        description="Resume text to evaluate. It is analyzed for this request and is not written to the shared job-posting database.",
    )
    job_description: str = Field(
        ...,
        min_length=1,
        max_length=SMART_JOB_MAX_LENGTH,
        description="One complete job description to analyze, including responsibilities and qualifications.",
    )
    use_model_assisted: bool = Field(
        default=False,
        description="When true, the backend may use the configured model-assisted extractor. If disabled or unavailable, the deterministic engine is used instead.",
    )


class SmartFitAnalysisResponse(BaseModel):
    fit_summary: FitSummary
    document_quality: DocumentQuality
    hard_requirements: list[HardRequirementAssessment]
    requirement_assessments: list[RequirementAssessment]
    category_coverage: list[CategoryCoverage]
    coaching_actions: list[CoachingAction]
    report_summary: list[str]
    gap_groups: list[GapGroup]
    resume_skills_found: list[str]
    job_relevant_resume_skills: list[str]
    other_resume_skills: list[str]
    strong_matches: list[str]
    related_matches: list[str]
    important_gaps: list[str]
    under_sold_experience: list[str]
    lower_priority_items: list[str]
    recommendations: list[str]
    limitations: list[str]
    analysis_engine: str = "deterministic"
    model_assisted_status: str = "not_requested"
