from pathlib import Path

path = Path("backend/app/job_search.py")
text = path.read_text()

old_import = "from app.external_urls import sanitize_external_https_url\nfrom app.job_source_registry import (\n"
new_import = "from app.external_urls import sanitize_external_https_url\nfrom app.legal_credentials import legal_credential_matches_search\nfrom app.job_source_registry import (\n"
assert old_import in text
text = text.replace(old_import, new_import, 1)

old_legal_titles = '''LEGAL_TITLE_TERMS = {
    "legal intern",
    "legal assistant",
    "legal analyst",
    "legal coordinator",
    "paralegal",
    "law clerk",
    "attorney",
    "counsel",
    "litigation",
}
'''
new_legal_titles = '''LEGAL_TITLE_TERMS = {
    "legal intern",
    "legal assistant",
    "legal analyst",
    "legal coordinator",
    "paralegal",
    "law clerk",
    "legal extern",
    "judicial intern",
    "judicial extern",
    "summer associate",
    "attorney",
    "associate attorney",
    "staff attorney",
    "lawyer",
    "counsel",
    "public defender",
    "prosecutor",
    "solicitor",
    "barrister",
    "litigation",
}
'''
assert old_legal_titles in text
text = text.replace(old_legal_titles, new_legal_titles, 1)

old_legal_query = '    "legal": {"legal", "law", "paralegal", "attorney", "counsel", "litigation", "law clerk"},\n'
new_legal_query = '''    "legal": {
        "legal",
        "law",
        "law student",
        "jd candidate",
        "j.d. candidate",
        "1l",
        "2l",
        "3l",
        "paralegal",
        "attorney",
        "lawyer",
        "counsel",
        "litigation",
        "law clerk",
        "legal extern",
        "judicial intern",
        "judicial internship",
        "judicial extern",
        "summer associate",
    },
'''
assert old_legal_query in text
text = text.replace(old_legal_query, new_legal_query, 1)

old_score_block = '''    family = (
        canonical_family
        if canonical_family in STRICT_DESCRIPTION_ONLY_ROLE_FAMILIES
        else legacy_family
    )
    industry = _query_industry(query)
'''
new_score_block = '''    family = (
        canonical_family
        if canonical_family in STRICT_DESCRIPTION_ONLY_ROLE_FAMILIES
        else legacy_family
    )
    if not legal_credential_matches_search(
        title=title,
        description=description,
        query=query,
        role_family=canonical_family,
        level=resolved_level,
    ):
        return 0
    industry = _query_industry(query)
'''
assert old_score_block in text
text = text.replace(old_score_block, new_score_block, 1)

path.write_text(text)
