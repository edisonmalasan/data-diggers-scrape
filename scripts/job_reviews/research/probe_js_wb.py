"""Check Wayback CDX for archived JobStreet PH company review pages (2026 + any)."""
import requests

H = {"User-Agent": "Mozilla/5.0 Chrome/126.0"}
CDX = "https://web.archive.org/cdx/search/cdx"

QUERIES = [
    ("jobstreet-companies-reviews-2026", {
        "url": "ph.jobstreet.com/companies/", "matchType": "prefix",
        "from": "20260101", "to": "20261008",
        "filter": ["statuscode:200", "original:.*\\/reviews.*"],
        "collapse": "urlkey", "limit": "200", "fl": "original,timestamp"}),
    ("jobstreet-companies-reviews-any", {
        "url": "ph.jobstreet.com/companies/", "matchType": "prefix",
        "filter": ["statuscode:200", "original:.*\\/reviews.*"],
        "collapse": "urlkey", "limit": "100", "fl": "original,timestamp"}),
    ("jobstreet-domain-2026-count", {
        "url": "ph.jobstreet.com", "matchType": "domain",
        "from": "20260101", "to": "20261008",
        "filter": ["statuscode:200"],
        "collapse": "urlkey", "limit": "50", "fl": "original,timestamp"}),
]

for name, params in QUERIES:
    try:
        r = requests.get(CDX, params=params, headers=H, timeout=120)
        lines = [l for l in r.text.splitlines() if l.strip()]
        print(f"== {name}: status={r.status_code} rows={len(lines)}")
        for l in lines[:15]:
            print("   ", l[:170])
    except Exception as e:
        print(f"== {name}: ERROR {e}")
