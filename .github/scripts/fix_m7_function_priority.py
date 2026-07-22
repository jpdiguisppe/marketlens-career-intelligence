from pathlib import Path


path = Path("backend/app/job_search.py")
text = path.read_text()

old_constants = '''FUNCTION_FIRST_ROLE_FAMILIES: tuple[RoleFamily, ...] = (
    "software",
    "data",
    "cybersecurity",
    "product",
    "marketing",
    "operations",
    "design",
)
'''
new_constants = '''CROSS_INDUSTRY_FUNCTION_QUERY_TERMS: dict[RoleFamily, set[str]] = {
    "software": ROLE_FAMILY_QUERY_TERMS["software"],
    "data": ROLE_FAMILY_QUERY_TERMS["data"],
    "cybersecurity": ROLE_FAMILY_QUERY_TERMS["cybersecurity"],
    "product": ROLE_FAMILY_QUERY_TERMS["product"],
    "marketing": ROLE_FAMILY_QUERY_TERMS["marketing"],
    "operations": ROLE_FAMILY_QUERY_TERMS["operations"],
    "design": ROLE_FAMILY_QUERY_TERMS["design"],
}
'''
if text.count(old_constants) != 1:
    raise RuntimeError(f"Expected one generated function-priority constant block, found {text.count(old_constants)}")
text = text.replace(old_constants, new_constants, 1)

old_functions = '''def _matching_role_families(query: str) -> list[RoleFamily]:
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
'''
new_functions = '''def _query_role_family(query: str) -> RoleFamily | None:
    normalized = query.lower()

    # First detect functions that can exist inside many industries. This keeps
    # "healthcare data analyst" in data and "financial services marketing" in
    # marketing while still allowing broad queries such as "finance internship"
    # or "healthcare jobs" to retain their existing role-family behavior.
    for family, terms in CROSS_INDUSTRY_FUNCTION_QUERY_TERMS.items():
        if _contains_any(normalized, terms):
            return family

    for family, terms in ROLE_FAMILY_QUERY_TERMS.items():
        if _contains_any(normalized, terms):
            return family
    return None
'''
if text.count(old_functions) != 1:
    raise RuntimeError(f"Expected one generated role-family function block, found {text.count(old_functions)}")
text = text.replace(old_functions, new_functions, 1)

path.write_text(text)
