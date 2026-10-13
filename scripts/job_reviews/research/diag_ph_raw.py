"""Dump raw payload structure of ph.indeed.com items + CDX gap checks.

1. Fetch 3 ph list pages (cached latest ts) and print full JSON of the
   first 3 items each — do ph items really lack jobTitle?
2. CDX: www.indeed.com fcountry=ph captures 2026 (previous probe 504'd).
3. CDX: full ph.indeed.com capture list vs inventory (what's missing?).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
STORAGE = HERE / ".storage"

from scrape_indeed_wb import CDX, extract_items  # noqa: E402
from scrape_indeed_wb2 import archive_get, polite  # noqa: E402

LATEST = STORAGE / "indeed_wb_latest.json"
INV = STORAGE / "indeed_wb_urls.json"

PAGES = [
    "https://ph.indeed.com/cmp/Keyence/reviews",
    "https://ph.indeed.com/cmp/Sison-Corillo-Parone-&-Co/reviews",
    "https://ph.indeed.com/cmp/Coherent-Corp.-1/reviews",
    "https://ph.indeed.com/cmp/Iqor/reviews/",
]


def dump_payloads() -> None:
    latest = json.loads(LATEST.read_text(encoding="utf-8"))
    for url in PAGES:
        ts = latest.get(url)
        print(f"\n===== {url} ts={ts} =====")
        if not ts:
            print("  no cached ts")
            continue
        r = archive_get(f"https://web.archive.org/web/{ts}id_/{url}",
                        tries=3, timeout=120)
        if r is None or r.status_code != 200:
            print(f"  fetch failed: {None if r is None else r.status_code}")
            continue
        items = extract_items(r.text)
        if not items:
            print(f"  items: {items!r}")
            polite()
            continue
        print(f"  {len(items)} items; keys of item[0]: {sorted(items[0])}")
        for it in items[:3]:
            print("  " + json.dumps(it, ensure_ascii=False)[:600])
        # jobTitle presence across all items
        jt = [bool((it.get('jobTitle') or '').strip()) for it in items]
        dates = [it.get('submissionDate', '') for it in items]
        print(f"  jobTitle non-empty: {sum(jt)}/{len(items)}")
        print(f"  dates: {dates}")
        polite()


def cdx_probes() -> None:
    inv = json.loads(INV.read_text(encoding="utf-8"))["items"]
    inv_ph = {i["url"] for i in inv if i["host"] == "ph.indeed.com"}

    # 2) www fcountry=ph (retry — previous probe hit 504s)
    for attempt_url, note in [
        ("www.indeed.com/cmp/", "www prefix"),
    ]:
        r = archive_get(CDX, {
            "url": attempt_url, "matchType": "prefix",
            "from": "20260101", "to": "20261009",
            "filter": ["statuscode:200", "original:.*fcountry=ph.*"],
            "collapse": "urlkey", "fl": "original,timestamp",
            "limit": "5000",
        }, tries=4, timeout=120)
        if r is not None and r.status_code == 200:
            lines = [l for l in r.text.splitlines() if l.strip()]
            print(f"\n[cdx] www fcountry=ph ({note}): {len(lines)}")
            for l in lines[:10]:
                print("   ", l[:150])
        else:
            print(f"\n[cdx] www fcountry=ph ({note}): FAIL "
                  f"{None if r is None else r.status_code}")
        polite()

    # 3) full ph.indeed.com capture list (no statuscode filter) vs inventory
    r = archive_get(CDX, {
        "url": "ph.indeed.com", "matchType": "domain",
        "from": "20260101", "to": "20261009",
        "filter": "original:.*reviews.*",
        "collapse": "urlkey", "fl": "original,timestamp,statuscode",
        "limit": "20000",
    }, tries=4, timeout=120)
    if r is not None and r.status_code == 200:
        rows = [l.split() for l in r.text.splitlines() if l.strip()]
        all_urls = {r0[0] for r0 in rows}
        missing = sorted(all_urls - inv_ph)
        print(f"\n[cdx] ph domain reviews captures: {len(rows)} rows, "
              f"{len(all_urls)} unique urls; NOT in inventory: {len(missing)}")
        for u in missing[:30]:
            print("   MISSING:", u[:150])
        non200 = [r0 for r0 in rows if len(r0) > 2 and r0[2] != "200"]
        print(f"   non-200 rows: {len(non200)}")
        for r0 in non200[:10]:
            print("   ", r0)
    else:
        print(f"\n[cdx] ph domain probe FAIL {None if r is None else r.status_code}")
    polite()


if __name__ == "__main__":
    dump_payloads()
    cdx_probes()
