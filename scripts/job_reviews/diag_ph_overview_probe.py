"""Probe ph.indeed.com company OVERVIEW captures (bare /cmp/<slug>, 23
distinct companies, never in the review inventory) for embedded
comp-initialData review payloads.  Run AFTER diag_www_passers finishes to
avoid doubling archive.org pressure. Read-only; logs to
.storage/diag_ph_overview.log.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
STORAGE = HERE / ".storage"

from scrape_indeed_wb import cdx_query, extract_items  # noqa: E402
from scrape_indeed_wb2 import archive_get, polite  # noqa: E402

OUT = STORAGE / "diag_ph_overview.log"


def log(msg: str) -> None:
    print(msg, flush=True)
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def main() -> int:
    rows = cdx_query({"url": "ph.indeed.com/cmp/", "matchType": "prefix",
                      "filter": ["statuscode:200", "mimetype:text/html"],
                      "fl": "original,timestamp", "limit": "2000"})
    bare = [(r[0], r[1]) for r in rows
            if "/reviews" not in r[0].lower()
            and re.fullmatch(r"https://ph\.indeed\.com/cmp/[^/?]+",
                             r[0].split("?")[0])]
    seen: set[str] = set()
    uniq = []
    for u, ts in sorted(bare, key=lambda x: x[1], reverse=True):
        p = u.split("?")[0]
        if p in seen:
            continue
        seen.add(p)
        uniq.append((u, ts))
    log(f"=== ph overview probe: {len(uniq)} distinct companies ===")
    n_items = 0
    for u, ts in uniq:
        r = archive_get(f"https://web.archive.org/web/{ts}id_/{u}",
                        tries=3, timeout=120)
        polite()
        if r is None or r.status_code != 200:
            log(f"FAIL {None if r is None else r.status_code} :: {u[:110]}")
            continue
        items = extract_items(r.text)
        k = len(items) if items else 0
        n_items += k
        extra = ""
        if items:
            dates = [it.get("submissionDate") or "" for it in items]
            extra = f" dates={dates[:5]}"
        log(f"items={k}{extra} :: {u[:110]}")
    log(f"total embedded items: {n_items}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
