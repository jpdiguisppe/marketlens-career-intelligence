"""Application package bootstrap.

Keep package-level work minimal. The job-search adapters isolate intent,
occupation, location, source coverage, and cross-sector correctness behavior
from provider-fetching code.
"""

from . import job_search as _job_search
from .job_search_correctness_patch import apply_job_search_correctness_patch
from .job_search_intent_patch import apply_job_search_intent_patch
from .job_search_location_patch import apply_job_search_location_patch
from .job_search_occupation_overrides import apply_job_search_occupation_overrides
from .job_search_source_expansion import apply_job_search_source_expansion

apply_job_search_intent_patch(_job_search)
apply_job_search_occupation_overrides(_job_search)
apply_job_search_correctness_patch(_job_search)
apply_job_search_location_patch(_job_search)
apply_job_search_source_expansion(_job_search)
