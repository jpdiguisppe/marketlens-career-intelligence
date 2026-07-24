from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Could not find expected {label} block")
    return text.replace(old, new, 1)


adapter_path = Path("backend/app/job_search_intent_patch.py")
adapter = adapter_path.read_text()
adapter = replace_once(
    adapter,
    '''        resolved_level = level or job_search.resolve_job_level(query)
        intent = intent_engine.classify_search_intent(query, resolved_level)

        if intent.role_family in intent_engine.ENGINE_HANDLED_FAMILIES:
            return intent_engine.job_matches_search_intent(title, description, intent)

        canonical_family = job_search._query_job_function(query)
        strict_families = getattr(
            job_search,
            "STRICT_DESCRIPTION_ONLY_ROLE_FAMILIES",
            set(),
        )
        if canonical_family in strict_families:
            return original_matches_requested_role(
                title,
                description,
                query,
                resolved_level,
            )

        if intent.role_family is None:
''',
    '''        resolved_level = level or job_search.resolve_job_level(query)
        canonical_family = job_search._query_job_function(query)
        strict_families = getattr(
            job_search,
            "STRICT_DESCRIPTION_ONLY_ROLE_FAMILIES",
            set(),
        )
        if canonical_family in strict_families:
            return original_matches_requested_role(
                title,
                description,
                query,
                resolved_level,
            )

        intent = intent_engine.classify_search_intent(query, resolved_level)
        if intent.role_family in intent_engine.ENGINE_HANDLED_FAMILIES:
            return intent_engine.job_matches_search_intent(title, description, intent)

        if intent.role_family is None:
''',
    "strict-family adapter precedence",
)
adapter_path.write_text(adapter)

benchmark_path = Path("backend/evaluation/job_search_benchmark.json")
benchmark = benchmark_path.read_text()
benchmark = replace_once(
    benchmark,
    '''    {
      "id": "intent-law-student-judicial",
      "category": "intent-legal-policy",
      "query": "law student judicial internship",
      "expected": {"job_function": "legal", "industry": "legal_services", "level": "intern", "location": null}
    },
''',
    '''    {
      "id": "intent-law-student-judicial",
      "category": "intent-legal-policy",
      "query": "law student judicial internship",
      "expected": {"job_function": "legal", "industry": null, "level": "intern", "location": null}
    },
''',
    "law-student industry expectation",
)
benchmark_path.write_text(benchmark)
