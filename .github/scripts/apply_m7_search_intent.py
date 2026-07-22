from pathlib import Path
import re


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"Expected exactly one {label} match, found {text.count(old)}")
    return text.replace(old, new, 1)


job_search_path = Path("backend/app/job_search.py")
main_path = Path("backend/app/main.py")
types_path = Path("frontend/src/types.ts")
tests_path = Path("backend/tests/test_job_search.py")

job_search = job_search_path.read_text()
main = main_path.read_text()
types = types_path.read_text()
tests = tests_path.read_text()

role_family_block = '''RoleFamily = Literal[
    "technology",
    "software",
    "finance",
    "data",
    "cybersecurity",
    "product",
    "marketing",
    "operations",
    "healthcare",
    "design",
]
'''
role_family_with_industry = role_family_block + '''Industry = Literal[
    "sports",
    "entertainment",
    "healthcare",
    "financial_services",
    "education",
    "nonprofit",
    "media",
]
'''
job_search = replace_once(job_search, role_family_block, role_family_with_industry, "role family block")

sports_pattern = re.compile(
    r'SPORTS_QUERY_TERMS = \{\n(?:    .*\n)+?\}\nSPORTS_TITLE_OR_COMPANY_TERMS = \{',
    re.MULTILINE,
)
industry_constants = '''INDUSTRY_QUERY_TERMS: dict[Industry, set[str]] = {
    "sports": {"sport", "sports", "athletic", "athletics", "esports", "e-sports"},
    "entertainment": {"entertainment", "film", "television", "tv", "music", "streaming", "gaming"},
    "healthcare": {"healthcare", "health care", "hospital", "medical", "clinical", "patient care"},
    "financial_services": {"finance", "financial services", "banking", "fintech", "insurance", "investment"},
    "education": {"education", "edtech", "university", "college", "school", "academic"},
    "nonprofit": {"nonprofit", "non-profit", "charity", "foundation", "social impact"},
    "media": {"media", "journalism", "publishing", "news", "broadcast", "broadcasting"},
}
FUNCTION_FIRST_ROLE_FAMILIES: tuple[RoleFamily, ...] = (
    "software",
    "data",
    "cybersecurity",
    "product",
    "marketing",
    "operations",
    "design",
)
SPORTS_QUERY_TERMS = INDUSTRY_QUERY_TERMS["sports"]
SPORTS_TITLE_OR_COMPANY_TERMS = {'''
job_search, count = sports_pattern.subn(industry_constants, job_search, count=1)
if count != 1:
    raise RuntimeError(f"Expected one sports query constants block, found {count}")

external_job_marker = '''@dataclass(frozen=True)
class ExternalJobResult:
'''
intent_dataclass = '''@dataclass(frozen=True)
class JobSearchIntent:
    query: str
    job_function: RoleFamily | None
    industry: Industry | None
    level: JobLevel
    location: str | None


'''
job_search = replace_once(
    job_search,
    external_job_marker,
    intent_dataclass + external_job_marker,
    "external job dataclass marker",
)

job_search = replace_once(
    job_search,
    '''    role_family: str | None = None
    source_coverage: list[SourceCoverageSummary] = field(default_factory=list)
''',
    '''    role_family: str | None = None
    industry: str | None = None
    source_coverage: list[SourceCoverageSummary] = field(default_factory=list)
''',
    "JobSearchResults metadata fields",
)

old_query_functions = '''def _query_role_family(query: str) -> RoleFamily | None:
    normalized = query.lower()
    for family, terms in ROLE_FAMILY_QUERY_TERMS.items():
        if _contains_any(normalized, terms):
            return family
    return None


def _query_industry(query: str) -> str | None:
    normalized = query.lower()
    if _contains_any(normalized, SPORTS_QUERY_TERMS):
        return "sports"
    return None
'''
new_query_functions = '''def _matching_role_families(query: str) -> list[RoleFamily]:
    normalized = query.lower()
    return [
        family
        for family, terms in ROLE_FAMILY_QUERY_TERMS.items()
        if _contains_any(normalized, terms)
    ]


def _query_role_family(query: str) -> RoleFamily | None:
    matches = _matching_role_families(query)
    if not matches:
        return None

    # When a query combines an industry with a cross-industry function, prefer
    # the function. Examples: healthcare marketing, finance data analyst, and
    # entertainment operations. A single-family query keeps existing behavior.
    for family in FUNCTION_FIRST_ROLE_FAMILIES:
        if family in matches:
            return family
    return matches[0]


def _query_industry(query: str) -> Industry | None:
    normalized = query.lower()
    for industry, terms in INDUSTRY_QUERY_TERMS.items():
        if _contains_any(normalized, terms):
            return industry
    return None


def parse_job_search_intent(
    query: str,
    location: str | None = None,
    level: str | None = None,
) -> JobSearchIntent:
    cleaned_query = query.strip()
    cleaned_location = location.strip() if location and location.strip() else None
    return JobSearchIntent(
        query=cleaned_query,
        job_function=_query_role_family(cleaned_query),
        industry=_query_industry(cleaned_query),
        level=resolve_job_level(cleaned_query, level),
        location=cleaned_location,
    )
'''
job_search = replace_once(job_search, old_query_functions, new_query_functions, "query intent functions")

old_search_start = '''    cleaned_query = query.strip()
    cleaned_location = location.strip() if location and location.strip() else None
    resolved_level = resolve_job_level(cleaned_query, level)
    role_family = _query_role_family(cleaned_query)
'''
new_search_start = '''    intent = parse_job_search_intent(query=query, location=location, level=level)
    cleaned_query = intent.query
    cleaned_location = intent.location
    resolved_level = intent.level
    role_family = intent.job_function
    industry = intent.industry
'''
job_search = replace_once(job_search, old_search_start, new_search_start, "search intent setup")

job_search = replace_once(
    job_search,
    '''        role_family=role_family,
        providers_searched=providers_searched,
''',
    '''        role_family=role_family,
        industry=industry,
        providers_searched=providers_searched,
''',
    "search result intent metadata",
)

main = replace_once(
    main,
    '''    role_family: str | None
    providers_searched: list[str]
''',
    '''    role_family: str | None
    industry: str | None
    providers_searched: list[str]
''',
    "API search response fields",
)
main = replace_once(
    main,
    '''        role_family=search_results.role_family,
        providers_searched=search_results.providers_searched,
''',
    '''        role_family=search_results.role_family,
        industry=search_results.industry,
        providers_searched=search_results.providers_searched,
''',
    "API search response mapping",
)

types = replace_once(
    types,
    '''  role_family: string | null;
  providers_searched: string[];
''',
    '''  role_family: string | null;
  industry: string | null;
  providers_searched: string[];
''',
    "frontend search response metadata",
)

tests = replace_once(
    tests,
    '''    _score_job,
    clean_job_description,
    resolve_job_level,
''',
    '''    _query_industry,
    _query_role_family,
    _score_job,
    clean_job_description,
    parse_job_search_intent,
    resolve_job_level,
''',
    "job search test imports",
)

intent_tests = '''\n\ndef test_search_intent_separates_job_function_from_industry() -> None:
    sports_marketing = parse_job_search_intent(
        "sports marketing internship",
        location=" Philadelphia ",
    )
    assert sports_marketing.job_function == "marketing"
    assert sports_marketing.industry == "sports"
    assert sports_marketing.level == "intern"
    assert sports_marketing.location == "Philadelphia"

    healthcare_data = parse_job_search_intent("healthcare data analyst")
    assert healthcare_data.job_function == "data"
    assert healthcare_data.industry == "healthcare"

    finance_marketing = parse_job_search_intent("financial services marketing")
    assert finance_marketing.job_function == "marketing"
    assert finance_marketing.industry == "financial_services"


def test_industry_taxonomy_detects_initial_milestone_seven_domains() -> None:
    assert _query_industry("entertainment partnerships") == "entertainment"
    assert _query_industry("university communications") == "education"
    assert _query_industry("nonprofit operations") == "nonprofit"
    assert _query_industry("news media analyst") == "media"
    assert _query_industry("backend software engineer") is None


def test_single_dimension_queries_keep_existing_role_family_behavior() -> None:
    assert _query_role_family("finance internship") == "finance"
    assert _query_role_family("healthcare jobs") == "healthcare"
    assert _query_role_family("software engineer") == "software"
'''
tests = replace_once(
    tests,
    '''\ndef test_intern_level_filters_to_internship_roles() -> None:
''',
    intent_tests + '''\n\ndef test_intern_level_filters_to_internship_roles() -> None:
''',
    "intent test insertion point",
)

job_search_path.write_text(job_search)
main_path.write_text(main)
types_path.write_text(types)
tests_path.write_text(tests)
