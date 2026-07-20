"""Application package bootstrap.

Keep package-level work minimal. The job-search intent patch keeps Milestone 2
behavior fixes isolated from provider-fetching code while we stabilize search.
"""

from . import job_search as _job_search
from .job_search_intent_patch import apply_job_search_intent_patch
from .job_search_occupation_overrides import apply_job_search_occupation_overrides

apply_job_search_intent_patch(_job_search)
apply_job_search_occupation_overrides(_job_search)
