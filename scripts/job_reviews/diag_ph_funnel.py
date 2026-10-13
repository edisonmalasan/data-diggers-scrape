"""Per-gate funnel for EVERY ph.indeed.com page already fetched (done3).

Answers: where exactly do the 124 ph items die (date/text/csit/country/
location), and is there ANY item passing date+csit?  Uses the cached latest
ts in .storage/indeed_wb_latest.json (one request per page, polite sleep).
Read-only: does not touch state files or staging.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
STORAGE = HERE / ".storage"

from scrape_indeed_wb import build_row, extract_items  # noqa: E402
from scrape_jobstreet import CS_IT_EXCLUDE, CS_IT_RE, is_ph_location  # noqa: E402
from scrape_indeed_wb2 import archive_get, polite  # noqa: E402

DONE = STORAGE / "indeed_wb_done3.json"
LATEST = STORAGE / "indeed_wb_latest.json"

GATES = ["date", "text", "csit", "country", "location", "meta"]


def main() -> int:
    done = json.loads(DONE.read_text(encoding="utf-8"))
    latest = json.loads(LATEST.read_text(encoding="utf-8"))
    ph_urls = sorted(u for u in done if "ph.indeed.com" in u)
    print(f"ph pages in done3: {len(ph_urls)}")

    fun: dict[str, int] = {g: 0 for g in GATES}
    fun["kept"] = 0
    date_pass: list[dict] = []      # items passing the date gate
    csit_pass: list[dict] = []      # items passing date+text+csit
    fetched = fail = 0

    for n, url in enumerate(ph_urls, 1):
        ts = latest.get(url)
        if not ts:
            print(f"[{n}] no cached ts (skip): {url[:90]}")
            continue
        snap = f"https://web.archive.org/web/{ts}id_/{url}"
        r = archive_get(snap, tries=3, timeout=120)
        if r is None or r.status_code != 200:
            fail += 1
            print(f"[{n}] FETCH {None if r is None else r.status_code}: {url[:90]}")
            continue
        fetched += 1
        items = extract_items(r.text)
        if not items:
            print(f"[{n}] items=0 :: {url[:90]}")
            polite()
            continue
        page_fun = {g: 0 for g in GATES}
        page_fun["kept"] = 0
        for raw in items:
            raw["host"] = "ph.indeed.com"
            before = dict(page_fun)

            def bump(gate: str) -> None:
                page_fun[gate] += 1

            # replicate build_row gate order via stats dict
            st = {k: 0 for k in ("items", "drop_date", "drop_text",
                                 "drop_csit", "drop_country",
                                 "drop_location", "drop_meta")}
            row = build_row(raw, "diag", "2026-01-01T00:00:00+00:00", st,
                            page_is_ph=True)
            if st["drop_date"]:
                bump("date")
            elif st["drop_text"]:
                bump("text")
            elif st["drop_csit"]:
                bump("csit")
                date_pass.append(raw)
            elif st["drop_country"]:
                bump("country")
                date_pass.append(raw)
                csit_pass.append(raw)
            elif st["drop_location"]:
                bump("location")
                date_pass.append(raw)
                csit_pass.append(raw)
            elif st["drop_meta"]:
                bump("meta")
                date_pass.append(raw)
                csit_pass.append(raw)
            else:
                bump("kept")
                page_fun["kept"] += 1
                date_pass.append(raw)
                csit_pass.append(raw)
        for g in (*GATES, "kept"):
            fun[g] += page_fun[g]
        if page_fun["date"] > 0 or page_fun["kept"] > 0:
            print(f"[{n}] {url[:95]}")
            print(f"      funnel={page_fun}")
        polite()

    print("\n===== ph.indeed.com aggregate funnel =====")
    print(fun)
    print(f"fetched={fetched} fetch_fail={fail}")
    print(f"\nitems passing date gate: {len(date_pass)}")
    for it in date_pass[:40]:
        print(f"  {it.get('submissionDate',''):<22} {it.get('job_title','')[:40]:<40} "
              f"country={it.get('country')!r} loc={it.get('location','')[:25]!r}")
    print(f"\nitems passing date+csit: {len(csit_pass)}")
    for it in csit_pass[:40]:
        print(f"  {it.get('submissionDate',''):<22} {it.get('job_title','')[:40]:<40} "
              f"country={it.get('country')!r} loc={it.get('location','')[:25]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
