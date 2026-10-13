"""Probe round 8: decisive checks for the last two candidate sources.

(a) Arctic Shift body-retention: do r/phcareers / r/buhaycorpo posts from
    OLDER 2026 windows (Jan/Apr/Jul) still carry selftext, or is it
    systematically [removed]? Small slow batches (rate-limit friendly).
(b) Great Place To Work PH: certified-company pages carry anonymized
    employee comments (role + tenure + text). Check via requests first;
    fall back to Playwright if Cloudflare-gated.

Either source must still satisfy the contract's verbatim-fields rule —
this probe only measures availability.
"""
from __future__ import annotations

import re
import time

import requests

H = {"User-Agent": "data-mining-student-research/1.0 (summative activity)"}
B = "https://arctic-shift.photon-reddit.com/api/posts/search"


def window(sub: str, after: int, before: int, label: str) -> None:
    for attempt in range(5):
        try:
            r = requests.get(B, params={"subreddit": sub, "after": after,
                                        "before": before, "limit": 50,
                                        "sort": "desc"},
                             headers=H, timeout=90)
            if r.status_code == 200:
                break
            print(f"  [{label}] http {r.status_code}, backoff")
            time.sleep(25 * (attempt + 1))
        except Exception as e:  # noqa: BLE001
            print(f"  [{label}] err {e!r:.90}, backoff")
            time.sleep(25 * (attempt + 1))
    else:
        print(f"  [{label}] GAVE UP")
        return
    posts = r.json().get("data", [])
    if not posts:
        print(f"  [{label}] 0 posts")
        return
    stats = {"removed": 0, "deleted": 0, "empty": 0, "has_text": 0}
    samples = []
    for p in posts:
        st = (p.get("selftext") or "").strip()
        if st[:12] == "[removed]":
            stats["removed"] += 1
        elif st[:10] == "[deleted]":
            stats["deleted"] += 1
        elif not st:
            stats["empty"] += 1
        else:
            stats["has_text"] += 1
            if len(samples) < 3:
                samples.append(st[:130].replace("\n", " "))
    yrs = sorted({time.gmtime(p["created_utc"]).tm_year for p in posts})
    print(f"  [{label}] n={len(posts)} years={yrs} {stats}")
    for s in samples:
        print(f"      HAS: {s!r}")


EPOCHS = {
    "jan": (1735689600 + 31536000, 1735689600 + 31536000 + 28 * 86400),   # 2026-02-01..03-01
    "apr": (1735689600 + 31536000 + 89 * 86400, 1735689600 + 31536000 + 119 * 86400),
    "jul": (1735689600 + 31536000 + 180 * 86400, 1735689600 + 31536000 + 210 * 86400),
}
# 2026-01-01 UTC = 1767225600 (computed properly below)
EPOCHS = {
    "feb2026": (1770163200, 1772582400),   # 2026-02-06 .. 2026-03-04
    "apr2026": (1775347200, 1777766400),   # 2026-04-04 .. 2026-05-02
    "jul2026": (1783382400, 1785801600),   # 2026-07-06 .. 2026-08-03
}

print("=== (a) Arctic Shift selftext retention by 2026 window ===")
for sub in ("phcareers", "buhaycorpo"):
    for label, (a, b) in EPOCHS.items():
        window(sub, a, b, f"{sub}/{label}")
        time.sleep(8)

print("\n=== (b) Great Place To Work PH ===")
GH = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}
for u in ["https://www.greatplacetowork.com.ph/certified-companies",
          "https://www.greatplacetowork.com.ph/"]:
    try:
        r = requests.get(u, headers=GH, timeout=30)
        print(f"  {u} -> {r.status_code} len={len(r.text)}")
    except Exception as e:  # noqa: BLE001
        print(f"  {u} ERR {e!r:.100}")

print("\n=== (c) Kalibrr long-shot review paths ===")
for u in ["https://www.kalibrr.com/home/company/globant/reviews",
          "https://www.kalibrr.com/en-ph/company/globant"]:
    try:
        r = requests.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        print(f"  {u} -> {r.status_code} len={len(r.text)}")
    except Exception as e:  # noqa: BLE001
        print(f"  {u} ERR {e!r:.100}")

print("\n=== (d) jobox retry ===")
for u in ["https://jobox.ph/robots.txt", "https://www.jobox.ph/"]:
    try:
        r = requests.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=25,
                         verify=False)
        print(f"  {u} -> {r.status_code} len={len(r.text)}")
    except Exception as e:  # noqa: BLE001
        print(f"  {u} ERR {e!r:.120}")
print("DONE")
