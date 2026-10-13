"""Probe candidate sources for PH CS/IT employee reviews (read-only, no scraping).

Prints HTTP status + signals per URL so we can pick sources that permit
automated access (DATA_CONTRACT rule 9).
"""
import sys
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

URLS = [
    # Wayback CDX: 2026 snapshots of Indeed PH company review pages
    ("wayback-cdx-indeed",
     "https://web.archive.org/cdx/search/cdx?url=ph.indeed.com/cmp/*&matchType=prefix"
     "&from=20260101&to=20261008&filter=statuscode:200&collapse=urlkey&limit=20&fl=original,timestamp"),
    # Wayback CDX: Glassdoor reviews
    ("wayback-cdx-glassdoor",
     "https://web.archive.org/cdx/search/cdx?url=glassdoor.com/Reviews/*&matchType=prefix"
     "&from=20260101&to=20261008&filter=statuscode:200&collapse=urlkey&limit=20&fl=original,timestamp"),
    # Live sites
    ("indeed-ph-live", "https://ph.indeed.com/cmp/Accenture/reviews"),
    ("ambitionbox", "https://www.ambitionbox.com/reviews/accenture-reviews"),
    ("careerbliss", "https://www.careerbliss.com/company-reviews/accenture/"),
    ("jobstreet", "https://www.jobstreet.com.ph/"),
    ("greatplacetowork", "https://greatplacetowork.com.ph/"),
    ("comparably", "https://www.comparably.com/companies/accenture/reviews"),
    ("glassdoor-live", "https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138.htm"),
    ("reddit-json", "https://www.reddit.com/r/phcareers/search.json?q=company+review&restrict_sr=1&sort=new&limit=3"),
    ("trustpilot", "https://www.trustpilot.com/review/www.accenture.com"),
    ("wayback-indeed-snapshot", "https://web.archive.org/web/2026/https://ph.indeed.com/cmp/Accenture/reviews"),
]


def probe(name, url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=25, allow_redirects=True)
        body = r.text[:4000].lower()
        title = ""
        if "<title" in body:
            i = body.find("<title")
            j = body.find("</title>", i)
            if j > i:
                title = r.text[i:j].split(">", 1)[-1][:80]
        flags = [k for k in ("captcha", "just a moment", "access denied", "unusual traffic",
                             "datadome", "are you a robot", "sign in") if k in body]
        print(f"[{name}] status={r.status_code} len={len(r.text)} url={r.url[:110]}")
        if title:
            print(f"    title={title!r}")
        if flags:
            print(f"    flags={flags}")
    except Exception as e:
        print(f"[{name}] ERROR {type(e).__name__}: {e}")


if __name__ == "__main__":
    for n, u in URLS:
        probe(n, u)
    sys.exit(0)
