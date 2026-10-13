"""Pattern classes inside glassdoor_urls.json: PH hits, jobTitle, locId, city filters."""
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

STORAGE = Path(__file__).resolve().parent / ".storage"
rows = json.loads((STORAGE / "glassdoor_urls.json").read_text(encoding="utf-8"))

PH_TOKEN = re.compile(r"manila|makati|cebu|davao|quezon|philippin|\bph\b|taguig|"
                      r"pasig|pampanga|ilocos|mindanao|visayas|luzon", re.I)
param_hits = Counter()
ph_urls = []
jobtitle_urls = []
named = Counter()
for r in rows:
    u = r["url"]
    sp = urlsplit(u)
    q = parse_qs(sp.query)
    for k in q:
        param_hits[k] += 1
    if PH_TOKEN.search(u):
        ph_urls.append(u)
    if "jobTitle" in q:
        jobtitle_urls.append((u, q.get("jobTitle")))
    m = re.search(r"/Reviews/([A-Za-z0-9%.\- ]+)-Reviews-E\d+", u)
    if m:
        named[m.group(1)] += 1

print(f"total={len(rows)}")
print(f"query params: {dict(param_hits)}")
print(f"PH-token URLs: {len(ph_urls)}")
for u in ph_urls[:15]:
    print("   ", u)
print(f"jobTitle URLs: {len(jobtitle_urls)}")
for u, jt in jobtitle_urls[:10]:
    print("   ", jt, u[:110])
print(f"named-company pages: {len(named)} (e.g. {named.most_common(10)})")
empty = sum(1 for r in rows if not re.search(r"-Reviews-E\d+", r["url"]))
print(f"no-E-ID URLs (rank4?): {empty}")
