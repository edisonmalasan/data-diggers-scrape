"""CDX discovery: Glassdoor review pages OUTSIDE www.glassdoor.com/Reviews/.

Queries (gentle: 2-3s spacing, 3 retries):
  A) domain=glassdoor.com (all subdomains) review-ish URLs, 2026
  B) glassdoor.com.ph explicit
  C) urlkey regex: manila/makati/cebu/philippin
  D) urlkey regex: filter.city / locId location-filtered pages
Saves NEW (not already in glassdoor_urls.json) URLs -> .storage/glassdoor_extra_urls.json
"""
import json
import time
from pathlib import Path

import requests

H = {"User-Agent": "Mozilla/5.0 Chrome/126.0"}
CDX = "https://web.archive.org/cdx/search/cdx"
HERE = Path(__file__).resolve().parents[1]
STORAGE = HERE / ".storage"

BASE = {
    "from": "20260101", "to": "20261008",
    "filter": ["statuscode:200"],
    "collapse": "urlkey", "fl": "original,timestamp",
    "limit": "50000",
}


def q(label, params, sleep=2.5):
    for attempt in range(4):
        try:
            r = requests.get(CDX, params=params, headers=H, timeout=180)
            if r.status_code != 200:
                raise RuntimeError(f"status {r.status_code}")
            rows = [l.split(None, 1) for l in r.text.splitlines() if l.strip()]
            print(f"[{label}] {len(rows)} rows")
            time.sleep(sleep)
            return rows
        except Exception as e:  # noqa: BLE001
            print(f"[{label}] attempt {attempt}: {e}")
            time.sleep(8 * (attempt + 1))
    return []


known = {r["url"] for r in json.loads(
    (STORAGE / "glassdoor_urls.json").read_text(encoding="utf-8"))}
print(f"known urls: {len(known)}")

found: dict[str, str] = {}

def keep(rows, tag):
    new = 0
    for orig, ts in rows:
        if orig not in known and (orig not in found or ts > found[orig]):
            found[orig] = ts
            new += 1
    print(f"  -> new: {new} (running total {len(found)})")


# A) all subdomains, review-ish urlkeys
rows = q("A domain=glassdoor.com review-ish",
         {**BASE, "url": "glassdoor.com", "matchType": "domain",
          "filter": ["statuscode:200", "urlkey:.*review.*"]})
keep(rows, "A")

# B) glassdoor.com.ph
rows = q("B glassdoor.com.ph",
         {**BASE, "url": "glassdoor.com.ph", "matchType": "domain"})
keep(rows, "B")

# C) PH city/country tokens anywhere under glassdoor.com
rows = q("C PH tokens",
         {**BASE, "url": "glassdoor.com", "matchType": "domain",
          "filter": ["statuscode:200",
                     "urlkey:.*(manila|makati|cebu|quezon|davao|philippin|"
                     "pampanga|taguig|pasig).*"]})
keep(rows, "C")

# D) location-filtered company review pages
rows = q("D filter.city / locId",
         {**BASE, "url": "glassdoor.com", "matchType": "domain",
          "filter": ["statuscode:200",
                     "urlkey:.*(filter\\.city|locid|locid=|il\\.[0-9]).*"]})
keep(rows, "D")

(STORAGE / "glassdoor_extra_urls.json").write_text(
    json.dumps([{"url": u, "ts": t} for u, t in sorted(found.items())], indent=0),
    encoding="utf-8")
print(f"SAVED {len(found)} -> glassdoor_extra_urls.json")
for u in list(found)[:40]:
    print("   ", u)
