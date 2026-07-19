"""Evidence-based analysis pipeline for MarketLens."""

from app.analysis.schemas import SmartFitAnalysisRequest, SmartFitAnalysisResponse
from app.analysis.service import AnalysisInputError
from app.analysis.role_aware import analyze_smart_fit
import app.analysis.service as _service

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
