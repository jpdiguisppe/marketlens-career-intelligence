from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
job_search = ROOT / "backend/app/job_search.py"

old = '''INTERN_TITLE_TERMS = INTERN_TERMS | {
    "fellow",
    "student program",
    "university program",
    "campus program",
}
'''
new = '''INTERN_TITLE_TERMS = INTERN_TERMS | {
    "summer analyst",
    "analyst intern",
    "summer intern",
    "summer internship",
    "student intern",
    "university intern",
    "internship program",
    "intern program",
    "fellow",
    "student program",
    "university program",
    "campus program",
}
'''

text = job_search.read_text()
if text.count(old) != 1:
    raise RuntimeError("Expected one internship-title block to update.")
job_search.write_text(text.replace(old, new, 1))

print("Restored explicit summer analyst and established internship title patterns.")
