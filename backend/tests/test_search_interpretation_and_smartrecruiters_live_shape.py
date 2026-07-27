from __future__ import annotations

from app import job_search
from app.analysis.service import analyze_smart_fit
from app.job_search_query_interpretation import (
    canonicalize_job_query,
    interpret_job_query,
)
from app.job_search_source_expansion import _normalize_posting, _search_terms
from app.skill_extractor import extract_skills
from app.smartrecruiters_live_shape_patch import extract_smartrecruiters_sections
from app.smartrecruiters_sources import SMARTRECRUITERS_SOURCES


def _source(identifier: str):
    return next(source for source in SMARTRECRUITERS_SOURCES if source.identifier == identifier)


def test_common_abbreviations_are_canonicalized_before_provider_routing() -> None:
    assert canonicalize_job_query("SWE") == "software engineer"
    assert canonicalize_job_query("SDE") == "software development engineer"
    assert canonicalize_job_query("SRE") == "site reliability engineer"
    assert canonicalize_job_query("MLE") == "machine learning engineer"
    assert canonicalize_job_query("SOC analyst") == "security operations center analyst"
    assert canonicalize_job_query("RN") == "registered nurse"
    assert canonicalize_job_query("FP&A") == "financial planning and analysis"
    assert canonicalize_job_query("UX") == "user experience"


def test_ambiguous_abbreviations_are_not_guessed() -> None:
    for query in ("PM", "SE", "BA", "CS", "DS", "PT", "OT"):
        interpretation = interpret_job_query(query)
        assert interpretation.canonical_query == query.lower()
        assert interpretation.abbreviation_expansions == ()


def test_high_confidence_spelling_repairs_preserve_role_meaning() -> None:
    interpretation = interpret_job_query("entry lvl sofware enginer")
    assert interpretation.canonical_query == "entry level software engineer"
    assert "lvl -> level" in interpretation.abbreviation_expansions
    assert "sofware -> software" in interpretation.spelling_corrections
    assert "enginer -> engineer" in interpretation.spelling_corrections


def test_swe_and_software_engineer_use_same_search_path() -> None:
    assert _search_terms("SWE") == _search_terms("Software Engineer")
    assert job_search._query_job_function("SWE") == "software"
    assert job_search._query_job_function("Software Engineer") == "software"

    swe_score = job_search._score_job(
        "Software Engineer",
        "Build Python APIs and SQL services.",
        "SWE",
        "any",
        company="City of Philadelphia",
    )
    canonical_score = job_search._score_job(
        "Software Engineer",
        "Build Python APIs and SQL services.",
        "Software Engineer",
        "any",
        company="City of Philadelphia",
    )
    assert swe_score == canonical_score
    assert swe_score > 0

    # Existing wrong-occupation rejection remains in force.
    assert job_search._score_job(
        "Analytics Engineer",
        "Build analytics models and reporting pipelines.",
        "SWE",
        "any",
    ) == 0


def test_live_nested_smartrecruiters_sections_are_extracted() -> None:
    details = {
        "jobAd": {
            "sections": {
                "companyDescription": {
                    "title": "Company Description",
                    "text": "<p>Public technology organization.</p>",
                },
                "jobDescription": {
                    "title": "Job Description",
                    "text": "<p>Build reliable Python FastAPI services and REST APIs.</p>",
                },
                "qualifications": {
                    "title": "Qualifications",
                    "text": "<p>Python and SQL are required. Docker is preferred.</p>",
                },
                "additionalInformation": {
                    "title": "Additional Information",
                    "text": "<p>Collaborate with engineering teams.</p>",
                },
            }
        }
    }

    sections = extract_smartrecruiters_sections(details)
    assert [title for title, _ in sections] == [
        "Company Description",
        "Job Description",
        "Qualifications",
        "Additional Information",
    ]
    assert "Python and SQL are required" in sections[2][1]


def test_live_smartrecruiters_posting_reaches_deterministic_smart_fit() -> None:
    source = _source("CityofPhiladelphia")
    raw = {
        "id": "live-shape",
        "name": "Software Engineer",
        "location": {
            "city": "Philadelphia",
            "region": "PA",
            "country": "us",
            "remote": False,
        },
        "experienceLevel": {"id": "entry_level", "label": "Entry Level"},
        "typeOfEmployment": {"label": "Full-time"},
    }
    details = {
        **raw,
        "applyUrl": "https://jobs.smartrecruiters.com/CityofPhiladelphia/live-shape/apply",
        "company": {"name": "City of Philadelphia"},
        "jobAd": {
            "sections": {
                "jobDescription": {
                    "title": "Responsibilities",
                    "text": "<p>Build reliable backend APIs using Python and FastAPI.</p>",
                },
                "qualifications": {
                    "title": "Required Qualifications",
                    "text": "<p>Python and SQL are required. Docker is preferred.</p>",
                },
            }
        },
    }

    job = _normalize_posting(job_search, source, raw, details)
    assert job is not None
    assert "Build reliable backend APIs" in job.description
    assert "Python and SQL are required" in job.description
    assert "Entry Level" not in job.description
    assert "Full-time" not in job.description
    assert {"Python", "SQL", "FastAPI", "Docker"}.issubset(set(extract_skills(job.description)))

    analysis = analyze_smart_fit(
        resume_text=(
            "PROJECTS\nBuilt a Python FastAPI service backed by PostgreSQL.\n"
            "SKILLS\nPython, SQL, FastAPI, PostgreSQL"
        ),
        job_description=job.description,
        use_model_assisted=False,
    )
    assert analysis.requirement_assessments
    assert "Python" in {item.skill for item in analysis.requirement_assessments}


def test_principal_title_overrides_conflicting_provider_entry_metadata() -> None:
    source = _source("CityofPhiladelphia")
    raw = {
        "id": "principal-conflict",
        "name": "Principal Software Engineer",
        "location": {
            "city": "Philadelphia",
            "region": "PA",
            "country": "us",
            "remote": False,
        },
        "experienceLevel": {"id": "entry_level", "label": "Entry Level"},
    }
    details = {
        **raw,
        "applyUrl": "https://jobs.smartrecruiters.com/CityofPhiladelphia/principal-conflict/apply",
        "company": {"name": "City of Philadelphia"},
        "jobAd": {
            "sections": {
                "jobDescription": {
                    "title": "Job Description",
                    "text": "Lead architecture and build Python services.",
                },
                "qualifications": {
                    "title": "Qualifications",
                    "text": "Seven years of software engineering experience required.",
                },
            }
        },
    }

    job = _normalize_posting(job_search, source, raw, details)
    assert job is not None
    assert "Entry Level" not in job.description
    assert job_search._score_job(
        job.title,
        job.description,
        "Software Engineer",
        "entry",
        company=job.company,
    ) == 0
    assert job_search._score_job(
        job.title,
        job.description,
        "Software Engineer",
        "senior",
        company=job.company,
    ) > 0
