"""Offline reliability evaluation for Milestone 8E.

The harness intentionally performs no provider calls. It repeatedly evaluates
sanitized fixtures, checks evidence and output invariants, and temporarily
forces provider configuration off to prove deterministic fallback preservation.
Reports contain identifiers, metrics, fingerprints, and failure codes only;
resume and job text are never included.
"""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any, Iterator

from app.analysis import analyze_smart_fit
from app.analysis.evaluation import load_smart_fit_benchmark
from app.analysis.schemas import (
    DocumentKind,
    EvidenceStatus,
    SmartFitAnalysisResponse,
)

DEFAULT_OPERATIONAL_BENCHMARK_PATH = (
    Path(__file__).resolve().parents[2]
    / "evaluation"
    / "operational_reliability_benchmark.json"
)
_PROVIDER_ENVIRONMENT_KEYS = (
    "AI_ANALYSIS_ENABLED",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OPENAI_BASE_URL",
    "OPENAI_TIMEOUT_SECONDS",
)
_RESPONSE_METADATA_FIELDS = {
    "analysis_engine",
    "model_assisted_status",
    "coaching_engine",
    "coaching_status",
}


def _normalized(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 1.0


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _analysis_payload(analysis: SmartFitAnalysisResponse) -> dict[str, Any]:
    return analysis.model_dump(mode="json")


def _fallback_preservation_payload(
    analysis: SmartFitAnalysisResponse,
) -> dict[str, Any]:
    payload = _analysis_payload(analysis)
    for field in _RESPONSE_METADATA_FIELDS:
        payload.pop(field, None)
    return payload


def _failure(
    *,
    case_id: str,
    check: str,
    actual: Any,
    run: int | None = None,
    expected: Any | None = None,
) -> dict[str, Any]:
    failure = {
        "case_id": case_id,
        "check": check,
        "actual": actual,
    }
    if run is not None:
        failure["run"] = run
    if expected is not None:
        failure["expected"] = expected
    return failure


def _quote_is_present(quote: str, document: str) -> bool:
    normalized_quote = _normalized(quote)
    return bool(normalized_quote) and normalized_quote in _normalized(document)


def validate_analysis_invariants(
    analysis: SmartFitAnalysisResponse,
    *,
    case_id: str,
    resume_text: str,
    job_description: str,
    run: int | None = None,
) -> list[dict[str, Any]]:
    """Return safe, document-free invariant failures for one response."""

    failures: list[dict[str, Any]] = []
    assessments_by_skill: dict[str, Any] = {}
    source_identities: set[tuple[str, str, str]] = set()

    for assessment in analysis.requirement_assessments:
        skill_key = _normalized(assessment.skill)
        if skill_key in assessments_by_skill:
            failures.append(
                _failure(
                    case_id=case_id,
                    run=run,
                    check="duplicate_requirement_label",
                    actual=assessment.skill,
                )
            )
        assessments_by_skill[skill_key] = assessment

        source_identity = (
            skill_key,
            assessment.requirement_type.value,
            _normalized(assessment.job_evidence),
        )
        if source_identity in source_identities:
            failures.append(
                _failure(
                    case_id=case_id,
                    run=run,
                    check="duplicate_grounded_requirement_identity",
                    actual={
                        "skill": assessment.skill,
                        "requirement_type": assessment.requirement_type.value,
                    },
                )
            )
        source_identities.add(source_identity)

        if not assessment.grounded:
            failures.append(
                _failure(
                    case_id=case_id,
                    run=run,
                    check="assessment_not_grounded",
                    actual=assessment.skill,
                )
            )

        citation = assessment.job_provenance
        if citation is None or not citation.grounded:
            failures.append(
                _failure(
                    case_id=case_id,
                    run=run,
                    check="missing_grounded_job_provenance",
                    actual=assessment.skill,
                )
            )
        else:
            if citation.document_kind != DocumentKind.JOB_POSTING:
                failures.append(
                    _failure(
                        case_id=case_id,
                        run=run,
                        check="wrong_job_provenance_document_kind",
                        actual=assessment.skill,
                    )
                )
            if _normalized(citation.quote) != _normalized(assessment.job_evidence):
                failures.append(
                    _failure(
                        case_id=case_id,
                        run=run,
                        check="job_evidence_provenance_mismatch",
                        actual=assessment.skill,
                    )
                )
            if not _quote_is_present(citation.quote, job_description):
                failures.append(
                    _failure(
                        case_id=case_id,
                        run=run,
                        check="job_quote_not_in_source",
                        actual=assessment.skill,
                    )
                )

        for resume_citation in assessment.resume_provenance:
            if (
                resume_citation.document_kind != DocumentKind.RESUME
                or not resume_citation.grounded
                or not _quote_is_present(resume_citation.quote, resume_text)
            ):
                failures.append(
                    _failure(
                        case_id=case_id,
                        run=run,
                        check="invalid_resume_provenance",
                        actual=assessment.skill,
                    )
                )

        for resume_evidence in assessment.resume_evidence:
            if not _quote_is_present(resume_evidence, resume_text):
                failures.append(
                    _failure(
                        case_id=case_id,
                        run=run,
                        check="resume_evidence_not_in_source",
                        actual=assessment.skill,
                    )
                )

    for requirement in analysis.hard_requirements:
        if not requirement.grounded or not _quote_is_present(
            requirement.source_text, job_description
        ):
            failures.append(
                _failure(
                    case_id=case_id,
                    run=run,
                    check="invalid_hard_requirement_grounding",
                    actual=requirement.category,
                )
            )
        if requirement.resume_evidence and not _quote_is_present(
            requirement.resume_evidence, resume_text
        ):
            failures.append(
                _failure(
                    case_id=case_id,
                    run=run,
                    check="hard_requirement_resume_evidence_not_in_source",
                    actual=requirement.category,
                )
            )

    expected_strong_matches = {
        _normalized(assessment.skill)
        for assessment in analysis.requirement_assessments
        if assessment.status in {EvidenceStatus.DEMONSTRATED, EvidenceStatus.EXPLICIT}
        and assessment.weight >= 0.5
        and assessment.grounded
    }
    actual_strong_matches = {_normalized(skill) for skill in analysis.strong_matches}
    if actual_strong_matches != expected_strong_matches:
        failures.append(
            _failure(
                case_id=case_id,
                run=run,
                check="unsupported_or_missing_strong_match",
                expected=sorted(expected_strong_matches),
                actual=sorted(actual_strong_matches),
            )
        )

    assessment_skills = set(assessments_by_skill)
    allowed_categories = {
        _normalized(item.category) for item in analysis.category_coverage
    } | {_normalized(item.category) for item in analysis.gap_groups}
    allowed_job_evidence = {
        _normalized(item.job_evidence)
        for item in analysis.requirement_assessments
        if item.job_evidence
    }
    for item in analysis.hard_requirements:
        allowed_job_evidence.add(_normalized(item.source_text))
        allowed_job_evidence.add(_normalized(item.requirement))
    for group in analysis.gap_groups:
        allowed_job_evidence.update(_normalized(value) for value in group.job_evidence)

    seen_actions: set[tuple[str, str, str]] = set()
    for action in analysis.coaching_actions:
        action_key = (
            action.action_type.value,
            _normalized(action.skill or action.category or ""),
            _normalized(action.title),
        )
        if action_key in seen_actions:
            failures.append(
                _failure(
                    case_id=case_id,
                    run=run,
                    check="duplicate_coaching_action",
                    actual=action.title,
                )
            )
        seen_actions.add(action_key)

        reference_is_valid = False
        if action.skill:
            reference_is_valid = _normalized(action.skill) in assessment_skills
        elif action.category:
            reference_is_valid = _normalized(action.category) in allowed_categories
        elif action.job_evidence:
            reference_is_valid = _normalized(action.job_evidence) in allowed_job_evidence

        if not reference_is_valid:
            failures.append(
                _failure(
                    case_id=case_id,
                    run=run,
                    check="coaching_reference_not_grounded",
                    actual=action.title,
                )
            )

    if analysis.grounding_warnings:
        failures.append(
            _failure(
                case_id=case_id,
                run=run,
                check="grounding_warnings_present",
                actual=len(analysis.grounding_warnings),
                expected=0,
            )
        )

    return failures


def load_operational_reliability_benchmark(
    path: Path | None = None,
) -> dict[str, Any]:
    benchmark_path = path or DEFAULT_OPERATIONAL_BENCHMARK_PATH
    with benchmark_path.open(encoding="utf-8") as benchmark_file:
        benchmark = json.load(benchmark_file)

    if benchmark.get("version") != 1:
        raise ValueError("Unsupported operational reliability benchmark version.")

    runs_per_case = int(benchmark.get("runs_per_case", 0))
    if runs_per_case < 3:
        raise ValueError("Operational reliability cases must run at least three times.")

    raw_cases = benchmark.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("Operational reliability benchmark cases must be non-empty.")

    smart_fit_cases = {
        case["id"]: case for case in load_smart_fit_benchmark()["cases"]
    }
    resolved_cases: list[dict[str, Any]] = []
    case_ids: set[str] = set()
    sectors: set[str] = set()
    fallback_cases = 0

    for raw_case in raw_cases:
        case_id = str(raw_case.get("id") or "").strip()
        if not case_id or case_id in case_ids:
            raise ValueError("Operational reliability case ids must be present and unique.")

        source_case_id = str(raw_case.get("source_case_id") or "").strip()
        source_case = smart_fit_cases.get(source_case_id) if source_case_id else None
        if source_case_id and source_case is None:
            raise ValueError(
                f"Operational reliability case {case_id!r} references unknown Smart Fit case {source_case_id!r}."
            )

        sector = str(
            raw_case.get("sector")
            or (source_case or {}).get("sector")
            or ""
        ).strip()
        resume_text = str(
            raw_case.get("resume_text")
            or (source_case or {}).get("resume_text")
            or ""
        ).strip()
        job_description = str(
            raw_case.get("job_description")
            or (source_case or {}).get("job_description")
            or ""
        ).strip()
        if not sector or not resume_text or not job_description:
            raise ValueError(
                f"Operational reliability case {case_id!r} must resolve sector and document text."
            )

        check_fallback = bool(raw_case.get("check_disabled_provider_fallback", False))
        fallback_cases += int(check_fallback)
        case_ids.add(case_id)
        sectors.add(sector)
        resolved_cases.append(
            {
                "id": case_id,
                "sector": sector,
                "resume_text": resume_text,
                "job_description": job_description,
                "check_disabled_provider_fallback": check_fallback,
            }
        )

    minimums = benchmark.get("minimums", {})
    if len(resolved_cases) < int(minimums.get("cases", 1)):
        raise ValueError("Operational reliability benchmark has too few cases.")
    if len(sectors) < int(minimums.get("sectors", 1)):
        raise ValueError("Operational reliability benchmark covers too few sectors.")
    if fallback_cases < int(minimums.get("fallback_cases", 0)):
        raise ValueError("Operational reliability benchmark has too few fallback cases.")

    return {
        **benchmark,
        "cases": resolved_cases,
    }


@contextmanager
def _provider_forced_off() -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in _PROVIDER_ENVIRONMENT_KEYS}
    try:
        os.environ["AI_ANALYSIS_ENABLED"] = "false"
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("OPENAI_MODEL", None)
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def evaluate_operational_reliability(
    benchmark: dict[str, Any] | None = None,
) -> dict[str, Any]:
    benchmark_data = benchmark or load_operational_reliability_benchmark()
    runs_per_case = int(benchmark_data["runs_per_case"])
    failures: list[dict[str, Any]] = []
    case_results: list[dict[str, Any]] = []

    stable_cases = 0
    invariant_runs = 0
    invariant_passes = 0
    fallback_cases = 0
    fallback_preserved = 0

    for case in benchmark_data["cases"]:
        case_failure_start = len(failures)
        fingerprints: list[str] = []
        latencies_ms: list[float] = []
        analyses: list[SmartFitAnalysisResponse] = []

        for run_index in range(1, runs_per_case + 1):
            started = perf_counter()
            analysis = analyze_smart_fit(
                resume_text=case["resume_text"],
                job_description=case["job_description"],
                use_model_assisted=False,
            )
            latencies_ms.append(round((perf_counter() - started) * 1000, 3))
            analyses.append(analysis)
            fingerprints.append(_fingerprint(_analysis_payload(analysis)))

            invariant_runs += 1
            invariant_failures = validate_analysis_invariants(
                analysis,
                case_id=case["id"],
                resume_text=case["resume_text"],
                job_description=case["job_description"],
                run=run_index,
            )
            if not invariant_failures:
                invariant_passes += 1
            failures.extend(invariant_failures)

            if (
                analysis.analysis_engine != "deterministic"
                or analysis.model_assisted_status != "not_requested"
                or analysis.coaching_engine != "deterministic"
                or analysis.coaching_status != "not_requested"
            ):
                failures.append(
                    _failure(
                        case_id=case["id"],
                        run=run_index,
                        check="deterministic_engine_metadata",
                        expected={
                            "analysis_engine": "deterministic",
                            "model_assisted_status": "not_requested",
                            "coaching_engine": "deterministic",
                            "coaching_status": "not_requested",
                        },
                        actual={
                            "analysis_engine": analysis.analysis_engine,
                            "model_assisted_status": analysis.model_assisted_status,
                            "coaching_engine": analysis.coaching_engine,
                            "coaching_status": analysis.coaching_status,
                        },
                    )
                )

        stable = len(set(fingerprints)) == 1
        stable_cases += int(stable)
        if not stable:
            failures.append(
                _failure(
                    case_id=case["id"],
                    check="repeated_run_instability",
                    expected=1,
                    actual=len(set(fingerprints)),
                )
            )

        fallback_result: dict[str, Any] | None = None
        if case["check_disabled_provider_fallback"]:
            fallback_cases += 1
            with _provider_forced_off():
                started = perf_counter()
                fallback_analysis = analyze_smart_fit(
                    resume_text=case["resume_text"],
                    job_description=case["job_description"],
                    use_model_assisted=True,
                )
                fallback_latency_ms = round((perf_counter() - started) * 1000, 3)

            invariant_runs += 1
            fallback_invariant_failures = validate_analysis_invariants(
                fallback_analysis,
                case_id=case["id"],
                resume_text=case["resume_text"],
                job_description=case["job_description"],
                run=0,
            )
            if not fallback_invariant_failures:
                invariant_passes += 1
            failures.extend(fallback_invariant_failures)

            preservation_match = _fingerprint(
                _fallback_preservation_payload(fallback_analysis)
            ) == _fingerprint(_fallback_preservation_payload(analyses[0]))
            fallback_preserved += int(preservation_match)

            if not preservation_match:
                failures.append(
                    _failure(
                        case_id=case["id"],
                        check="disabled_provider_changed_deterministic_output",
                        expected=True,
                        actual=False,
                    )
                )
            if (
                fallback_analysis.analysis_engine != "deterministic"
                or fallback_analysis.coaching_engine != "deterministic"
                or not fallback_analysis.model_assisted_status.startswith("fallback_")
                or not fallback_analysis.coaching_status.startswith("fallback_")
            ):
                failures.append(
                    _failure(
                        case_id=case["id"],
                        check="disabled_provider_fallback_metadata",
                        expected="deterministic engines with fallback_* statuses",
                        actual={
                            "analysis_engine": fallback_analysis.analysis_engine,
                            "model_assisted_status": fallback_analysis.model_assisted_status,
                            "coaching_engine": fallback_analysis.coaching_engine,
                            "coaching_status": fallback_analysis.coaching_status,
                        },
                    )
                )

            fallback_result = {
                "preserved": preservation_match,
                "latency_ms": fallback_latency_ms,
                "analysis_status": fallback_analysis.model_assisted_status.split(":", 1)[0],
                "coaching_status": fallback_analysis.coaching_status.split(":", 1)[0],
            }

        mean_latency = round(mean(latencies_ms), 3)
        case_passed = len(failures) == case_failure_start
        case_results.append(
            {
                "id": case["id"],
                "sector": case["sector"],
                "passed": case_passed,
                "runs": runs_per_case,
                "stable": stable,
                "fingerprint": fingerprints[0],
                "latency_ms": {
                    "minimum": min(latencies_ms),
                    "mean": mean_latency,
                    "maximum": max(latencies_ms),
                },
                "fallback": fallback_result,
            }
        )

    case_passes = sum(int(case["passed"]) for case in case_results)
    maximum_mean_latency = max(
        case["latency_ms"]["mean"] for case in case_results
    )
    metrics = {
        "case_pass_rate": _ratio(case_passes, len(case_results)),
        "stable_run_rate": _ratio(stable_cases, len(case_results)),
        "invariant_pass_rate": _ratio(invariant_passes, invariant_runs),
        "fallback_preservation_rate": _ratio(fallback_preserved, fallback_cases),
        "maximum_mean_case_latency_ms": maximum_mean_latency,
    }

    thresholds = {
        key: float(value)
        for key, value in benchmark_data.get("thresholds", {}).items()
    }
    threshold_failures: dict[str, dict[str, float]] = {}
    for metric, required in thresholds.items():
        actual = float(metrics.get(metric, 0.0))
        if metric == "maximum_mean_case_latency_ms":
            failed = actual > required
        else:
            failed = actual < required
        if failed:
            threshold_failures[metric] = {
                "actual": actual,
                "required": required,
            }

    return {
        "benchmark_version": benchmark_data["version"],
        "passed": not failures and not threshold_failures,
        "counts": {
            "cases": len(case_results),
            "sectors": len({case["sector"] for case in case_results}),
            "runs_per_case": runs_per_case,
            "analysis_runs": invariant_runs,
            "fallback_cases": fallback_cases,
            "failures": len(failures),
        },
        "metrics": metrics,
        "thresholds": thresholds,
        "threshold_failures": threshold_failures,
        "failures": failures,
        "cases": case_results,
    }


def format_operational_reliability_report(report: dict[str, Any]) -> str:
    status = "PASS" if report["passed"] else "FAIL"
    metrics = report["metrics"]
    lines = [
        f"Operational reliability evaluation: {status}",
        (
            f"Cases: {report['counts']['cases']} across {report['counts']['sectors']} sectors; "
            f"{report['counts']['runs_per_case']} repeated runs per case"
        ),
        f"Case pass rate: {metrics['case_pass_rate']:.1%}",
        f"Repeated-run stability: {metrics['stable_run_rate']:.1%}",
        f"Invariant pass rate: {metrics['invariant_pass_rate']:.1%}",
        f"Disabled-provider preservation: {metrics['fallback_preservation_rate']:.1%}",
        f"Maximum mean deterministic latency: {metrics['maximum_mean_case_latency_ms']:.3f} ms",
    ]
    if report["failures"]:
        lines.append("Failures:")
        for failure in report["failures"][:10]:
            lines.append(
                f"- {failure['case_id']}: {failure['check']} (actual={failure['actual']!r})"
            )
    if report["threshold_failures"]:
        lines.append(f"Threshold failures: {report['threshold_failures']}")
    return "\n".join(lines)


__all__ = [
    "DEFAULT_OPERATIONAL_BENCHMARK_PATH",
    "evaluate_operational_reliability",
    "format_operational_reliability_report",
    "load_operational_reliability_benchmark",
    "validate_analysis_invariants",
]
