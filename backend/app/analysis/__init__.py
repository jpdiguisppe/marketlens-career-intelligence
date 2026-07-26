"""Evidence-based analysis pipeline for MarketLens."""

from app.analysis.schemas import SmartFitAnalysisRequest, SmartFitAnalysisResponse
from app.analysis.service import AnalysisInputError
from app.analysis.role_aware_stable import analyze_smart_fit
from app.analysis.role_domain_priority_patch import install_role_domain_priority_patch
from app.analysis.semantic_merge_patch import install_semantic_merge_patch
import app.analysis.service as _service

# A specific job-function signal such as ``marketing`` must win over a generic
# shared title token such as ``coordinator``.
install_role_domain_priority_patch()

# Model assistance may add grounded semantic recall, but deterministic parsing
# remains authoritative for resume-proof strength and scoring boundaries.
install_semantic_merge_patch()

# Keep direct imports from app.analysis.service behavior-compatible with the
# package export while Milestone 3 role-aware scoring is layered on top of the
# existing deterministic Smart Fit engine.
_service.analyze_smart_fit = analyze_smart_fit

__all__ = [
    "AnalysisInputError",
    "SmartFitAnalysisRequest",
    "SmartFitAnalysisResponse",
    "analyze_smart_fit",
]
