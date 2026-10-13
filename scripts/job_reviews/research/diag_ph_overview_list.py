"""List distinct ph.indeed.com company OVERVIEW captures (bare /cmp/<slug>)
that are not in the review inventory — candidate untapped pages.
Offline (CDX only)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from scrape_indeed_wb import cdx_query  # noqa: E402

rows = cdx_query({"url": "ph.indeed.com/cmp/", "matchType": "prefix",
                  "filter": ["statuscode:200", "mimetype:text/html"],
                  "fl": "original,timestamp", "limit": "2000"})
others = [(r[0], r[1]) for r in rows if "/reviews" not in r[0].lower()]
bare = [(u, ts) for u, ts in others
        if re.fullmatch(r"https://ph\.indeed\.com/cmp/[^/?]+", u.split("?")[0])]
print("bare overview captures:", len(bare))
seen: set[str] = set()
uniq = []
for u, ts in sorted(bare, key=lambda x: x[1], reverse=True):
    p = u.split("?")[0]
    if p in seen:
        continue
    seen.add(p)
    uniq.append((u, ts))
print("distinct overview companies:", len(uniq))
for u, ts in uniq:
    print("  ", ts, u)
