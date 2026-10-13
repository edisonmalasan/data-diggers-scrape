"""Probe Glints PH company reviews via real Chrome (Playwright).

Glints robots.txt only disallows auth/settings/user paths — company review
pages are crawl-permitted, but plain requests get a 403 WAF challenge, so we
load with a real browser (same pattern as scrape_jobstreet.py).

Checks: does a PH company reviews page exist, render, and contain
date/job-title/pros-cons fields we can map to the contract?
"""
from __future__ import annotations

import re
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
STORAGE = HERE / ".storage"

# Search Glints PH for known IT/CS employers and try the reviews tab.
URLS = [
    "https://glints.com/ph/en/companies",
    "https://glints.com/ph/en/companies/globe-telecom-361375662572904/reviews",
]

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=False)
    ctx = b.new_context(locale="en-US",
                        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                                    "Chrome/126.0.0.0 Safari/537.36"))
    pg = ctx.new_page()
    for u in URLS:
        try:
            resp = pg.goto(u, timeout=60000, wait_until="domcontentloaded")
            pg.wait_for_timeout(4000)
            status = resp.status if resp else "?"
            html = pg.content()
            title = pg.title()
            print(f"\n=== {u}")
            print(f"  status={status} title={title!r} len={len(html)}")
            for marker in ["Review", "review", "Pros", "Cons", "rating",
                           "Rating", "employee", "Employee"]:
                print(f"    {marker!r}: {html.count(marker)}")
            out = STORAGE / f"glints_probe_{abs(hash(u)) % 100000}.html"
            out.write_text(html, encoding="utf-8")
            print(f"  saved {out.name}")
            # find company links on the directory page
            if u.endswith("/companies"):
                links = sorted(set(re.findall(
                    r'href="(/ph/en/companies/[^"?#]+)"', html)))
                print(f"  company links found: {len(links)}; sample={links[:8]}")
        except Exception as e:  # noqa: BLE001
            print(f"\n=== {u}\n  ERR {e!r:.200}")
    b.close()
print("DONE")
