"""Probe candidate non-JobStreet review sites for 2026 Wayback captures.

For each candidate review path: count 2026 captures via CDX, then fetch a
sample snapshot and report which contract-relevant fields are present
(date, pros/cons, location, job title).
"""
import re
import time

import requests

H = {"User-Agent": "Mozilla/5.0 Chrome/126.0"}
CDX = "https://web.archive.org/cdx/search/cdx"

CANDIDATES = [
    ("indeed-ph", "ph.indeed.com/cmp/"),
    ("indeed-www", "www.indeed.com/cmp/"),
    ("indeed-phil", "www.indeed.ph/cmp/"),
    ("ambitionbox", "www.ambitionbox.com/reviews/"),
    ("careerbliss", "www.careerbliss.com/reviews/"),
    ("kununu", "www.kununu.com/"),
    ("comparably", "www.comparably.com/companies/"),
    ("recruitmentguru", "recruitmentguru.ph/"),  # long-shot
]

REVIEW_HINT = re.compile(r"review", re.I)


def cdx(prefix: str) -> list[list[str]]:
    params = {
        "url": prefix, "matchType": "prefix",
        "from": "20260101", "to": "20261008",
        "filter": "statuscode:200", "collapse": "urlkey",
        "fl": "original,timestamp", "limit": "50000",
    }
    for attempt in range(3):
        try:
            r = requests.get(CDX, params=params, headers=H, timeout=180)
            if r.status_code != 200:
                raise RuntimeError(f"status {r.status_code}")
            return [l.split(None, 1) for l in r.text.splitlines() if l.strip()]
        except Exception as e:  # noqa: BLE001
            print(f"    cdx attempt {attempt}: {e}")
            time.sleep(6)
    return []


def probe_html(url: str) -> dict:
    """Fetch a snapshot; report which review fields are detectable."""
    for attempt in range(3):
        try:
            r = requests.get(url, headers=H, timeout=90)
            if r.status_code != 200:
                return {"status": r.status_code}
            t = r.text
            return {
                "status": 200,
                "len": len(t),
                "pros": len(re.findall(r"\bPros\b", t)),
                "cons": len(re.findall(r"\bCons\b", t)),
                "loc": len(re.findall(r"Location", t)),
                "full_date": len(re.findall(
                    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
                    r"\s+\d{1,2},\s+2026", t)),
                "my_date": len(re.findall(
                    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+2026", t)),
                "jobtitle": len(re.findall(r"Job Title|job-title|Designation", t)),
            }
        except Exception as e:  # noqa: BLE001
            print(f"    fetch attempt {attempt}: {e}")
            time.sleep(6)
    return {"status": "ERR"}


for name, prefix in CANDIDATES:
    print(f"\n=== {name} ({prefix}) ===")
    rows = cdx(prefix)
    rev = [(o, t) for o, t in rows if REVIEW_HINT.search(o)]
    print(f"  captures: {len(rows)} total, {len(rev)} review-ish")
    for o, t in sorted(rev, key=lambda x: x[1], reverse=True)[:3]:
        snap = f"https://web.archive.org/web/{t}id_/{o}"
        info = probe_html(snap)
        print(f"  {t} {o[:90]}")
        print(f"    -> {info}")
        time.sleep(1.5)
    time.sleep(1)
print("\nDONE")
