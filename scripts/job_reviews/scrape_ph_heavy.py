"""Squeeze pass: process ALL 2026 Wayback captures of the remaining
PH-heavy MNC review pages (Accenture, Concentrix, Cognizant, TCS, IBM,
Samsung, Cardinal Health, iQor, VXI, EPAM, ...) found in the inventory.

Motivation: these are the only archived employer pages whose reviewer
corps plausibly includes the Philippines. Instruments a ph_any stat
(country == PH regardless of other gates) to quantify PH share.

Uses scrape_indeed_wb primitives (same gates, same politeness). Done keys
are "<url>@<ts>" and do not collide with the main run's "<url>" keys.
Run: python -u scripts/job_reviews/scrape_ph_heavy.py [--max-captures 6]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
STORAGE = HERE / ".storage"
DONE2_FILE = STORAGE / "indeed_wb_done2.json"
STATS2_FILE = STORAGE / "indeed_wb_stats2.json"

from scrape_indeed_wb import (  # noqa: E402
    CDX, build_row, extract_items, http_get, load_existing_ids, write_rows,
)

# Genuine PH-workforce MNCs (multi-national with big PH ops / BPO in PH).
PH_HEAVY = re.compile(
    r"accenture|concentrix|cognizant|tcs|tata-consultancy|ibm|samsung|"
    r"cardinal-health|iqor|vxi|epam|optum|unitedhealth|dxc|dxp|capgemini|"
    r"wipro|infosys|ntt|hitachi|fujitsu|canon|ricoh|emerson|schneider|"
    r"manulife|axa|sun-life|aia|insular|deloitte|pwc|kpmg|crowe|"
    r"alvarez|fti-consulting|bloomberg|sap|visa|docusign|okta|adobe|"
    r"salesforce|oracle|microsoft|amazon|intuit|teleperformance",
    re.I)

TARGETS = [
    "https://www.indeed.com/cmp/Accenture/reviews",
    "https://www.indeed.com/cmp/Accenture-2/reviews",
    "https://www.indeed.com/cmp/Concentrix/reviews",
    "https://www.indeed.com/cmp/Cognizant/reviews",
    "https://www.indeed.com/cmp/Iqor/reviews/",
    "https://www.indeed.com/cmp/Vxi-Global-Solutions/reviews",
]


def all_captures(url: str, cap: int) -> list[str]:
    """Newest-first list of 2026 capture timestamps for an exact URL."""
    r = http_get(CDX, {"url": url, "matchType": "exact",
                       "from": "20260101", "to": "20261009",
                       "filter": "statuscode:200", "fl": "timestamp"},
                 tries=5)
    if r is None or r.status_code != 200:
        return []
    ts = [l.strip() for l in r.text.splitlines() if l.strip()]
    time.sleep(2.5)
    return sorted(set(ts), reverse=True)[:cap]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=80)
    ap.add_argument("--max-captures", type=int, default=6)
    ap.add_argument("--sleep", type=float, default=2.5)
    args = ap.parse_args()

    inv = json.loads((STORAGE / "indeed_wb_urls.json").read_text(encoding="utf-8"))["items"]

    # PH-heavy plain pages from the inventory + hardcoded aliases
    urls: list[str] = list(TARGETS)
    for it in inv:
        u = it["url"]
        if "ph.indeed.com" in u:
            continue
        if not re.search(r"/reviews?/?(\?|$)", u.lower()):
            continue
        if PH_HEAVY.search(u) and u not in urls:
            urls.append(u)
    print(f"[targets] {len(urls)} PH-heavy review pages")

    done = set(json.loads(DONE2_FILE.read_text(encoding="utf-8"))) \
        if DONE2_FILE.exists() else set()
    seen_ids = load_existing_ids()
    stats = {"items": 0, "ph_any": 0, "y2026_any": 0, "drop_date": 0,
             "drop_text": 0, "drop_csit": 0, "drop_country": 0,
             "drop_location": 0, "drop_meta": 0, "kept": 0, "pages": 0,
             "fetch_fail": 0}
    consec_fail = 0
    new_rows: list[dict] = []
    try:
        for u in urls:
            if len(seen_ids) >= args.target:
                print(f"[run] target {args.target} reached -> stop")
                break
            for ts in all_captures(u, args.max_captures):
                if len(seen_ids) >= args.target:
                    break
                key = f"{u}@{ts}"
                if key in done:
                    continue
                snap = f"https://web.archive.org/web/{ts}id_/{u}"
                r = http_get(snap, tries=6, timeout=150)
                if r is None or r.status_code != 200:
                    stats["fetch_fail"] += 1
                    consec_fail += 1
                    print(f"  FETCH-FAIL {None if r is None else r.status_code} {ts} {u[:70]}")
                    if consec_fail >= 5:
                        print("[run] 5 consecutive failures -> stop (resumable)")
                        return 0
                    time.sleep(args.sleep)
                    continue
                consec_fail = 0
                items = extract_items(r.text)
                done.add(key)
                DONE2_FILE.write_text(json.dumps(sorted(done), indent=0),
                                      encoding="utf-8")
                if items is None:
                    stats["pages"] += 1
                    time.sleep(args.sleep)
                    continue
                page_rows = []
                now = datetime.now(timezone.utc).isoformat()
                for raw in items:
                    if raw.get("country") == "PH":
                        stats["ph_any"] += 1
                    if "2026" in (raw.get("submissionDate") or ""):
                        stats["y2026_any"] += 1
                    raw["host"] = ("ph.indeed.com" if "ph.indeed.com" in u
                                   else "www.indeed.com")
                    row = build_row(raw, snap, now, stats)
                    if row and row["review_id"] not in seen_ids:
                        seen_ids.add(row["review_id"])
                        page_rows.append(row)
                if page_rows:
                    write_rows(page_rows)
                    new_rows.extend(page_rows)
                    stats["kept"] += len(page_rows)
                stats["pages"] += 1
                print(f"  items={len(items)} kept+={len(page_rows)} "
                      f"total_new={len(new_rows)} :: {ts} {unquote(u)[:80]}")
                time.sleep(args.sleep)
    except KeyboardInterrupt:
        print("\n[interrupted] state saved")

    STATS2_FILE.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"[run] DONE pages={stats['pages']} items={stats['items']} "
          f"ph_any={stats['ph_any']} y2026_any={stats['y2026_any']} "
          f"new_rows={len(new_rows)} staged_total={len(load_existing_ids())}")
    print(f"[run] stats: {stats}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
