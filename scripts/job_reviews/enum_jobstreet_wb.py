"""Enumerate 2026 Wayback captures of JobStreet company review pages.

Captured pages freeze the 30 most-recent reviews at capture time, so a page
archived mid-2026 contains 2026-H1 reviews that have since scrolled off the
live page 1 -> unique rows for us. Also sanity-checks that the archived
capture actually contains rendered reviews (SSR) rather than an empty shell.
"""
import json
import sys
import time
from pathlib import Path

import requests

H = {"User-Agent": "Mozilla/5.0 Chrome/126.0"}
CDX = "https://web.archive.org/cdx/search/cdx"
OUT = Path(__file__).with_name(".storage") / "jobstreet_wb.json"

DOMAINS = ["ph.jobstreet.com", "jobstreet.com.ph"]
BASE = {
    "matchType": "prefix",
    "from": "20260101", "to": "20261008",
    "filter": ["statuscode:200"],
    "collapse": "urlkey", "fl": "original,timestamp",
}


def pull(domain: str) -> dict[str, str]:
    base = {**BASE, "url": f"{domain}/companies/"}
    cnt = {k: v for k, v in base.items() if k not in ("collapse", "fl")}
    npages = 1
    for attempt in range(4):
        try:
            r = requests.get(CDX, params={**cnt, "showNumPages": "true"},
                             headers=H, timeout=180)
            try:
                npages = int(r.text.strip() or 0)
            except ValueError:
                print(domain, "showNumPages ->", repr(r.text[:80]),
                      "falling back to 1 page")
            break
        except requests.RequestException as e:
            print(f"  showNumPages attempt {attempt}: {e}")
            time.sleep(5)
    print(f"{domain}: {npages} pages")
    seen: dict[str, str] = {}
    for pg in range(npages):
        for attempt in range(3):
            try:
                r = requests.get(CDX, params={**base, "page": str(pg)}, headers=H, timeout=180)
                if r.status_code != 200:
                    raise RuntimeError(f"status {r.status_code}")
                rows = [l.split(None, 1) for l in r.text.splitlines() if l.strip()]
                for orig, ts in rows:
                    if "/reviews" not in orig:
                        continue
                    if orig not in seen or ts > seen[orig]:
                        seen[orig] = ts
                print(f"  page {pg}/{npages}: +{len(rows)} rows -> {len(seen)} review urls")
                break
            except Exception as e:  # noqa: BLE001
                print(f"  page {pg} attempt {attempt}: {e}")
                time.sleep(4)
        time.sleep(0.4)
    return seen


all_urls: dict[str, str] = {}
for d in DOMAINS:
    try:
        all_urls.update(pull(d))
    except Exception as e:  # noqa: BLE001
        print(d, "PULL FAILED:", type(e).__name__, e)

# sanity check: do archived captures contain rendered reviews?
if all_urls:
    sample = sorted(all_urls.items(), key=lambda kv: kv[1], reverse=True)[:5]
    print("\nsanity check on newest 5 snapshots:")
    for url, ts in sample:
        try:
            r = requests.get(f"https://web.archive.org/web/{ts}id_/{url}",
                             headers=H, timeout=90)
            n = r.text.count("The good things")
            print(f"  {ts} {url[-70:]}: status={r.status_code} good-things-markers={n}")
        except Exception as e:  # noqa: BLE001
            print(f"  {ts}: ERROR {e}")

OUT.write_text(json.dumps(
    [{"url": u, "ts": t} for u, t in sorted(all_urls.items())], indent=0),
    encoding="utf-8")
print(f"\nSAVED {len(all_urls)} -> {OUT}")
sys.exit(0)
