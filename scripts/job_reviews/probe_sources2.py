"""Probe round 2: remaining candidate PH-review sources (live + Wayback CDX).

Checked and REJECTED earlier (see .storage/EXTRA_SOURCE_REPORT.md): Indeed,
AmbitionBox (India-only), CareerBliss (403), Kununu (no PH), Kalibrr (job
listings only, no reviews — re-confirmed in probe_kalibrr2.py), GoWork.ph live
(robots.txt Disallow: /), Prosple (403), Foundit (robots Disallow: /).

This round checks:
  1. gowork.ph via Wayback 2026 captures (public archive.org snapshot reads
     are the established precedent from scrape_indeed_wb.py rule-9 note)
  2. glints.com robots + PH review pages (Glints has employer reviews)
  3. joboid.com (PH job board with company reviews?)
  4. zaplay?/myjobstreet? — skip (same corpus as JobStreet)
  5. ambitionbox.com/reviews-with/philippines — double-check no PH filter
"""
from __future__ import annotations

import time

import requests

H = {"User-Agent": "Mozilla/5.0 Chrome/126.0"}
CDX = "https://web.archive.org/cdx/search/cdx"


def cdx(prefix: str, frm: str = "20260101", to: str = "20261009",
        limit: int = 5000) -> list[tuple[str, str]]:
    params = {"url": prefix, "matchType": "prefix", "from": frm, "to": to,
              "filter": "statuscode:200", "collapse": "urlkey",
              "fl": "original,timestamp", "limit": str(limit)}
    for attempt in range(4):
        try:
            r = requests.get(CDX, params=params, headers=H, timeout=180)
            if r.status_code != 200:
                raise RuntimeError(f"status {r.status_code}")
            out = []
            for line in r.text.splitlines():
                parts = line.split(None, 1)
                if len(parts) == 2:
                    out.append((parts[0], parts[1]))
            return out
        except Exception as e:  # noqa: BLE001
            print(f"    cdx attempt {attempt}: {e!r:.120}")
            time.sleep(8)
    return []


print("=== 1. gowork.ph Wayback 2026 captures (any path) ===")
rows = cdx("gowork.ph", limit=20000)
rev = [(o, t) for o, t in rows if "review" in o.lower()
       or "/company" in o.lower() or "/companies" in o.lower()]
print(f"  total captures={len(rows)} reviewish={len(rev)}")
for o, t in sorted(rev, key=lambda x: x[1], reverse=True)[:15]:
    print(f"  {t} {o[:120]}")
time.sleep(2)

print("\n=== 2. glints robots + live PH review probe ===")
for u in ["https://glbots.com/robots.txt", "https://www.glints.com/robots.txt",
          "https://glints.com/id-en/robots.txt"]:
    try:
        r = requests.get(u, headers=H, timeout=30)
        print(f"  {u} -> {r.status_code}: {r.text[:300]!r}")
    except Exception as e:  # noqa: BLE001
        print(f"  {u} ERR {e!r:.100}")
    time.sleep(1)

for u in ["https://glints.com/ph/en/companies",
          "https://glints.com/ph/en/companies/globe-telecom-361375662572904/reviews",
          "https://www.glints.com/ph/en/employer/"]:
    try:
        r = requests.get(u, headers=H, timeout=30, allow_redirects=True)
        print(f"  {u} -> {r.status_code} len={len(r.text)} final={r.url[:90]}")
    except Exception as e:  # noqa: BLE001
        print(f"  {u} ERR {e!r:.100}")
    time.sleep(1)

print("\n=== 3. joboid.com ===")
for u in ["https://www.joboid.com/robots.txt"]:
    try:
        r = requests.get(u, headers=H, timeout=30)
        print(f"  {u} -> {r.status_code}: {r.text[:400]!r}")
    except Exception as e:  # noqa: BLE001
        print(f"  {u} ERR {e!r:.100}")

print("\n=== 4. ambitionbox PH double-check (CDX 2026, philippines in url) ===")
rows = cdx("www.ambitionbox.com/reviews/", limit=20000)
ph = [(o, t) for o, t in rows if "philippin" in o.lower() or "/ph/" in o.lower()]
print(f"  ambitionbox 2026 review captures={len(rows)} ph-ish={len(ph)}")
for o, t in ph[:10]:
    print(f"  {t} {o[:120]}")

print("\nDONE")
