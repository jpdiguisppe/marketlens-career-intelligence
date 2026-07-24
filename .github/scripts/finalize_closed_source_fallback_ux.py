from pathlib import Path

path = Path("backend/app/job_search.py")
text = path.read_text()
old = "Searches Google for indexed Workday postings without scraping Workday search pages."
new = "MarketLens opens a Google search for indexed Workday postings without scraping Workday search pages."
if old not in text:
    raise RuntimeError("Could not find Workday fallback note")
path.write_text(text.replace(old, new, 1))
