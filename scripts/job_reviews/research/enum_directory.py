"""Enumerate ALL JobStreet directory industries -> company slugs + has-reviews flag.

Directory cards render a 'Reviews' nav link only when the company has reviews,
so we can skip review-less companies entirely (the biggest yield win).
robots.txt allows clean /companies/directory/<industry> paths.

Output: merges into .storage/jobstreet_slugs.json adding fields:
  rev: True/False (has reviews), ind: <industry-slug>
"""
import json
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SLUGS = ROOT / ".storage" / "jobstreet_slugs.json"
INDS = ROOT / ".storage" / "jobstreet_industries.json"
BASE = "https://ph.jobstreet.com"

EXTRACT = r"""() => {
  const ORIGIN = 'https://ph.jobstreet.com';
  const norm = h => (h || '').replace(ORIGIN, '').split('?')[0];
  // slugs whose card exposes a /reviews link, derived straight from hrefs
  const revSlugs = new Set();
  document.querySelectorAll("a[href]").forEach(x => {
    const m = norm(x.getAttribute('href')).match(/^\/companies\/([a-z0-9\-]+)\/reviews$/);
    if (m) revSlugs.add(m[1]);
  });
  const out = [], seen = new Set();
  document.querySelectorAll("a[href*='/companies/']").forEach(a => {
    const m = norm(a.getAttribute('href')).match(/^\/companies\/([a-z0-9\-]+)$/);
    if (!m || seen.has(m[1])) return;
    seen.add(m[1]);
    out.push({slug: m[1], rev: revSlugs.has(m[1])});
  });
  return out;
}"""

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=False)
    pg = b.new_context(locale="en-US").new_page()

    # 1) collect industry paths
    pg.goto(f"{BASE}/companies/directory", timeout=45000, wait_until="domcontentloaded")
    pg.wait_for_timeout(3000)
    hrefs = pg.eval_on_selector_all("a[href]", "els => els.map(e => e.getAttribute('href'))")
    inds = sorted({h.split("?")[0] for h in hrefs
                   if h and h.startswith("/companies/directory/") and h.count("/") == 3})
    print(f"industries: {len(inds)}")
    INDS.write_text(json.dumps(inds, indent=0), encoding="utf-8")

    # 2) walk each industry page
    merged: dict[str, dict] = {}
    for i, ind in enumerate(inds, 1):
        try:
            pg.goto(f"{BASE}{ind}", timeout=45000, wait_until="domcontentloaded")
            pg.wait_for_timeout(2500)
            pg.mouse.wheel(0, 8000)
            pg.wait_for_timeout(1200)
            cards = pg.evaluate(EXTRACT)
            for c in cards:
                rec = merged.setdefault(c["slug"], {"slug": c["slug"], "rev": False,
                                                    "ind": ind.rsplit("/", 1)[-1]})
                rec["rev"] = rec["rev"] or c["rev"]
            nrev = sum(1 for c in cards if c["rev"])
            print(f"[{i}/{len(inds)}] {ind.rsplit('/',1)[-1][:44]}: "
                  f"{len(cards)} companies ({nrev} w/ reviews)")
        except Exception as e:  # noqa: BLE001
            print(f"[{i}/{len(inds)}] ERROR {ind}: {type(e).__name__} {e}")
        time.sleep(0.8)
    b.close()

# 3) merge with existing slugs (wayback list has ts; directory has rev/ind)
existing = {s["slug"]: s for s in json.loads(SLUGS.read_text(encoding="utf-8"))}
new = 0
for slug, rec in merged.items():
    if slug in existing:
        existing[slug]["rev"] = rec["rev"]   # fresh directory truth overwrites
        existing[slug]["ind"] = rec["ind"]
    else:
        existing[slug] = rec
        new += 1
SLUGS.write_text(json.dumps(sorted(existing.values(), key=lambda x: x["slug"]), indent=0),
                 encoding="utf-8")
withrev = sum(1 for s in existing.values() if s.get("rev"))
print(f"\nMERGED: total={len(existing)} (+{new} new), with_reviews={withrev} -> {SLUGS}")
