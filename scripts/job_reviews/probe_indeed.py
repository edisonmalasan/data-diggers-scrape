"""Targeted probe: Wayback 2026 captures of ph.indeed.com/cmp/<slug>/reviews.

Lists non-asset review URLs, fetches a few, and reports whether per-review
Location, 2026 dates, job title and pros/cons are present (incl. in embedded
JSON). Plain requests only, 1.5-3s delays, retries with backoff.
"""
import json
import re
import time

import requests

H = {"User-Agent": "Mozilla/5.0 Chrome/126.0"}
CDX = "https://web.archive.org/cdx/search/cdx"

params = {
    "url": "ph.indeed.com/cmp/", "matchType": "prefix",
    "from": "20260101", "to": "20261008",
    "filter": "statuscode:200", "collapse": "urlkey",
    "fl": "original,timestamp", "limit": "50000",
}
rows = []
for attempt in range(5):
    try:
        r = requests.get(CDX, params=params, headers=H, timeout=180)
        r.raise_for_status()
        rows = [l.split(None, 1) for l in r.text.splitlines() if l.strip()]
        break
    except Exception as e:  # noqa: BLE001
        print(f"cdx attempt {attempt}: {e}")
        time.sleep(8)

# real review pages: /cmp/<slug>/reviews  (no query strings, no assets)
pat = re.compile(r"^https?://ph\.indeed\.com/cmp/([^/?#]+)/reviews/?$")
review_pages = []
other = []
for o, t in rows:
    if "/s/assets/" in o or o.endswith((".css", ".js", ".svg", ".png", ".jpg", ".ico")):
        continue
    m = pat.match(o)
    if m:
        review_pages.append((o, t, m.group(1)))
    else:
        other.append(o)

print(f"total captures: {len(rows)}  review pages: {len(review_pages)}  other: {len(other)}")
for o in other[:25]:
    print("  other:", o[:120])

for o, t, slug in review_pages[:3]:
    snap = f"https://web.archive.org/web/{t}id_/{o}"
    print(f"\n--- {t} {o}")
    for attempt in range(4):
        try:
            r = requests.get(snap, headers=H, timeout=120)
            print("  status", r.status_code, "len", len(r.text))
            txt = r.text
            print("  markers:",
                  {k: len(re.findall(p, txt)) for k, p in {
                      "Pros": r"\bPros\b", "Cons": r"\bCons\b",
                      "Location": r"[Ll]ocation",
                      "Mon2026": r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+2026",
                      "MonYr2026": r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+2026",
                      "PHcity": r"Manila|Cebu City|Quezon City|Makati|Taguig|Davao",
                      "jobtitle": r"jobTitle|job_title|Job Title",
                      "INITIAL": r"__INITIAL|__NEXT_DATA__|indeed\.context|window\.",
                  }.items()})
            # show a snippet around the first "Pros"
            i = txt.find("Pros")
            if i != -1:
                print("  snippet:", re.sub(r"\s+", " ", txt[max(0, i - 600):i + 900])[:1500])
            break
        except Exception as e:  # noqa: BLE001
            print(f"  fetch attempt {attempt}: {e}")
            time.sleep(8)
    time.sleep(2.5)
print("\nDONE")
