"""Check Wayback CDX for archived PH job-review pages (read-only)."""
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36"}
BASE = "https://web.archive.org/cdx/search/cdx"

QUERIES = [
    ("indeed-cmp-anydate", {"url": "ph.indeed.com/cmp/", "matchType": "prefix",
                            "collapse": "urlkey", "limit": "15", "fl": "original,timestamp,statuscode"}),
    ("indeed-cmp-2026", {"url": "ph.indeed.com/cmp/", "matchType": "prefix",
                         "from": "2026", "to": "2026", "collapse": "urlkey",
                         "limit": "30", "fl": "original,timestamp,statuscode"}),
    ("glassdoor-rev-2026", {"url": "glassdoor.com/Reviews/", "matchType": "prefix",
                            "from": "2026", "to": "2026", "collapse": "urlkey",
                            "limit": "30", "fl": "original,timestamp,statuscode"}),
    ("indeed-ph-any", {"url": "ph.indeed.com", "matchType": "domain",
                       "from": "2026", "to": "2026", "collapse": "urlkey",
                       "limit": "40", "fl": "original,timestamp,statuscode"}),
]

for name, params in QUERIES:
    try:
        r = requests.get(BASE, params=params, headers=HEADERS, timeout=40)
        lines = [l for l in r.text.splitlines() if l.strip()]
        print(f"== {name}: status={r.status_code} rows={len(lines)}")
        for l in lines[:15]:
            print("   ", l)
    except Exception as e:
        print(f"== {name}: ERROR {e}")
