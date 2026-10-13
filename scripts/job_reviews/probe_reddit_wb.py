"""Probe round 5: Wayback 2026 capture inventory for the two remaining
candidate sources — Glints PH company reviews, and Reddit PH-work threads.

Sources already ruled out (probe_sources*.py + .storage/EXTRA_SOURCE_REPORT.md):
Indeed (0 kept), AmbitionBox (India-only), CareerBliss (403), Kununu (no PH),
Kalibrr (no reviews), GoWork.ph (robots Disallow: / + 0 Wayback 2026 captures),
Prosple/Foundit/Bossjob (403/robots), pullpush.io (429/connection-reset).

This script only COUNTS captures so we can size the yield before writing a
real scraper.
"""
from __future__ import annotations

import time

import requests

H = {"User-Agent": "Mozilla/5.0 Chrome/126.0"}
CDX = "https://web.archive.org/cdx/search/cdx"


def cdx(url: str, matchType: str = "prefix", frm: str = "20260101",
        to: str = "20261009", limit: int = 50000,
        extra: dict | None = None) -> list[tuple[str, str]]:
    params = {"url": url, "matchType": matchType, "from": frm, "to": to,
              "filter": "statuscode:200", "collapse": "urlkey",
              "fl": "original,timestamp", "limit": str(limit)}
    if extra:
        params.update(extra)
    for attempt in range(4):
        try:
            r = requests.get(CDX, params=params, headers=H, timeout=240)
            if r.status_code != 200:
                raise RuntimeError(f"status {r.status_code}")
            out = []
            for line in r.text.splitlines():
                parts = line.split(None, 1)
                if len(parts) == 2:
                    out.append((parts[0], parts[1]))
            return out
        except Exception as e:  # noqa: BLE001
            print(f"    cdx attempt {attempt}: {e!r:.110}")
            time.sleep(10)
    return []


print("=== A. Glints PH review-ish captures (2026) ===")
for prefix in ["glints.com/ph/", "www.glints.com/ph/"]:
    rows = cdx(prefix)
    rev = [(o, t) for o, t in rows if "review" in o.lower()
           or "/companies/" in o.lower() or "/employer" in o.lower()]
    print(f"  {prefix}: total={len(rows)} reviewish={len(rev)}")
    for o, t in sorted(rev, key=lambda x: x[1], reverse=True)[:10]:
        print(f"    {t} {o[:120]}")
    time.sleep(3)

print("\n=== B. Reddit PH-work thread captures (2026) ===")
total_threads: set[str] = set()
for host in ("old.reddit.com", "www.reddit.com"):
    for sub in ("phcareers", "buhaycorpo"):
        rows = cdx(f"{host}/r/{sub}/comments/")
        ids = {o.split("/comments/")[1].split("/")[0]
               for o, _ in rows if "/comments/" in o}
        total_threads |= ids
        print(f"  {host}/r/{sub}/comments/: captures={len(rows)} unique_threads={len(ids)}")
        time.sleep(3)

print(f"\n  => unique 2026-archived threads across hosts/subs: {len(total_threads)}")

# sample: fetch one old.reddit thread snapshot, confirm post fields parseable
if total_threads:
    sample_id = sorted(total_threads)[0]
    rows = cdx(f"old.reddit.com/r/phcareers/comments/{sample_id}",
               matchType="prefix", limit=5)
    if not rows:
        rows = cdx(f"www.reddit.com/r/phcareers/comments/{sample_id}",
                   matchType="prefix", limit=5)
    if rows:
        o, t = rows[0]
        snap = f"https://web.archive.org/web/{t}id_/{o}"
        rr = requests.get(snap, headers=H, timeout=90)
        print(f"\n  sample snapshot {snap} -> {rr.status_code} len={len(rr.text)}")
        for marker in ["<title>", "submitted", "datetime=", "selftext",
                       "data-author", "thing"]:
            print(f"    {marker!r}: {rr.text.count(marker)}")
print("\nDONE")
