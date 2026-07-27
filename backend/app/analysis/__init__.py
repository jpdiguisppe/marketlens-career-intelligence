"""Evidence-based analysis pipeline for MarketLens."""

from app.analysis.schemas import SmartFitAnalysisRequest, SmartFitAnalysisResponse
from app.analysis.service import AnalysisInputError
from app.analysis.provenance_patch import install_provenance_patch
import app.analysis.service as _service

# Request-scoped provenance must wrap the base service before the role-aware
# layer captures it. This ensures every exact requirement assessment is grounded
# before role and capability summaries are derived.
install_provenance_patch()

from app.analysis.role_aware_stable import (  # noqa: E402
    analyze_smart_fit as _role_aware_analyze_smart_fit,
)
from app.analysis.role_domain_priority_patch import (  # noqa: E402
    install_role_domain_priority_patch,
)
from app.analysis.semantic_merge_patch import install_semantic_merge_patch  # noqa: E402
from app.analysis.personalized_coaching import apply_personalized_coaching  # noqa: E402

# A specific job-function signal such as ``marketing`` must win over a generic
# shared title token such as ``coordinator``.
install_role_domain_priority_patch()

# Model assistance may add grounded semantic recall, but deterministic parsing
# remains authoritative for resume-proof strength and scoring boundaries.
install_semantic_merge_patch()


def analyze_smart_fit(
    resume_text: str,
    job_description: str,
    use_model_assisted: bool = False,
) -> SmartFitAnalysisResponse:
    """Run scoring first, then add evidence-bound optional coaching.

    The coaching layer receives only the completed grounded response and may
    update coaching text and metadata. It cannot change scoring, assessments,
    hard requirements, or provenance.
    """

    analysis = _role_aware_analyze_smart_fit(
        resume_text=resume_text,
        job_description=job_description,
        use_model_assisted=use_model_assisted,
    )
    return apply_personalized_coaching(
        analysis,
        use_model_assisted=use_model_assisted,
    )


# Keep direct imports from app.analysis.service behavior-compatible with the
# package export while the layered analysis pipeline is assembled here.
_service.analyze_smart_fit = analyze_smart_fit

__all__ = [
    "AnalysisInputError",
    "SmartFitAnalysisRequest",
    "SmartFitAnalysisResponse",
    "analyze_smart_fit",
]
