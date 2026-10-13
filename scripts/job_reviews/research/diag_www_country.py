"""Decide whether www.indeed.com pages can EVER yield a kept row.

Scans a sample of www pages (PH-heavy employers + PH-floc pages, both
already-fetched and still-queued) and tallies, per item:
  country value x location x date-gate x csit-gate.
Also probes CDX for other PH Indeed domains (indeed.ph etc.).

Read-only; does not touch state/staging.
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
STORAGE = HERE / ".storage"

from scrape_indeed_wb import CDX, PH_FLOC_RE, extract_items  # noqa: E402
from scrape_indeed_wb2 import PH_HEAVY_RE, archive_get, polite  # noqa: E402
from scrape_jobstreet import CS_IT_EXCLUDE, CS_IT_RE  # noqa: E402
import scrape_indeed_wb as wb  # noqa: E402

LATEST = STORAGE / "indeed_wb_latest.json"
QUEUE = STORAGE / "indeed_wb_queue3.json"
DONE = STORAGE / "indeed_wb_done3.json"


def gates(raw: dict) -> tuple[bool, bool, str]:
    """Returns (date_ok, csit_ok, country_value)."""
    date_ok = bool(wb.DATE_OK_RE.match((raw.get("submissionDate") or "").strip()))
    jt = (raw.get("jobTitle") or "").strip()
    csit_ok = bool(CS_IT_RE.search(jt)) and not CS_IT_EXCLUDE.search(jt)
    c = raw.get("country")
    return date_ok, csit_ok, (c.strip() if isinstance(c, str) else repr(c))


def scan_pages(urls: list[str], note: str) -> None:
    latest = json.loads(LATEST.read_text(encoding="utf-8"))
    print(f"\n######## {note}: {len(urls)} pages ########")
    cc = collections.Counter()          # country value -> count (all items)
    cc_pass = collections.Counter()     # country for date+csit PASSERS
    ph_pass_rows = []
    for n, url in enumerate(urls, 1):
        ts = latest.get(url)
        if not ts:
            print(f"[{n}] no cached ts: {url[:100]}")
            continue
        r = archive_get(f"https://web.archive.org/web/{ts}id_/{url}",
                        tries=3, timeout=120)
        if r is None or r.status_code != 200:
            print(f"[{n}] FETCH FAIL {None if r is None else r.status_code}: {url[:100]}")
            continue
        items = extract_items(r.text) or []
        local = collections.Counter()
        for raw in items:
            date_ok, csit_ok, cv = gates(raw)
            cc[cv] += 1
            local[cv] += 1
            if date_ok and csit_ok:
                cc_pass[cv] += 1
                if cv.upper() == "PH" or (cv == "None" and False):
                    ph_pass_rows.append((url, raw))
                elif cv == "None":
                    ph_pass_rows.append((url, raw))   # missing country: candidate
        flag = "" if set(local) <= {"'US'"} else "  <-- NON-US PRESENT"
        print(f"[{n}] items={len(items)} countries={dict(local)}{flag} :: {url[:95]}")
        polite()
    print(f"\n[{note}] country tally (all items): {dict(cc)}")
    print(f"[{note}] country tally (date+csit passers): {dict(cc_pass)}")
    print(f"[{note}] PH-or-missing passers: {len(ph_pass_rows)}")
    for u, raw in ph_pass_rows[:10]:
        print("   CANDIDATE:", raw.get("jobTitle"), "|", raw.get("country"),
              "|", raw.get("location"), "|", u[:90])


def main() -> int:
    done = json.loads(DONE.read_text(encoding="utf-8"))
    q = json.loads(QUEUE.read_text(encoding="utf-8"))["items"]
    todo = [e["url"] for e in q if e["url"] not in done]

    # --- group remaining queue by tier
    by_tier: dict[int, list[str]] = collections.defaultdict(list)
    for e in q:
        if e["url"] not in done:
            by_tier[e["tier"]].append(e["url"])
    print("remaining queue tiers:",
          {t: len(v) for t, v in sorted(by_tier.items())})

    # 8 PH-floc pages (tier 4) — fetch ALL of them
    scan_pages(by_tier.get(4, []), "tier4 PH-floc www (queued)")

    # PH-heavy www pages still queued (tier 3 sample) + already fetched sample
    heavy_q = [u for u in by_tier.get(3, []) if PH_HEAVY_RE.search(u)][:6]
    scan_pages(heavy_q, "tier3 PH-heavy www queued sample")

    heavy_done = [u for u in done
                  if "www.indeed.com" in u and PH_HEAVY_RE.search(u)
                  and u.rstrip("/").endswith("reviews")][:6]
    scan_pages(heavy_done, "PH-heavy www list pages already fetched")

    # CS/IT fjobtitle www pages already fetched (source of the 111 drops)
    csit_done = [u for u in done if "www.indeed.com" in u
                 and re.search(r"fjobtitle=", u)][:6]
    scan_pages(csit_done, "csit-fjobtitle www already fetched")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
