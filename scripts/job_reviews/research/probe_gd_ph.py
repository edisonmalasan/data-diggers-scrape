"""Step 3b: find 2026 Wayback Glassdoor snapshots for PH-relevant URLs."""
import requests

H = {"User-Agent": "Mozilla/5.0 Chrome/126.0"}
CDX = "https://web.archive.org/cdx/search/cdx"

QUERIES = [
    ("glassdoor-manila-2026", {
        "url": "www.glassdoor.com/Reviews/", "matchType": "prefix",
        "from": "20260101", "to": "20261008",
        "filter": ["statuscode:200", "original:.*Manila.*"],
        "collapse": "urlkey", "limit": "200", "fl": "original,timestamp"}),
    ("glassdoor-philippines-2026", {
        "url": "www.glassdoor.com/Reviews/", "matchType": "prefix",
        "from": "20260101", "to": "20261008",
        "filter": ["statuscode:200", "original:.*(?i)philippines.*"],
        "collapse": "urlkey", "limit": "200", "fl": "original,timestamp"}),
    ("glassdoor-accenture-2026", {
        "url": "www.glassdoor.com/Reviews/Accenture", "matchType": "prefix",
        "from": "20260101", "to": "20261008",
        "filter": ["statuscode:200"],
        "collapse": "urlkey", "limit": "60", "fl": "original,timestamp"}),
    ("glassdoor-IM995-2026", {
        "url": "www.glassdoor.com/Reviews/", "matchType": "prefix",
        "from": "20260101", "to": "20261008",
        "filter": ["statuscode:200", "original:.*IM995.*"],
        "collapse": "urlkey", "limit": "200", "fl": "original,timestamp"}),
]

for name, params in QUERIES:
    try:
        r = requests.get(CDX, params=params, headers=H, timeout=120)
        lines = [l for l in r.text.splitlines() if l.strip()]
        print(f"== {name}: status={r.status_code} rows={len(lines)}")
        for l in lines[:12]:
            print("   ", l[:160])
    except Exception as e:
        print(f"== {name}: ERROR {e}")
