"""Evidence-based analysis pipeline for MarketLens."""

from app.analysis.schemas import SmartFitAnalysisRequest, SmartFitAnalysisResponse
from app.analysis.service import AnalysisInputError
from app.analysis.provenance_patch import install_provenance_patch
from app.analysis.model_failure_status_patch import install_model_failure_status_patch
from app.analysis.provider_telemetry_summary_policy import (
    attach_provider_telemetry,
    begin_provider_telemetry,
    install_coaching_telemetry_patch,
    install_extraction_telemetry_patch,
    reset_provider_telemetry,
)
from app.safe_logging import sensitive_log_context
import app.analysis.service as _service

# Request-scoped provenance, failure metadata, and extraction telemetry must wrap
# the base service before the role-aware layer captures it.
install_provenance_patch()
install_model_failure_status_patch()
install_extraction_telemetry_patch()

from app.analysis.role_aware_stable import (  # noqa: E402
    analyze_smart_fit as _role_aware_analyze_smart_fit,
)
from app.analysis.role_domain_priority_patch import (  # noqa: E402
    install_role_domain_priority_patch,
)
from app.analysis.responsibility_label_normalization import (  # noqa: E402
    install_responsibility_label_normalization,
)
from app.analysis.semantic_merge_patch import install_semantic_merge_patch  # noqa: E402
from app.analysis.personalized_coaching_reliability_patch import (  # noqa: E402
    install_personalized_coaching_reliability_patch,
)
from app.analysis.personalized_coaching_title_patch import (  # noqa: E402
    install_personalized_coaching_title_patch,
)
from app.analysis.coaching_failure_status_patch import (  # noqa: E402
    install_coaching_failure_status_patch,
)

# A specific job-function signal such as ``marketing`` must win over a generic
# shared title token such as ``coordinator``.
install_role_domain_priority_patch()

# Exact grounded responsibility phrases may use concise canonical capability
# labels while retaining their original source quotes and provenance.
install_responsibility_label_normalization()

# Model assistance may add grounded semantic recall, but deterministic parsing
# remains authoritative for resume-proof strength and scoring boundaries.
install_semantic_merge_patch()

# The provider chooses only grounded assessment references. MarketLens remains
# authoritative for canonical evidence and permits distinct coaching actions to
# reuse the same reference without allowing true duplicate actions.
install_personalized_coaching_reliability_patch()

# Display titles are backend-owned. Short provider titles are normalized only so
# the plan can be parsed, then replaced after the action passes strict reference,
# status, basis, and action-type validation.
install_personalized_coaching_title_patch()

# Safe machine-readable coaching failure codes are applied only after every
# existing coaching request and validation patch has been installed.
install_coaching_failure_status_patch()

# Coaching telemetry observes the final, fully validated request boundary.
install_coaching_telemetry_patch()

from app.analysis.personalized_coaching import apply_personalized_coaching  # noqa: E402


def analyze_smart_fit(
    resume_text: str,
    job_description: str,
    use_model_assisted: bool = False,
) -> SmartFitAnalysisResponse:
    """Run scoring and coaching, then attach document-free provider telemetry.

    The coaching and telemetry layers cannot change scores, assessments, hard
    requirements, evidence, or provenance. Telemetry and sensitive log values
    are request-scoped and discarded after this response is assembled.
    """

    telemetry_token = begin_provider_telemetry()
    try:
        with sensitive_log_context(resume_text, job_description):
            analysis = _role_aware_analyze_smart_fit(
                resume_text=resume_text,
                job_description=job_description,
                use_model_assisted=use_model_assisted,
            )
            coached = apply_personalized_coaching(
                analysis,
                use_model_assisted=use_model_assisted,
            )
            return attach_provider_telemetry(
                coached,
                use_model_assisted=use_model_assisted,
            )
    finally:
        reset_provider_telemetry(telemetry_token)


# Keep direct imports from app.analysis.service behavior-compatible with the
# package export while the layered analysis pipeline is assembled here.
_service.analyze_smart_fit = analyze_smart_fit

__all__ = [
    "AnalysisInputError",
    "SmartFitAnalysisRequest",
    "SmartFitAnalysisResponse",
    "analyze_smart_fit",
]
