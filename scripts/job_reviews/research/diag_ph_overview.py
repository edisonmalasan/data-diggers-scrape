"""Probe ph.indeed.com NON-review paths (company overview pages /cmp/<co>,
/overview, /salaries etc.) for embedded comp-initialData review payloads.
If overview pages carry reviewsList.items[], that's untapped PH inventory.
Read-only."""
from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
STORAGE = HERE / ".storage"

from scrape_indeed_wb import cdx_query, extract_items  # noqa: E402
from scrape_indeed_wb2 import archive_get, polite  # noqa: E402


def main() -> int:
    rows = cdx_query({"url": "ph.indeed.com/cmp/", "matchType": "prefix",
                      "filter": ["statuscode:200", "mimetype:text/html"],
                      "fl": "original,timestamp", "limit": "2000"})
    inv = json.loads((STORAGE / "indeed_wb_urls.json").read_text(encoding="utf-8"))["items"]
    inv_urls = set(e["url"] for e in inv)

    # non /reviews paths
    others = [(r[0], r[1]) for r in rows
              if "/reviews" not in r[0].lower()
              and not re.search(r"\.(js|css|png|svg|ico)", r[0], re.I)]
    print(f"ph non-review cmp captures: {len(others)}")
    # group by path (drop query), sample distinct companies
    by_path: dict[str, list] = {}
    for u, ts in others:
        by_path.setdefault(u.split("?")[0], []).append((u, ts))
    print(f"distinct paths: {len(by_path)}")
    for p in sorted(by_path)[:20]:
        print("   ", p[:120])

    random.Random(2).shuffle(others)
    print(f"\nprobing {min(12, len(others))} overview pages ...")
    for u, ts in others[:12]:
        r = archive_get(f"https://web.archive.org/web/{ts}id_/{u}",
                        tries=3, timeout=120)
        polite()
        if r is None or r.status_code != 200:
            print(f"   FAIL {None if r is None else r.status_code} :: {u[:100]}")
            continue
        items = extract_items(r.text)
        n = len(items) if items else 0
        sample = ""
        if items:
            it = items[0]
            sample = (f" | first: {(it.get('jobTitle') or '')[:30]!r} "
                      f"country={it.get('country')!r} "
                      f"date={(it.get('submissionDate') or '')[:20]!r}")
        print(f"   items={n}{sample} :: {u[:105]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
