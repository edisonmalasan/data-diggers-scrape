"""Probe round 6: Arctic Shift public Reddit archive API (arctic-shift) for
r/phcareers / r/buhaycorpo 2026 submission volume.

Why: reddit.com JSON blocks this IP and pullpush.io rate-limits it; Arctic
Shift (arctic-shift.photon-reddit.com) is the community-run Pushshift
successor with a public read-only API. If reachable, it removes the Wayback
capture-sparsity bottleneck for the Reddit source.

This probe only counts and samples — no staging.
"""
from __future__ import annotations

import time

import requests

H = {"User-Agent": "data-mining-student-research/1.0 (summative activity)"}
BASE = "https://arctic-shift.photon-reddit.com/api/posts/search"

# 2026-01-01 .. 2026-10-09 in unix seconds
AFTER = 1767196800   # 2026-01-01 UTC
BEFORE = 1791561600  # 2026-10-10 UTC

for sub in ("phcareers", "buhaycorpo"):
    try:
        r = requests.get(BASE, params={
            "subreddit": sub, "after": AFTER, "before": BEFORE,
            "limit": 5, "sort": "desc", "order": "desc",
        }, headers=H, timeout=60)
        print(f"arctic r/{sub} -> {r.status_code} len={len(r.text)}")
        if r.ok:
            d = r.json()
            posts = d.get("data", [])
            print(f"  sample posts: {len(posts)}")
            for p in posts[:3]:
                print(f"    [{p.get('created_utc')}] {str(p.get('title'))[:80]}")
            # metadata count if provided
            meta = {k: v for k, v in d.items() if k != "data"}
            print(f"  meta: {meta}")
    except Exception as e:  # noqa: BLE001
        print(f"arctic r/{sub} ERR {e!r:.150}")
    time.sleep(2)

# rough volume: fetch with limit=100 and check 'next' pagination token
try:
    r = requests.get(BASE, params={"subreddit": "phcareers", "after": AFTER,
                                   "before": BEFORE, "limit": 100},
                     headers=H, timeout=90)
    if r.ok:
        d = r.json()
        print(f"\nphcareers 2026 page1: {len(d.get('data', []))} posts, "
              f"next={d.get('next')}")
except Exception as e:  # noqa: BLE001
    print(f"phcareers page1 ERR {e!r:.150}")
print("DONE")
