"""Support documented and live SmartRecruiters posting-detail shapes.

The Posting API has returned both direct string jobAd fields and nested section
objects. MarketLens accepts both, gives documented nested sections priority,
and leaves all existing filtering/scoring rules intact.
"""

from __future__ import annotations

from typing import Any


_SECTION_SPECS: tuple[tuple[str, str], ...] = (
    ("companyDescription", "Company Description"),
    ("jobDescription", "Job Description"),
    ("qualifications", "Qualifications"),
    ("additionalInformation", "Additional Information"),
)


def _section_value(value: Any, fallback_title: str) -> tuple[str, str] | None:
    if isinstance(value, str):
        text = value.strip()
        return (fallback_title, text) if text else None
    if not isinstance(value, dict):
        return None

    text = value.get("text")
    if not isinstance(text, str) or not text.strip():
        return None
    title = value.get("title")
    cleaned_title = title.strip() if isinstance(title, str) and title.strip() else fallback_title
    return cleaned_title, text.strip()


def _job_ad_containers(job_ad: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(job_ad, dict):
        return ()
    sections = job_ad.get("sections")
    if isinstance(sections, dict):
        return sections, job_ad
    return (job_ad,)


def _uses_nested_sections(details: dict[str, Any]) -> bool:
    job_ad = details.get("jobAd")
    return isinstance(job_ad, dict) and isinstance(job_ad.get("sections"), dict)


def extract_smartrecruiters_sections(details: dict[str, Any]) -> list[tuple[str, str]]:
    containers = _job_ad_containers(details.get("jobAd"))
    extracted: list[tuple[str, str]] = []
    seen_text: set[str] = set()

    for key, fallback_title in _SECTION_SPECS:
        section: tuple[str, str] | None = None
        for container in containers:
            section = _section_value(container.get(key), fallback_title)
            if section is not None:
                break
        if section is None:
            continue
        title, text = section
        dedupe_key = text.strip().lower()
        if dedupe_key in seen_text:
            continue
        seen_text.add(dedupe_key)
        extracted.append((title, text))

    return extracted


def apply_smartrecruiters_live_shape_patch(source_expansion: Any) -> None:
    if getattr(source_expansion, "_LIVE_SHAPE_PATCH_APPLIED", False):
        return

    def detail_description(job_search: Any, details: dict[str, Any], title: str) -> str:
        parts: list[str] = []
        for section_title, raw_text in extract_smartrecruiters_sections(details):
            cleaned_text = job_search.clean_job_description(raw_text)
            if not cleaned_text:
                continue
            cleaned_title = job_search.clean_job_description(section_title)
            parts.append(f"{cleaned_title}\n{cleaned_text}" if cleaned_title else cleaned_text)

        if not _uses_nested_sections(details):
            # Some older/alternate Posting API responses expose direct string
            # jobAd fields. Preserve their existing level signal for search
            # compatibility, but label it explicitly as provider metadata rather
            # than presenting it as a MarketLens classification.
            provider_level = source_expansion._metadata_label(details, "experienceLevel")
            if provider_level:
                parts.append(f"Provider experience metadata\n{provider_level}")

        # Documented nested sections are the production shape that triggered the
        # bug. Their actual posting text remains separate from provider metadata,
        # preventing contradictory labels such as Principal + Entry Level from
        # entering the card preview or Smart Fit input.
        return "\n\n".join(parts).strip() or title

    source_expansion._detail_description = detail_description
    source_expansion._LIVE_SHAPE_PATCH_APPLIED = True
