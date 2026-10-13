"""Probe round 4: pullpush.io (public Reddit archive) for r/phcareers /
r/buhaycorpo 2026 posts, + quick liveness checks of JobOx / Mynimo.

Why Reddit: the summative instructions explicitly allow non-job-board sources
("gather data from different sources (ex: social media, blogs, etc.)").
Reddit's own JSON API blocks this IP (403 / welcome-page), so we query
pullpush.io, a public read-only archive of Reddit content. Every staged row
keeps its canonical https://www.reddit.com/r/<sub>/comments/<id>/ source_url
for traceability.

Contract gates that must be satisfiable VERBATIM from post fields:
  - review_date: created_utc in 2026
  - company_name + job_title: explicit strings in title/selftext
  - location: explicit PH place mention (PH_RE gate, same as JobStreet)
  - text: selftext/title non-trivial
"""
from __future__ import annotations

import json
import re
import time

import requests

H = {"User-Agent": "data-mining-student-research/1.0 (summative activity)"}
PP = "https://api.pullpush.io/reddit/search/submission/"

for sub in ("phcareers", "buhaycorpo"):
    try:
        r = requests.get(PP, params={"subreddit": sub, "size": 5,
                                     "sort": "desc", "sort_type": "created_utc"},
                         headers=H, timeout=60)
        print(f"pullpush r/{sub} -> {r.status_code} len={len(r.text)}")
        if r.ok:
            d = r.json()
            posts = d.get("data", [])
            print(f"  posts={len(posts)}")
            for p in posts[:3]:
                t = time.strftime("%Y-%m-%d", time.gmtime(p.get("created_utc", 0)))
                print(f"    [{t}] {p.get('title', '')[:80]}")
    except Exception as e:  # noqa: BLE001
        print(f"pullpush r/{sub} ERR {e!r:.150}")
    time.sleep(2)

# 2026 window probe: after/before epoch for 2026-01-01 .. 2026-10-09
AFTER = int(time.mktime(time.strptime("2026-01-01", "%Y-%m-%d")))
BEFORE = int(time.mktime(time.strptime("2026-10-10", "%Y-%m-%d")))
print(f"\n2026 window: after={AFTER} before={BEFORE}")
for sub in ("phcareers", "buhaycorpo"):
    try:
        r = requests.get(PP, params={"subreddit": sub, "size": 100,
                                     "after": AFTER, "before": BEFORE,
                                     "sort": "desc", "sort_type": "created_utc"},
                         headers=H, timeout=90)
        print(f"pullpush 2026 r/{sub} -> {r.status_code}")
        if r.ok:
            posts = r.json().get("data", [])
            print(f"  2026 posts returned: {len(posts)}")
            if posts:
                yrs = {}
                for p in posts:
                    y = time.gmtime(p.get("created_utc", 0)).tm_year
                    yrs[y] = yrs.get(y, 0) + 1
                print(f"  year mix: {yrs}")
    except Exception as e:  # noqa: BLE001
        print(f"pullpush 2026 r/{sub} ERR {e!r:.150}")
    time.sleep(2)

print("\n=== quick checks ===")
for u in ["https://www.jobox.ph/robots.txt", "https://mynimo.com/robots.txt"]:
    try:
        r = requests.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=25)
        print(f"{u} -> {r.status_code}: {r.text[:250]!r}")
    except Exception as e:  # noqa: BLE001
        print(f"{u} ERR {e!r:.100}")
print("DONE")
