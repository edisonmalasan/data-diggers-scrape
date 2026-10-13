"""Inspect raw submissionDate / jobTitle / country / location values in saved
Indeed dumps to characterize the PH x CS/IT x 2026 intersection. Local-only.
"""
import json
import re
from collections import Counter
from pathlib import Path

DUMP = Path(r"C:\Users\Edison\AppData\Local\Temp\opencode")
SNAPS = ["indep_iqor_list.html", "indep_keyence_list.html",
         "indep_yellowbrick_perma1.html", "indep_coherent_list.html",
         "indep_grandapex_list.html"]

sys_path = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(sys_path))
from scrape_indeed_wb import extract_items  # noqa: E402

years = Counter()
countries = Counter()
locs = Counter()
titles = []
for fname in SNAPS:
    f = DUMP / fname
    if not f.exists():
        continue
    items = extract_items(f.read_text(encoding="utf-8"))
    if not items:
        continue
    for it in items:
        d = (it.get("submissionDate") or "?")
        yr = re.search(r"(\d{4})", d)
        years[yr.group(1) if yr else "?"] += 1
        countries[it.get("country") or "?"] += 1
        locs[(it.get("location") or "?")[:22]] += 1
        titles.append(it.get("jobTitle") or "?")

print("submissionDate year distribution:", dict(years.most_common()))
print("country distribution:", dict(countries.most_common()))
print("\nmost common locations:")
for loc, n in locs.most_common(15):
    print(f"  {n:3}  {loc!r}")
print("\nmost common job titles:")
for t, n in Counter(titles).most_common(15):
    print(f"  {n:3}  {t!r}")
