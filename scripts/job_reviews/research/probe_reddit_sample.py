"""Sample r/phcareers + r/buhaycorpo 2026 posts to design extraction gates.

Prints title / selftext-head / length for ~60 recent posts so we can see
how often company, job title, and PH location appear VERBATIM (contract
rule 6/8: no fabrication — fields must exist in the post text).
Slow pacing (6s) because Arctic Shift returns 422 'Timeout' when rushed.
"""
from __future__ import annotations

import time

import requests

H = {"User-Agent": "data-mining-student-research/1.0 (summative activity)"}
B = "https://arctic-shift.photon-reddit.com/api/posts/search"
AFTER = 1767196800
BEFORE = 1791561600

posts: list[dict] = []
for sub in ("phcareers", "buhaycorpo"):
    before = None
    got = 0
    while got < 60:
        params = {"subreddit": sub, "after": AFTER, "limit": 25,
                  "sort": "desc"}
        if before:
            params["before"] = before
        for attempt in range(5):
            try:
                r = requests.get(B, params=params, headers=H, timeout=90)
                if r.status_code == 200:
                    batch = r.json().get("data", [])
                    break
                print(f"  http {r.status_code}, backing off")
                time.sleep(20 * (attempt + 1))
            except Exception as e:  # noqa: BLE001
                print(f"  err {e!r:.100}, backing off")
                time.sleep(20 * (attempt + 1))
        else:
            batch = []
        if not batch:
            break
        posts.extend(batch)
        got += len(batch)
        oldest = min(p["created_utc"] for p in batch)
        yr = time.gmtime(oldest).tm_year
        print(f"  r/{sub} got={got} oldest={time.strftime('%Y-%m-%d', time.gmtime(oldest))}")
        if yr < 2026:
            break
        before = int(oldest)
        time.sleep(6)
    time.sleep(4)

print(f"\n=== {len(posts)} posts ===")
for p in posts[:60]:
    d = time.strftime("%Y-%m-%d", time.gmtime(p["created_utc"]))
    title = (p.get("title") or "").replace("\n", " ")[:110]
    body = (p.get("selftext") or "").replace("\n", " ")[:180]
    flair = p.get("link_text") or p.get("flair") or ""
    print(f"[{d}] r/{p.get('subreddit')} | {title}")
    if body:
        print(f"    {body}")
print("DONE")
