"""Expand JobStreet company slugs via the robots-ALLOWED ?keywords= search.

robots.txt: 'Allow: *?keywords' — keyword searches are explicitly permitted;
plain /companies/<slug>/reviews fetches are permitted; ?page=.. is NOT.
New slugs are marked ts=20261008 (verified live today -> treated as recent).
"""
import json
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).with_name(".storage") / "jobstreet_slugs.json"

QUERIES = [
    "software", "developer", "information technology", "technologies",
    "digital", "systems", "network", "telecom", "data", "cloud",
    "outsourcing", "bpo", "solutions", "bank", "analytics",
    "consulting", "global services", "engineering", "electronics",
    "computer", "cybersecurity", "telecommunications",
]

LINK_RE = re.compile(r"^/companies/([a-z0-9\-]+)")

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=False)
    page = browser.new_context(locale="en-US").new_page()
    found: dict[str, dict] = {}
    for q in QUERIES:
        url = f"https://ph.jobstreet.com/companies?keywords={q.replace(' ', '+')}"
        try:
            page.goto(url, timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            hrefs = page.eval_on_selector_all(
                "a[href*='/companies/']", "els => els.map(e => e.getAttribute('href'))")
            n0 = len(found)
            for h in hrefs:
                m = LINK_RE.match(h or "")
                if m and m.group(1) != "write-a-review":
                    found.setdefault(m.group(1), {"slug": m.group(1), "ts": "20261008",
                                                  "reviews": True})
            print(f"{q!r}: links={len(hrefs)} new_total={len(found)} (+{len(found)-n0})")
        except Exception as e:  # noqa: BLE001
            print(f"{q!r}: ERROR {type(e).__name__} {e}")
        time.sleep(1.5)
    browser.close()

# merge with existing
existing = {s["slug"]: s for s in json.loads(OUT.read_text(encoding="utf-8"))}
before = len(existing)
for slug, meta in found.items():
    if slug not in existing:
        existing[slug] = meta
OUT.write_text(json.dumps(sorted(existing.values(), key=lambda x: x["slug"]), indent=0),
               encoding="utf-8")
print(f"merged: {before} -> {len(existing)} slugs (+{len(existing)-before}) -> {OUT}")
