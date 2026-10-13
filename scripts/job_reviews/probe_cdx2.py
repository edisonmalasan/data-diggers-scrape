"""Size the Wayback CDX index for 2026 Glassdoor review pages (paginated pull)."""
import requests

H = {"User-Agent": "Mozilla/5.0 Chrome/126.0"}
CDX = "https://web.archive.org/cdx/search/cdx"
BASE = {
    "url": "www.glassdoor.com/Reviews/", "matchType": "prefix",
    "from": "20260101", "to": "20261008",
    "filter": ["statuscode:200"],
}

# how many pages of results?
r = requests.get(CDX, params={**BASE, "showNumPages": "true"}, headers=H, timeout=180)
print("numPages:", repr(r.text[:200]), "status", r.status_code)

# sample first page with collapse
r2 = requests.get(CDX, params={**BASE, "collapse": "urlkey", "limit": "2000",
                               "fl": "original,timestamp", "page": "0"},
                  headers=H, timeout=180)
lines = [l for l in r2.text.splitlines() if l.strip()]
print("page0 rows:", len(lines), "status", r2.status_code)
for l in lines[:8]:
    print("   ", l[:150])
