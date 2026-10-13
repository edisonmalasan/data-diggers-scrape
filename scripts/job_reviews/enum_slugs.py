"""Enumerate JobStreet company slugs from Wayback CDX (all dates) + live directory."""
import json
import re
import time
from pathlib import Path

import requests

H = {"User-Agent": "Mozilla/5.0 Chrome/126.0"}
CDX = "https://web.archive.org/cdx/search/cdx"
OUT = Path(__file__).with_name(".storage")
OUT.mkdir(exist_ok=True)

slugs: dict[str, dict] = {}

# 1) Full CDX pull: ph.jobstreet.com/companies/ (any date, collapse dupes)
params = {
    "url": "ph.jobstreet.com/companies/", "matchType": "prefix",
    "filter": ["statuscode:200"],
    "collapse": "urlkey", "limit": "20000", "fl": "original,timestamp",
}
print("CDX pull...")
try:
    r = requests.get(CDX, params=params, headers=H, timeout=300)
    rows = [l.split() for l in r.text.splitlines() if l.strip()]
    print("rows:", len(rows))
    for orig, ts in rows:
        m = re.match(r"https?://ph\.jobstreet\.com/companies/([a-z0-9\-]+)/?", orig)
        if not m:
            continue
        slug = m.group(1)
        if slug in ("write-a-review",):
            continue
        has_rev = "/reviews" in orig
        prev = slugs.get(slug)
        if prev is None:
            slugs[slug] = {"slug": slug, "ts": ts, "reviews": has_rev}
        elif has_rev:
            prev["reviews"] = True
except Exception as e:
    print("CDX ERROR:", e)

print("slugs from CDX:", len(slugs), "| with /reviews snapshot:", sum(1 for v in slugs.values() if v["reviews"]))

# 2) Save
p = OUT / "jobstreet_slugs.json"
p.write_text(json.dumps(list(slugs.values()), indent=1), encoding="utf-8")
print("saved ->", p)
