"""Application package bootstrap.

Keep package-level work minimal. The job-search adapters isolate intent,
occupation, level, location, source coverage, and cross-sector correctness
behavior from provider-fetching code.
"""

from .http_safety import install_safe_fastapi_defaults
from .safe_logging import install_safe_log_record_factory

# Install process-wide output safety before application modules create loggers or
# the main module imports FastAPI.
install_safe_log_record_factory()
install_safe_fastapi_defaults()

from . import job_search as _job_search
from . import job_search_source_expansion as _source_expansion
from . import job_search_universal_compatibility as _universal_compatibility
from . import job_search_universal_occupation as _universal_occupation
from . import occupation_catalog_runtime as _occupation_runtime
from . import smartrecruiters_sources as _smartrecruiters_sources
from .job_search_abbreviation_guard import apply_job_search_abbreviation_guard
from .job_search_correctness_patch import apply_job_search_correctness_patch
from .job_search_intent_patch import apply_job_search_intent_patch
from .job_search_level_patch import apply_job_search_level_patch
from .job_search_location_patch import apply_job_search_location_patch
from .job_search_occupation_overrides import apply_job_search_occupation_overrides
from .job_search_query_interpretation import apply_job_search_query_interpretation
from .job_search_sector_breadth import apply_broad_sector_search
from .job_search_specific_occupation_patch import (
    apply_job_search_specific_occupation_patch,
)
from .job_search_universal_compatibility import (
    apply_universal_compatibility,
    capture_legacy_search_functions,
)
from .job_search_universal_occupation import apply_universal_occupation_search
from .occupation_runtime_hardening import apply_occupation_runtime_hardening
from .smartrecruiters_live_shape_patch import apply_smartrecruiters_live_shape_patch
from .smartrecruiters_source_extensions import apply_smartrecruiters_source_extensions

apply_job_search_intent_patch(_job_search)
apply_job_search_occupation_overrides(_job_search)
apply_job_search_correctness_patch(_job_search)
apply_job_search_specific_occupation_patch(_job_search)
apply_job_search_level_patch(_job_search)
apply_job_search_location_patch(_job_search)
apply_job_search_query_interpretation(_job_search, _source_expansion)
apply_job_search_abbreviation_guard(_job_search)
apply_smartrecruiters_live_shape_patch(_source_expansion)
apply_smartrecruiters_source_extensions(
    _smartrecruiters_sources,
    _source_expansion,
)
_source_expansion.apply_job_search_source_expansion(_job_search)
capture_legacy_search_functions(_job_search, _source_expansion)
apply_occupation_runtime_hardening(
    _occupation_runtime,
    _universal_occupation,
    _universal_compatibility,
)
# The adapter originally imported the raw catalog callables. Replace those
# module globals with the hardened cached production runtime before wrapping
# the established search stack.
_universal_occupation.interpret_occupation_query = (
    _occupation_runtime.interpret_occupation_query
)
_universal_occupation.normalize_occupation_text = (
    _occupation_runtime.normalize_occupation_text
)
_universal_occupation.title_matches_occupation = (
    _occupation_runtime.title_matches_occupation
)
apply_universal_occupation_search(_job_search, _source_expansion)
apply_universal_compatibility(_job_search, _source_expansion)
apply_broad_sector_search(_job_search)
