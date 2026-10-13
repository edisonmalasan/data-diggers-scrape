"""Inspect the 2025-dated rows in the member file against the gates."""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from scrape_jobstreet import CS_IT_EXCLUDE, CS_IT_RE, is_ph_location  # noqa: E402

rows = list(csv.DictReader(open("data/job_reviews_2025_2026.csv", newline="",
                                encoding="utf-8")))
r25 = [r for r in rows if "2025" in (r.get("review_date") or "")]
print("2025-dated rows in member file:", len(r25))
for r in r25:
    text = (r.get("review_text") or "").strip() or (r.get("pros") or "").strip() \
        or (r.get("cons") or "").strip()
    csit = bool(CS_IT_RE.search(r["job_title"])) and \
        not bool(CS_IT_EXCLUDE.search(r["job_title"]))
    print("---")
    print(" company:", r["company_name"], "| title:", r["job_title"],
          "| date:", r["review_date"], "| loc:", r["location"] or "(empty)")
    print(" csit:", csit, "| ph:", is_ph_location(r["location"]),
          "| text:", bool(text))
